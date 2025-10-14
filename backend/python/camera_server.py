#!/usr/bin/env python3
"""
Flask server for Raspberry Pi camera streaming and YOLOv8 sign detection.
Optimized for Raspberry Pi 5 with camera module.
"""
import os
import time
import cv2
import numpy as np
from flask import Flask, Response, jsonify
from flask_cors import CORS
from threading import Thread, Lock, Event
from collections import deque
import logging
from contextlib import contextmanager

# Import configuration loader
from config_loader import get_config_loader

# Try importing picamera2 for Raspberry Pi camera, fall back to cv2
try:
    from picamera2 import Picamera2
    USE_PICAMERA = True
except ImportError:
    USE_PICAMERA = False
    print("picamera2 not available, using OpenCV VideoCapture")

# Try importing ultralytics for YOLOv8
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("ultralytics not available, using dummy detections")

app = Flask(__name__)
CORS(app)

# Load configuration from shared/config.json (with environment variable override support)
config = get_config_loader()
MODEL_PATH = os.getenv('MODEL_PATH', config.get_model_path())
FALLBACK_MODEL = 'yolov8n.pt'
CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', config.get_camera_width()))
CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', config.get_camera_height()))
CAMERA_FPS = int(os.getenv('CAMERA_FPS', config.get_camera_fps()))
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', config.get_confidence_threshold()))
DETECTION_INTERVAL = int(os.getenv('DETECTION_INTERVAL', config.get_detection_interval()))
JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', config.get_jpeg_quality()))
MAX_DETECTION_HISTORY = 10

print(f"\n{'='*60}")
print(f"Camera Server Configuration:")
print(f"{'='*60}")
print(f"Model Path:            {MODEL_PATH}")
print(f"Camera Resolution:     {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS} FPS")
print(f"Confidence Threshold:  {CONFIDENCE_THRESHOLD}")
print(f"Detection Interval:    {DETECTION_INTERVAL} frame(s)")
print(f"JPEG Quality:          {JPEG_QUALITY}")
print(f"{'='*60}\n")

# Global state
camera = None
model = None
current_frame = None
current_detections = deque(maxlen=MAX_DETECTION_HISTORY)
frame_lock = Lock()
detection_lock = Lock()
running = False
frame_ready = Event()

# Performance metrics
frame_count = 0
detection_count = 0
last_fps_time = time.time()
current_fps = 0

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@contextmanager
def camera_resource():
    """Context manager for camera resource cleanup."""
    cam = None
    try:
        yield cam
    finally:
        if cam is not None:
            if USE_PICAMERA and isinstance(cam, Picamera2):
                cam.stop()
            elif hasattr(cam, 'release'):
                cam.release()
            logger.info("Camera released")


def initialize_camera():
    """Initialize Raspberry Pi camera or fallback to USB camera."""
    global camera
    
    if USE_PICAMERA:
        try:
            logger.info("Initializing Raspberry Pi Camera...")
            camera = Picamera2()
            config = camera.create_preview_configuration(
                main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"},
                buffer_count=2  # Minimize buffer for lower latency
            )
            camera.configure(config)
            camera.start()
            # Warm up camera
            time.sleep(0.5)
            logger.info(f"Raspberry Pi Camera initialized ({CAMERA_WIDTH}x{CAMERA_HEIGHT})")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Pi Camera: {e}")
            camera = None
    
    # Fallback to USB camera
    try:
        logger.info("Initializing USB/Default camera...")
        camera = cv2.VideoCapture(0, cv2.CAP_V4L2 if os.name != 'nt' else cv2.CAP_DSHOW)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
        
        if camera.isOpened():
            # Warm up camera
            for _ in range(5):
                camera.read()
            logger.info(f"USB Camera initialized ({CAMERA_WIDTH}x{CAMERA_HEIGHT})")
            return True
        else:
            logger.error("Failed to open camera")
            return False
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return False


def initialize_model():
    """Load YOLOv8 model with optimization."""
    global model
    
    if not HAS_YOLO:
        logger.warning("YOLOv8 not available, using dummy detections")
        return False
    
    try:
        # Try loading custom trained model first
        if os.path.exists(MODEL_PATH):
            logger.info(f"Loading custom model from {MODEL_PATH}")
            model = YOLO(MODEL_PATH)
        else:
            logger.info(f"Custom model not found, using {FALLBACK_MODEL}")
            model = YOLO(FALLBACK_MODEL)
        
        # Warm up model with dummy input
        dummy_frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
        _ = model(dummy_frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        logger.info(f"Model loaded successfully ({len(model.names)} classes)")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


def get_frame():
    """Capture frame from camera with error handling."""
    global camera
    
    if camera is None:
        return None
    
    try:
        if USE_PICAMERA and isinstance(camera, Picamera2):
            # Picamera2 - already in RGB888
            return camera.capture_array()
        else:
            # OpenCV VideoCapture
            ret, frame = camera.read()
            return frame if ret else None
    except Exception as e:
        logger.error(f"Error capturing frame: {e}")
        return None


def dummy_detections(frame_shape):
    """Generate dummy detections when YOLO is not available."""
    h, w = frame_shape[:2]
    return [
        {
            'id': 1,
            'label': 'stop',
            'confidence': 0.92,
            'bbox': [int(w*0.2), int(h*0.2), int(w*0.4), int(h*0.5)],
            'timestamp': time.time()
        }
    ]


def detect_signs(frame):
    """Run YOLOv8 detection on frame with optimizations."""
    global model, detection_count
    
    if model is None or not HAS_YOLO:
        return dummy_detections(frame.shape)
    
    try:
        # Run inference with optimizations
        results = model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            verbose=False,
            stream=False,
            imgsz=(CAMERA_HEIGHT, CAMERA_WIDTH)  # Match camera resolution
        )
        
        detections = []
        timestamp = time.time()
        
        # Process results efficiently
        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                # Batch process boxes
                xyxy = boxes.xyxy.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                classes = boxes.cls.cpu().numpy().astype(int)
                
                for i, (bbox, conf, cls) in enumerate(zip(xyxy, confs, classes)):
                    detections.append({
                        'id': detection_count * 100 + i,
                        'label': model.names[cls],
                        'confidence': round(float(conf), 2),
                        'bbox': [int(x) for x in bbox],
                        'timestamp': timestamp
                    })
        
        detection_count += 1
        return detections
    except Exception as e:
        logger.error(f"Detection error: {e}")
        return []


def draw_detections(frame, detections):
    """Draw bounding boxes and labels on frame efficiently."""
    if not detections:
        return frame
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 2
    
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        label = det['label'].replace('_', ' ')
        conf = det['confidence']
        
        # Color based on confidence (green for high, yellow for medium)
        color = (0, 255, 0) if conf > 0.7 else (0, 255, 255)
        
        # Draw box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label with background
        text = f"{label} {conf:.0%}"
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Ensure label stays within frame
        label_y1 = max(y1 - text_h - baseline - 5, 0)
        label_y2 = label_y1 + text_h + baseline + 5
        
        cv2.rectangle(frame, (x1, label_y1), (x1 + text_w + 10, label_y2), color, -1)
        cv2.putText(frame, text, (x1 + 5, label_y2 - baseline - 2), 
                   font, font_scale, (0, 0, 0), thickness)
    
    return frame


def camera_loop():
    """Main camera processing loop with optimizations."""
    global current_frame, current_detections, running, frame_count, current_fps, last_fps_time
    
    logger.info("Starting camera loop...")
    local_frame_count = 0
    latest_detections = []
    
    while running:
        try:
            frame = get_frame()
            
            if frame is None:
                time.sleep(0.05)
                continue
            
            # Run detection every N frames to save CPU
            if local_frame_count % DETECTION_INTERVAL == 0:
                latest_detections = detect_signs(frame)
                
                # Update detection history
                if latest_detections:
                    with detection_lock:
                        current_detections.append({
                            'detections': latest_detections,
                            'timestamp': time.time(),
                            'frame': local_frame_count
                        })
            
            # Draw latest detections on current frame
            annotated_frame = draw_detections(frame.copy(), latest_detections)
            
            # Add FPS counter
            cv2.putText(annotated_frame, f"FPS: {current_fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Update global state
            with frame_lock:
                current_frame = annotated_frame
            
            frame_ready.set()
            local_frame_count += 1
            
            # Calculate FPS
            if local_frame_count % 30 == 0:
                current_time = time.time()
                elapsed = current_time - last_fps_time
                if elapsed > 0:
                    current_fps = 30 / elapsed
                    last_fps_time = current_time
            
            # Dynamic frame rate control
            time.sleep(1.0 / CAMERA_FPS)
            
        except Exception as e:
            logger.error(f"Error in camera loop: {e}")
            time.sleep(0.5)
    
    logger.info(f"Camera loop stopped (processed {local_frame_count} frames)")


def generate_frames():
    """Generator for MJPEG stream with optimization."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    
    while True:
        # Wait for frame to be ready
        frame_ready.wait(timeout=1.0)
        
        with frame_lock:
            if current_frame is None:
                time.sleep(0.05)
                continue
            
            # Encode frame as JPEG with specified quality
            ret, buffer = cv2.imencode('.jpg', current_frame, encode_params)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' + 
               frame_bytes + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/detections', methods=['GET'])
def get_detections():
    """Get current detections with history."""
    with detection_lock:
        # Get most recent detections
        if current_detections:
            latest = current_detections[-1]
            detections = latest['detections']
        else:
            detections = []
    
    return jsonify({
        'ok': True,
        'detections': detections,
        'count': len(detections),
        'timestamp': time.time(),
        'fps': round(current_fps, 1)
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status with metrics."""
    return jsonify({
        'ok': True,
        'camera': camera is not None,
        'model': model is not None,
        'picamera': USE_PICAMERA,
        'yolo': HAS_YOLO,
        'running': running,
        'fps': round(current_fps, 1),
        'frame_count': frame_count,
        'detection_count': detection_count,
        'config': {
            'resolution': f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
            'target_fps': CAMERA_FPS,
            'confidence': CONFIDENCE_THRESHOLD,
            'detection_interval': DETECTION_INTERVAL
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


def start_server():
    """Initialize and start the Flask server."""
    global running
    
    logger.info("Initializing sign detection system...")
    
    # Initialize camera
    if not initialize_camera():
        logger.error("Failed to initialize camera")
        return False
    
    # Initialize model
    initialize_model()
    
    # Start camera processing thread
    running = True
    camera_thread = Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    
    logger.info("System initialized successfully")
    return True


def cleanup():
    """Cleanup resources safely."""
    global running, camera
    
    logger.info("Cleaning up...")
    running = False
    frame_ready.set()  # Unblock any waiting threads
    time.sleep(0.5)
    
    if camera is not None:
        try:
            if USE_PICAMERA and isinstance(camera, Picamera2):
                camera.stop()
            elif hasattr(camera, 'release'):
                camera.release()
            logger.info("Camera released successfully")
        except Exception as e:
            logger.error(f"Error releasing camera: {e}")
    
    logger.info(f"Cleanup complete (Total frames: {frame_count}, Detections: {detection_count})")


if __name__ == '__main__':
    try:
        if start_server():
            port = int(os.getenv('PORT', config.get_python_server_port()))
            print(f"Starting Flask server on port {port}...")
            app.run(host='0.0.0.0', port=port, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        cleanup()
