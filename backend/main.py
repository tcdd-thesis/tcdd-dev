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
from display import DisplayController
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
display_controller = None
is_streaming = True  # Always streaming in backend
metrics_logger = MetricsLogger(log_dir='data/logs', prefix='metrics', interval=1)
violations_logger = ViolationsLogger(log_dir='data/logs', prefix='violations')

# ============================================================================
# CONFIGURATION CHANGE HANDLERS
# ============================================================================

def on_config_change(old_config, new_config):
    """
    Handle configuration changes and update running components
    This is called automatically when config.json is modified
    """
    global camera, detector, display_controller
    
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
        
        # Check display settings changes
        display_changed = (
            old_config.get('display') != new_config.get('display')
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
        
        # Update display brightness if changed
        if display_changed and display_controller:
            new_brightness = new_config.get('display', {}).get('brightness', 100)
            old_brightness = old_config.get('display', {}).get('brightness', 100)
            if new_brightness != old_brightness:
                logger.info(f"🔆 Display brightness changed: {old_brightness}% → {new_brightness}%")
                display_controller.set_brightness(new_brightness)
        
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
    global camera, detector, display_controller, is_streaming
    try:
        logger.info("Initializing display controller...")
        display_controller = DisplayController(config)
        
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

@app.route('/api/shutdown', methods=['POST'])
def shutdown_system():
    """Shutdown the Raspberry Pi using detached process"""
    import subprocess
    
    logger.info("Shutdown requested via API")
    
    # Spawn detached process to shutdown after brief delay
    shutdown_script = '''
        sleep 1
        sudo shutdown now
    '''
    
    try:
        subprocess.Popen(
            ['bash', '-c', shutdown_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        logger.error(f"Failed to initiate shutdown: {e}")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': 'Shutting down...'}), 200

@app.route('/api/reboot', methods=['POST'])
def reboot_system():
    """Reboot the Raspberry Pi using detached process"""
    import subprocess
    
    logger.info("Reboot requested via API")
    
    # Spawn detached process to reboot after brief delay
    reboot_script = '''
        sleep 1
        sudo reboot
    '''
    
    try:
        subprocess.Popen(
            ['bash', '-c', reboot_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        logger.error(f"Failed to initiate reboot: {e}")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': 'Rebooting...'}), 200

@app.route('/api/close-app', methods=['POST'])
def close_app():
    """Close the application immediately using external process"""
    import subprocess
    
    # Get our own PID
    my_pid = os.getpid()
    
    logger.info(f"Close app requested - PID {my_pid} will be killed")
    
    # Spawn a detached shell process that waits briefly then kills everything
    # This runs OUTSIDE of Python's control so SocketIO can't block it
    kill_script = f'''
        sleep 0.5
        killall -9 chromium-browser 2>/dev/null
        killall -9 chromium 2>/dev/null
        kill -9 {my_pid} 2>/dev/null
    '''
    
    try:
        # Use Popen with shell=True and start_new_session to fully detach
        subprocess.Popen(
            ['bash', '-c', kill_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent process
        )
    except Exception as e:
        logger.error(f"Failed to spawn kill process: {e}")
    
    return jsonify({'message': 'Closing...'}), 200

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
# DISPLAY BRIGHTNESS API
# ----------------------------------------------------------------------------

@app.route('/api/display/brightness', methods=['GET'])
def get_display_brightness():
    """Get current display brightness level"""
    try:
        if display_controller:
            return jsonify({
                'brightness': display_controller.get_brightness(),
                'available': display_controller.is_available(),
                'initialized': display_controller.is_initialized()
            }), 200
        else:
            return jsonify({
                'brightness': 100,
                'available': False,
                'initialized': False,
                'message': 'Display controller not initialized'
            }), 200
    except Exception as e:
        logger.error(f"Error getting display brightness: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/display/brightness', methods=['POST'])
def set_display_brightness():
    """
    Set display brightness level
    
    Request body:
        { "brightness": 0-100 }
    """
    try:
        data = request.get_json()
        brightness = data.get('brightness', 100)
        
        # Validate brightness value
        brightness = max(0, min(100, int(brightness)))
        
        if display_controller:
            success = display_controller.set_brightness(brightness)
            
            if success:
                # Also update config
                config.set('display.brightness', brightness, save=True)
                
                return jsonify({
                    'message': f'Brightness set to {brightness}%',
                    'brightness': brightness
                }), 200
            else:
                return jsonify({
                    'error': 'Failed to set brightness',
                    'brightness': display_controller.get_brightness()
                }), 500
        else:
            # Still save to config even if controller not available
            config.set('display.brightness', brightness, save=True)
            return jsonify({
                'message': f'Brightness saved to config (controller not available)',
                'brightness': brightness,
                'available': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error setting display brightness: {e}")
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

            # JPEG encode timing
            import cv2
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
            socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            if camera:
                camera.stop()
            logger.info("Goodbye!")
    else:
        logger.error("Failed to initialize system. Exiting.")
        sys.exit(1)
