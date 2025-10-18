#!/usr/bin/env python3
"""
Camera capture module for Raspberry Pi and USB cameras.
Provides a simple Camera class used by backend/main.py.
Applies automatic white balance (AWB) to neutralize color cast.
"""

import os
import time
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Try importing Picamera2 (Raspberry Pi camera)
try:
    from picamera2 import Picamera2  # type: ignore
    HAS_PICAMERA2 = True
except Exception:
    HAS_PICAMERA2 = False
    Picamera2 = None  # type: ignore


def _apply_white_balance_bgr(frame_bgr: np.ndarray) -> np.ndarray:
    """Auto white-balance via LAB color mean-centering (fast, no extra deps)."""
    try:
        lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        a_mean = float(a.mean())
        b_mean = float(b.mean())
        # Center color channels around 128 (neutral gray)
        a = np.clip(a - (a_mean - 128.0), 0, 255).astype(np.uint8)
        b = np.clip(b - (b_mean - 128.0), 0, 255).astype(np.uint8)
        corrected = cv2.merge([l, a, b])
        return cv2.cvtColor(corrected, cv2.COLOR_LAB2BGR)
    except Exception as e:
        logger.debug(f"AWB failed, returning original frame: {e}")
        return frame_bgr


class Camera:
    """Minimal camera wrapper used by backend/main.py"""

    def __init__(self, cfg):
        # Read config with safe fallbacks
        self.width = int(cfg.get('camera.width', 640))
        self.height = int(cfg.get('camera.height', 480))
        self.fps = int(cfg.get('camera.fps', 30))
        engine = (cfg.get('detection.engine', 'ultralytics') or 'ultralytics').lower()
        # NCNN path expects RGB input; Ultralytics prefers BGR (OpenCV)
        self.output_color = 'RGB' if engine == 'ncnn' else 'BGR'

        self.picam: Optional[Picamera2] = None  # type: ignore
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False

    def start(self) -> bool:
        # Prefer Pi Camera if available
        if HAS_PICAMERA2:
            try:
                logger.info("Initializing PiCamera2...")
                self.picam = Picamera2()  # type: ignore
                config = self.picam.create_preview_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"},
                    buffer_count=2
                )
                self.picam.configure(config)
                # Enable automatic white balance on hardware (best effort)
                try:
                    self.picam.set_controls({"AwbEnable": True, "AwbMode": 0})
                except Exception:
                    pass
                self.picam.start()
                time.sleep(1.0)  # allow AWB to converge
                self.running = True
                logger.info(f"PiCamera2 started at {self.width}x{self.height}@{self.fps}")
                return True
            except Exception as e:
                logger.warning(f"PiCamera2 init failed, falling back to OpenCV: {e}")
                self.picam = None

        # Fallback to USB/default camera via OpenCV
        try:
            logger.info("Initializing OpenCV VideoCapture(0)...")
            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2 if os.name != 'nt' else cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            # Reduce latency by minimizing internal buffer
            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            if not self.cap.isOpened():
                raise RuntimeError("Unable to open camera 0")
            # Warm-up frames
            for _ in range(5):
                self.cap.read()
            self.running = True
            logger.info(f"OpenCV camera started at {self.width}x{self.height}@{self.fps}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenCV camera: {e}")
            self.cap = None
            self.running = False
            return False

    def is_running(self) -> bool:
        return self.running

    def get_frame(self):
        if not self.running:
            return None

        frame_bgr = None
        try:
            if self.picam is not None:
                # PiCamera returns RGB; convert to BGR for processing/AWB
                rgb = self.picam.capture_array()
                frame_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            elif self.cap is not None:
                ok, frame = self.cap.read()
                frame_bgr = frame if ok else None
            else:
                return None

            if frame_bgr is None:
                return None

            # Apply software AWB
            frame_bgr = _apply_white_balance_bgr(frame_bgr)

            # Return in requested color order
            if self.output_color == 'RGB':
                return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            return frame_bgr

        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None

    def stop(self):
        try:
            if self.picam is not None:
                try:
                    self.picam.stop()
                except Exception:
                    pass
                self.picam = None
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
        finally:
            self.running = False
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

# Optional configuration loader (fallback to defaults if unavailable)
try:
    from config_loader import get_config_loader  # may not exist in this repo
    _HAS_CONFIG_LOADER = True
except Exception:
    _HAS_CONFIG_LOADER = False

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


"""
Global defaults; will be overridden by Camera(config) on initialization
when this module is used via backend/main.py.
"""
if _HAS_CONFIG_LOADER:
    # Load configuration via helper if available (other repo layout)
    config = get_config_loader()
    model_config = config.get_model_config()
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', config.get_camera_width()))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', config.get_camera_height()))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', config.get_camera_fps()))
    DETECTION_INTERVAL = int(os.getenv('DETECTION_INTERVAL', config.get_detection_interval()))
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', config.get_jpeg_quality()))
else:
    # Sane defaults; main.py's Camera wrapper will overwrite these
    config = None
    model_config = {"type": "ultralytics", "confidence": 0.5}
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', 640))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', 480))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', 30))
    DETECTION_INTERVAL = int(os.getenv('DETECTION_INTERVAL', 1))
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', 80))
MAX_DETECTION_HISTORY = 10

try:
    print(f"\n{'='*60}")
    print(f"Camera Module Configuration:")
    print(f"{'='*60}")
    print(f"Model Type:            {model_config.get('type', 'ultralytics')}")
    print(f"Camera Resolution:     {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS} FPS")
    print(f"Confidence Threshold:  {model_config.get('confidence', 0.5)}")
    print(f"Detection Interval:    {DETECTION_INTERVAL} frame(s)")
    print(f"JPEG Quality:          {JPEG_QUALITY}")
    print(f"{'='*60}\n")
except Exception:
    pass

# Global state
camera = None
detector = None
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
            
            # Configure camera with auto white balance enabled
            config = camera.create_preview_configuration(
                main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"},
                buffer_count=2  # Minimize buffer for lower latency
            )
            camera.configure(config)
            
            # Set automatic white balance mode for better color accuracy
            # Available modes: 'auto', 'tungsten', 'fluorescent', 'indoor', 'daylight', 'cloudy'
            camera.set_controls({
                "AwbEnable": True,  # Enable auto white balance
                "AwbMode": 0        # 0 = Auto mode for adaptive color correction
            })
            
            camera.start()
            # Warm up camera and let AWB stabilize
            time.sleep(1.0)  # Increased to let AWB converge
            logger.info(f"Raspberry Pi Camera initialized with Auto White Balance ({CAMERA_WIDTH}x{CAMERA_HEIGHT})")
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



def apply_white_balance(frame):
    """
    Apply automatic white balance correction to remove color cast.
    Uses LAB color space for more accurate color temperature adjustment.
    
    Args:
        frame: Input BGR frame from camera
        
    Returns:
        Color-corrected BGR frame with neutral white balance
    """
    if frame is None:
        return None
    
    try:
        # Convert BGR to LAB color space (perceptually uniform)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        
        # Split LAB channels
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # Calculate mean values for a and b channels (color information)
        a_mean = np.mean(a_channel)
        b_mean = np.mean(b_channel)
        
        # Shift a and b channels to center them around 128 (neutral gray)
        # This removes color cast by neutralizing the color bias
        a_channel = np.clip(a_channel - (a_mean - 128), 0, 255).astype(np.uint8)
        b_channel = np.clip(b_channel - (b_mean - 128), 0, 255).astype(np.uint8)
        
        # Merge corrected channels back
        corrected_lab = cv2.merge([l_channel, a_channel, b_channel])
        
        # Convert back to BGR
        corrected_frame = cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)
        
        #!/usr/bin/env python3
        """
        Camera capture module for Raspberry Pi and USB cameras.
        Provides a simple Camera class used by backend/main.py.
        Applies automatic white balance (AWB) to neutralize color cast.
        """

        import os
        import time
        import logging
        from typing import Optional

        import cv2
        import numpy as np

        logger = logging.getLogger(__name__)

        # Try importing Picamera2 (Raspberry Pi camera)
        try:
            from picamera2 import Picamera2  # type: ignore
            HAS_PICAMERA2 = True
        except Exception:
            HAS_PICAMERA2 = False
            Picamera2 = None  # type: ignore


        def _apply_white_balance_bgr(frame_bgr: np.ndarray) -> np.ndarray:
            """Auto white-balance via LAB color mean-centering (fast, no deps)."""
            try:
                lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                a_mean = float(a.mean())
                b_mean = float(b.mean())
                # Center color channels around 128 (neutral gray)
                a = np.clip(a - (a_mean - 128.0), 0, 255).astype(np.uint8)
                b = np.clip(b - (b_mean - 128.0), 0, 255).astype(np.uint8)
                corrected = cv2.merge([l, a, b])
                return cv2.cvtColor(corrected, cv2.COLOR_LAB2BGR)
            except Exception as e:
                logger.debug(f"AWB failed, returning original frame: {e}")
                return frame_bgr


        class Camera:
            """Minimal camera wrapper used by backend/main.py"""

            def __init__(self, cfg):
                # Read config with safe fallbacks
                self.width = int(cfg.get('camera.width', 640))
                self.height = int(cfg.get('camera.height', 480))
                self.fps = int(cfg.get('camera.fps', 30))
                engine = (cfg.get('detection.engine', 'ultralytics') or 'ultralytics').lower()
                # NCNN path expects RGB input; Ultralytics prefers BGR (OpenCV)
                self.output_color = 'RGB' if engine == 'ncnn' else 'BGR'

                self.picam: Optional[Picamera2] = None  # type: ignore
                self.cap: Optional[cv2.VideoCapture] = None
                self.running = False

            def start(self) -> bool:
                # Prefer Pi Camera if available
                if HAS_PICAMERA2:
                    try:
                        logger.info("Initializing PiCamera2...")
                        self.picam = Picamera2()  # type: ignore
                        config = self.picam.create_preview_configuration(
                            main={"size": (self.width, self.height), "format": "RGB888"},
                            buffer_count=2
                        )
                        self.picam.configure(config)
                        # Enable automatic white balance on hardware
                        try:
                            self.picam.set_controls({"AwbEnable": True, "AwbMode": 0})
                        except Exception:
                            pass
                        self.picam.start()
                        time.sleep(1.0)  # allow AWB to converge
                        self.running = True
                        logger.info(f"PiCamera2 started at {self.width}x{self.height}@{self.fps}")
                        return True
                    except Exception as e:
                        logger.warning(f"PiCamera2 init failed, falling back to OpenCV: {e}")
                        self.picam = None

                # Fallback to USB/default camera via OpenCV
                try:
                    logger.info("Initializing OpenCV VideoCapture(0)...")
                    self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2 if os.name != 'nt' else cv2.CAP_DSHOW)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not self.cap.isOpened():
                        raise RuntimeError("Unable to open camera 0")
                    # Warm-up frames
                    for _ in range(5):
                        self.cap.read()
                    self.running = True
                    logger.info(f"OpenCV camera started at {self.width}x{self.height}@{self.fps}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to initialize OpenCV camera: {e}")
                    self.cap = None
                    self.running = False
                    return False

            def is_running(self) -> bool:
                return self.running

            def get_frame(self):
                if not self.running:
                    return None

                frame_bgr = None
                try:
                    if self.picam is not None:
                        # PiCamera returns RGB; convert to BGR for processing/AWB
                        rgb = self.picam.capture_array()
                        frame_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                    elif self.cap is not None:
                        ok, frame = self.cap.read()
                        frame_bgr = frame if ok else None
                    else:
                        return None

                    if frame_bgr is None:
                        return None

                    # Apply software AWB
                    frame_bgr = _apply_white_balance_bgr(frame_bgr)

                    # Return in requested color order
                    if self.output_color == 'RGB':
                        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    return frame_bgr

                except Exception as e:
                    logger.error(f"Error capturing frame: {e}")
                    return None

            def stop(self):
                try:
                    if self.picam is not None:
                        try:
                            self.picam.stop()
                        except Exception:
                            pass
                        self.picam = None
                    if self.cap is not None:
                        try:
                            self.cap.release()
                        except Exception:
                            pass
                        self.cap = None
                finally:
                    self.running = False
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
    'model': detector is not None,
        'picamera': USE_PICAMERA,
        'yolo': HAS_YOLO,
        'running': running,
        'fps': round(current_fps, 1),
        'frame_count': frame_count,
        'detection_count': detection_count,
        'config': {
            'resolution': f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
            'target_fps': CAMERA_FPS,
            'confidence': model_config.get('confidence', 0.15),
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
    # Initialize detector
    initialize_detector()
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
