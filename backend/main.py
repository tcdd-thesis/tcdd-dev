#!/usr/bin/env python3
"""
Sign Detection System - Main Flask Application
Serves both frontend (HTML/CSS/JS) and backend API
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import sys
import logging
import subprocess
import signal
import threading
from datetime import datetime
from pathlib import Path

# Set project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
os.chdir(PROJECT_ROOT)

# Import local modules
from camera import Camera
from detector import Detector
from config import Config
from metrics_logger import MetricsLogger
from violations_logger import ViolationsLogger
import psutil

# Initialize Flask app
app = Flask(__name__,
            static_folder='../frontend/static',
            static_url_path='/static',
            template_folder='../frontend/templates')

# Enable CORS for development
CORS(app)

# Initialize SocketIO for real-time video streaming
socketio = SocketIO(app, cors_allowed_origins="*")

# Load configuration
config = Config()

# Create necessary directories before logging setup
os.makedirs('data/logs', exist_ok=True)
os.makedirs('data/captures', exist_ok=True)
os.makedirs('data/recordings', exist_ok=True)
os.makedirs('backend/models', exist_ok=True)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get('logging.level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.get('logging.file', 'data/logs/app.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global instances
camera = None
detector = None
is_streaming = True  # Always streaming in backend
metrics_logger = MetricsLogger(log_dir='data/logs', prefix='metrics', interval=1)
violations_logger = ViolationsLogger(log_dir='data/logs', prefix='violations')

# Recording state
is_recording = False
recording_writer = None
recording_filename = None
recording_start_time = None
recording_lock = threading.Lock()
RECORDING_MAX_DURATION = 15 * 60  # 15 minutes in seconds

# ============================================================================
# CONFIGURATION CHANGE HANDLERS
# ============================================================================

def on_config_change(old_config, new_config):
    """
    Handle configuration changes and update running components
    This is called automatically when config.json is modified
    """
    global camera, detector
    
    logger.info("🔄 Configuration changed, updating components...")
    
    try:
        # Check camera settings changes
        camera_changed = (
            old_config.get('camera') != new_config.get('camera')
        )
        
        # Check detector settings changes
        detector_changed = (
            old_config.get('detection') != new_config.get('detection')
        )
        
        # Restart camera if settings changed
        if camera_changed and camera:
            logger.info("📷 Camera settings changed, restarting camera...")
            camera.stop()
            camera = Camera(config)
            camera.start()
            logger.info("✅ Camera restarted with new settings")
        
        # Reload detector if model or confidence changed
        if detector_changed and detector:
            logger.info("🔍 Detector settings changed, reloading detector...")
            detector = Detector(config)
            logger.info("✅ Detector reloaded with new settings")
        
        # Broadcast changes to all connected clients
        socketio.emit('config_updated', {
            'timestamp': datetime.now().isoformat(),
            'config': new_config
        })
        
        logger.info("✅ Configuration update complete!")
        
    except Exception as e:
        logger.error(f"❌ Error updating components after config change: {e}")

# Register the config change callback
config.register_change_callback(on_config_change)

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize():
    """Initialize camera and detector and start background streaming"""
    global camera, detector, is_streaming
    try:
        logger.info("Initializing camera...")
        camera = Camera(config)
        
        logger.info("Initializing detector...")
        detector = Detector(config)
        
        logger.info("Initialization complete!")
        # Start camera and detection immediately
        camera.start()
        is_streaming = True
        socketio.start_background_task(stream_video)
        return True
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False

# ============================================================================
# WEB ROUTES (Serve Frontend)
# ============================================================================

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route for client-side routing"""
    if path.startswith('static/') or '.' in path:
        return send_from_directory(app.static_folder, path)
    return render_template('index.html')

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    try:
        model_info = detector.get_info() if detector else {'engine': 'unknown', 'model': 'not loaded'}
        
        status = {
            'camera': camera.is_running() if camera else False,
            'detector': detector.is_loaded() if detector else False,
            'streaming': is_streaming,
            'engine': model_info['engine'],
            'model': model_info['model'],
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Start camera and detection (no-op, always running)"""
    return jsonify({'message': 'Camera already running'}), 200

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Stop camera and detection (not supported in always-on mode)"""
    return jsonify({'message': 'Camera always running in background'}), 200

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration with metadata"""
    try:
        return jsonify({
            'config': config.get_all(),
            'metadata': config.get_metadata()
        }), 200
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['PUT'])
def update_config():
    """
    Update configuration
    Changes are saved to config.json and automatically reflected in the system
    """
    try:
        data = request.get_json()
        
        # Update configuration (this will trigger callbacks and save to file)
        config.update(data, save=True)
        
        logger.info(f"✅ Configuration updated via API: {list(data.keys())}")
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'config': config.get_all(),
            'metadata': config.get_metadata()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error updating config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/reload', methods=['POST'])
def reload_config():
    """
    Force reload configuration from config.json file
    Useful after manually editing config.json
    """
    try:
        reloaded = config.reload()

        if reloaded:
            logger.info("✅ Configuration reloaded from file")
            return jsonify({
                'message': 'Configuration reloaded successfully',
                'config': config.get_all(),
                'metadata': config.get_metadata()
            }), 200
        else:
            return jsonify({
                'message': 'No changes detected in config file',
                'config': config.get_all()
            }), 200

    except Exception as e:
        logger.error(f"❌ Error reloading config: {e}")
        return jsonify({'error': str(e)}), 500

# ----------------------------------------------------------------------------
# VIOLATIONS API
# ----------------------------------------------------------------------------

@app.route('/api/violations', methods=['GET'])
def get_violations():
    """Return recent violation events as JSON array for UI display."""
    try:
        limit = int(request.args.get('limit', '100'))
        events = violations_logger.tail(limit=limit)
        return jsonify({
            'count': len(events),
            'violations': events
        }), 200
    except Exception as e:
        logger.error(f"Error getting violations: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# RECORDING API
# ============================================================================

@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """Start recording the video feed to an MP4 file."""
    global is_recording, recording_writer, recording_filename, recording_start_time
    
    try:
        with recording_lock:
            if is_recording:
                return jsonify({'message': 'Already recording', 'filename': recording_filename}), 200
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            recording_filename = f'recording_{timestamp}.mp4'
            filepath = os.path.join('data', 'recordings', recording_filename)
            
            # Get video dimensions from config
            width = config.get('camera.width', 640)
            height = config.get('camera.height', 480)
            fps = config.get('camera.fps', 30)
            
            # Initialize video writer with H.264 codec
            import cv2
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            recording_writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
            
            if not recording_writer.isOpened():
                recording_writer = None
                recording_filename = None
                return jsonify({'error': 'Failed to initialize video writer'}), 500
            
            is_recording = True
            recording_start_time = datetime.now()
            
            logger.info(f"📹 Recording started: {recording_filename}")
            
            return jsonify({
                'message': 'Recording started',
                'filename': recording_filename,
                'max_duration': RECORDING_MAX_DURATION
            }), 200
            
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """Stop the current recording."""
    global is_recording, recording_writer, recording_filename, recording_start_time
    
    try:
        with recording_lock:
            if not is_recording:
                return jsonify({'message': 'Not recording'}), 200
            
            saved_filename = recording_filename
            
            if recording_writer:
                recording_writer.release()
                recording_writer = None
            
            is_recording = False
            recording_filename = None
            recording_start_time = None
            
            logger.info(f"📹 Recording stopped: {saved_filename}")
            
            return jsonify({
                'message': 'Recording stopped',
                'filename': saved_filename
            }), 200
            
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recording/status', methods=['GET'])
def recording_status():
    """Get current recording status."""
    try:
        elapsed = 0
        remaining = RECORDING_MAX_DURATION
        
        if is_recording and recording_start_time:
            elapsed = (datetime.now() - recording_start_time).total_seconds()
            remaining = max(0, RECORDING_MAX_DURATION - elapsed)
        
        return jsonify({
            'recording': is_recording,
            'filename': recording_filename,
            'elapsed_seconds': int(elapsed),
            'remaining_seconds': int(remaining),
            'max_duration': RECORDING_MAX_DURATION
        }), 200
    except Exception as e:
        logger.error(f"Error getting recording status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recordings', methods=['GET'])
def list_recordings():
    """List all saved recordings with file info."""
    try:
        recordings_dir = os.path.join('data', 'recordings')
        recordings = []
        
        if os.path.exists(recordings_dir):
            for filename in os.listdir(recordings_dir):
                if filename.endswith('.mp4'):
                    filepath = os.path.join(recordings_dir, filename)
                    stat = os.stat(filepath)
                    recordings.append({
                        'filename': filename,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # Sort by modified time, newest first
        recordings.sort(key=lambda x: x['modified'], reverse=True)
        
        # Calculate total size
        total_size_mb = sum(r['size_mb'] for r in recordings)
        
        return jsonify({
            'count': len(recordings),
            'total_size_mb': round(total_size_mb, 2),
            'recordings': recordings
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing recordings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recordings/<filename>', methods=['GET'])
def serve_recording(filename):
    """Serve a recording file for playback/download."""
    try:
        recordings_dir = os.path.join(PROJECT_ROOT, 'data', 'recordings')
        return send_from_directory(recordings_dir, filename, as_attachment=False)
    except Exception as e:
        logger.error(f"Error serving recording {filename}: {e}")
        return jsonify({'error': 'Recording not found'}), 404

@app.route('/api/recordings/<filename>', methods=['DELETE'])
def delete_recording(filename):
    """Delete a recording file."""
    try:
        # Security check - prevent path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join('data', 'recordings', filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🗑️ Deleted recording: {filename}")
            return jsonify({'message': f'Deleted {filename}'}), 200
        else:
            return jsonify({'error': 'Recording not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting recording {filename}: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SYSTEM CONTROL API
# ============================================================================

@app.route('/api/system/shutdown-app', methods=['POST'])
def shutdown_app():
    """Gracefully shutdown the application."""
    try:
        logger.info("🛑 Application shutdown requested...")
        
        # Stop recording if active
        global is_recording, recording_writer
        with recording_lock:
            if is_recording and recording_writer:
                recording_writer.release()
                is_recording = False
        
        # Stop camera
        if camera:
            camera.stop()
            logger.info("📷 Camera stopped")
        
        # Send response before shutting down
        response = jsonify({'message': 'Application shutting down...'})
        
        # Schedule shutdown after response is sent
        def shutdown():
            import time
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGTERM)
        
        threading.Thread(target=shutdown, daemon=True).start()
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/shutdown-pi', methods=['POST'])
def shutdown_pi():
    """Shutdown the Raspberry Pi."""
    try:
        logger.info("🔴 Raspberry Pi shutdown requested...")
        
        # Stop recording if active
        global is_recording, recording_writer
        with recording_lock:
            if is_recording and recording_writer:
                recording_writer.release()
                is_recording = False
        
        # Stop camera
        if camera:
            camera.stop()
        
        # Send response before shutting down
        response = jsonify({'message': 'Raspberry Pi shutting down...'})
        
        # Schedule Pi shutdown after response is sent
        def pi_shutdown():
            import time
            time.sleep(2)
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=False)
        
        threading.Thread(target=pi_shutdown, daemon=True).start()
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Error during Pi shutdown: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/reboot-pi', methods=['POST'])
def reboot_pi():
    """Reboot the Raspberry Pi (app will auto-restart via systemd)."""
    try:
        logger.info("🔄 Raspberry Pi reboot requested...")
        
        # Stop recording if active
        global is_recording, recording_writer
        with recording_lock:
            if is_recording and recording_writer:
                recording_writer.release()
                is_recording = False
        
        # Stop camera
        if camera:
            camera.stop()
        
        # Send response before rebooting
        response = jsonify({'message': 'Raspberry Pi rebooting...'})
        
        # Schedule Pi reboot after response is sent
        def pi_reboot():
            import time
            time.sleep(2)
            subprocess.run(['sudo', 'reboot'], check=False)
        
        threading.Thread(target=pi_reboot, daemon=True).start()
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Error during Pi reboot: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# STREAMING LOOP WITH METRICS
# ============================================================================

def stream_video():
    """Stream video frames with detections and log C++-style metrics to CSV"""
    global is_streaming
    logger.info("Starting video stream...")
    frame_count = 0
    total_detections = 0
    dropped_frames = 0
    last_fps_time = datetime.now()
    jpeg_quality = config.get('streaming.quality', 85)
    process = psutil.Process(os.getpid())

    while is_streaming:
        try:
            # Capture frame timing
            frame_capture_start = datetime.now()
            frame = camera.get_frame()
            frame_capture_end = datetime.now()
            if frame is None:
                dropped_frames += 1
                socketio.sleep(0)
                continue

            # Inference timing
            inference_start = datetime.now()
            detections = detector.detect(frame)
            inference_end = datetime.now()

            annotated_frame = detector.draw_detections(frame, detections)

            # Write frame to recording if active
            import cv2
            with recording_lock:
                if is_recording and recording_writer:
                    # Write the annotated frame (with detections) to recording
                    recording_writer.write(annotated_frame)
                    
                    # Check if max duration reached
                    if recording_start_time:
                        elapsed = (datetime.now() - recording_start_time).total_seconds()
                        if elapsed >= RECORDING_MAX_DURATION:
                            recording_writer.release()
                            logger.info(f"📹 Recording auto-stopped (max duration reached): {recording_filename}")
                            socketio.emit('recording_stopped', {
                                'filename': recording_filename,
                                'reason': 'max_duration'
                            })
                            globals()['recording_writer'] = None
                            globals()['is_recording'] = False
                            globals()['recording_filename'] = None
                            globals()['recording_start_time'] = None

            # JPEG encode timing
            jpeg_start = datetime.now()
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
            jpeg_end = datetime.now()

            # Emit to clients
            import base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('video_frame', {
                'frame': frame_base64,
                'detections': [
                    {
                        'class_name': det['class_name'],
                        'confidence': float(det['confidence']),
                        'bbox': det['bbox']
                    } for det in detections
                ],
                'count': len(detections)
            })

            # Simple example: derive and log violation events (stub)
            # In a real implementation, this would use tracked vehicles, signal state, and rules.
            # Here we log a synthetic violation when a STOP sign is detected with high confidence.
            try:
                stop_dets = [d for d in detections if d.get('class_name', '').lower() in ('stop', 'stop_sign')]
                if stop_dets:
                    top = max(stop_dets, key=lambda d: d.get('confidence', 0))
                    if top.get('confidence', 0) >= max(0.85, config.get('detection.confidence', 0.5)):
                        event = {
                            'id': f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{frame_count:06d}",
                            'timestamp': now.isoformat(),
                            'violation_type': 'stop_sign',
                            'confidence': float(top['confidence']),
                            'driver_action': 'unknown',
                            'action_confidence': 0.0,
                            'vehicle': {'track_id': None},
                            'context': {'camera_id': 'cam-01', 'frame_id': frame_count},
                            'evidence': {
                                'sign_detected': {'label': top['class_name'], 'conf': float(top['confidence'])},
                                'bboxes': {'sign': top['bbox']}
                            },
                            'thresholds': {'decision_threshold': config.get('detection.confidence', 0.5)},
                            'severity': 'low',
                            'review': {'status': 'auto'},
                            'model': detector.get_info() if detector else {'engine': 'unknown', 'model': 'n/a'}
                        }
                        violations_logger.log(event)
            except Exception as e:
                logger.debug(f"Violation logging skipped: {e}")

            # Metrics
            frame_count += 1
            total_detections += len(detections)
            now = datetime.now()
            elapsed = (now - last_fps_time).total_seconds()
            fps = (frame_count / elapsed) if elapsed > 0 else 0.0
            camera_frame_time_ms = (frame_capture_end - frame_capture_start).total_seconds() * 1000.0
            inference_time_ms = (inference_end - inference_start).total_seconds() * 1000.0
            jpeg_encode_time_ms = (jpeg_end - jpeg_start).total_seconds() * 1000.0
            cpu_usage_percent = psutil.cpu_percent(interval=None)
            ram_usage_mb = process.memory_info().rss / (1024 * 1024)
            queue_size = 0

            metrics_logger.log(
                timestamp_iso=now.isoformat(),
                fps=fps,
                inference_time_ms=inference_time_ms,
                detections_count=len(detections),
                cpu_usage_percent=cpu_usage_percent,
                ram_usage_mb=ram_usage_mb,
                camera_frame_time_ms=camera_frame_time_ms,
                jpeg_encode_time_ms=jpeg_encode_time_ms,
                total_detections=total_detections,
                dropped_frames=dropped_frames,
                queue_size=queue_size
            )

            socketio.sleep(1.0 / config.get('camera.fps', 30))

        except Exception as e:
            logger.error(f"Error in video stream: {e}")
            socketio.sleep(0.1)

    logger.info("Video stream stopped")
    metrics_logger.close()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data/logs', exist_ok=True)
    os.makedirs('data/captures', exist_ok=True)
    os.makedirs('backend/models', exist_ok=True)
    
    # Initialize system
    logger.info("="*60)
    logger.info("Sign Detection System Starting...")
    logger.info("="*60)
    
    if initialize():
        port = config.get('port', 5000)
        debug = config.get('debug', False)
        
        logger.info(f"Server starting on http://0.0.0.0:{port}")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60)
        
        try:
            socketio.run(app, host='0.0.0.0', port=port, debug=debug)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            if camera:
                camera.stop()
            logger.info("Goodbye!")
    else:
        logger.error("Failed to initialize system. Exiting.")
        sys.exit(1)
