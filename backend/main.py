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
import threading
import cv2
import base64
from datetime import datetime
from pathlib import Path

try:
    import simplejpeg
    HAS_SIMPLEJPEG = True
except ImportError:
    HAS_SIMPLEJPEG = False

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
# If empty config and exception raised, exit
if config is None:
    sys.exit(1)

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

# ── Threaded pipeline shared state ──────────────────────────────────────────
_latest_frame = None            # Most recent raw frame from camera thread
_latest_frame_lock = threading.Lock()
_latest_detections = []         # Most recent detection results
_latest_annotated = None        # Most recent annotated frame
_latest_result_lock = threading.Lock()
_pipeline_frame_count = 0       # Frames captured by camera thread
_pipeline_infer_count = 0       # Frames processed by inference thread

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

        # Launch threaded pipeline:
        # 1. Camera capture thread (daemon) – grabs frames continuously
        # 2. Inference thread (daemon) – runs detection on latest frame
        # 3. SocketIO greenlet – encodes JPEG & emits to clients
        cam_thread = threading.Thread(target=_camera_capture_loop, daemon=True, name="CamThread")
        infer_thread = threading.Thread(target=_inference_loop, daemon=True, name="InferThread")
        cam_thread.start()
        infer_thread.start()
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
    """Shutdown the Raspberry Pi with a 2-second delay for UI feedback"""
    import subprocess
    import threading
    
    def delayed_shutdown():
        import time
        time.sleep(2)  # Allow UI to show shutdown message
        logger.info("Executing system shutdown...")
        subprocess.run(['sudo', 'shutdown', 'now'])
    
    logger.info("Shutdown requested via API")
    threading.Thread(target=delayed_shutdown, daemon=True).start()
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
    """Close the application: kill Chromium browser then stop the Flask server"""
    import subprocess
    import threading
    import signal
    
    def delayed_close():
        import time
        time.sleep(1)  # Allow response to reach the client
        logger.info("Killing Chromium browser...")
        try:
            subprocess.run(['pkill', '-f', 'chromium'], timeout=5)
        except Exception as e:
            logger.warning(f"Could not kill Chromium: {e}")
        
        logger.info("Stopping Flask server...")
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
    
    logger.info("Close app requested via API")
    threading.Thread(target=delayed_close, daemon=True).start()
    return jsonify({'message': 'Closing application...'}), 200

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
# WIFI API
# ----------------------------------------------------------------------------

def run_nmcli(args, timeout=10):
    """Run nmcli command and return output"""
    import subprocess
    try:
        result = subprocess.run(
            ['nmcli'] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return '', 'Command timed out', -1
    except FileNotFoundError:
        return '', 'nmcli not found (NetworkManager not installed)', -2
    except Exception as e:
        return '', str(e), -3

@app.route('/api/wifi/status', methods=['GET'])
def get_wifi_status():
    """Get current WiFi connection status"""
    try:
        # Get connection status
        stdout, stderr, code = run_nmcli(['-t', '-f', 'ACTIVE,SSID,SIGNAL,SECURITY', 'dev', 'wifi'])
        
        if code != 0:
            # Try alternative: check if we have any network connectivity
            import socket
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=2)
                connected = True
            except OSError:
                connected = False
            
            return jsonify({
                'connected': connected,
                'ssid': None,
                'signal': 0,
                'error': stderr if code != 0 else None
            }), 200
        
        # Parse nmcli output
        connected = False
        current_ssid = None
        signal = 0
        
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split(':')
                if len(parts) >= 3 and parts[0] == 'yes':
                    connected = True
                    current_ssid = parts[1]
                    signal = int(parts[2]) if parts[2].isdigit() else 0
                    break
        
        return jsonify({
            'connected': connected,
            'ssid': current_ssid,
            'signal': signal
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting WiFi status: {e}")
        return jsonify({'error': str(e), 'connected': False}), 500

@app.route('/api/wifi/scan', methods=['GET'])
def scan_wifi():
    """Scan for available WiFi networks"""
    try:
        # Rescan networks
        run_nmcli(['dev', 'wifi', 'rescan'], timeout=5)
        
        # Get list of networks
        stdout, stderr, code = run_nmcli(['-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'dev', 'wifi', 'list'])
        
        if code != 0:
            return jsonify({'error': stderr, 'networks': []}), 500
        
        networks = []
        seen_ssids = set()
        
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split(':')
                if len(parts) >= 3:
                    ssid = parts[0]
                    if ssid and ssid not in seen_ssids:
                        seen_ssids.add(ssid)
                        networks.append({
                            'ssid': ssid,
                            'signal': int(parts[1]) if parts[1].isdigit() else 0,
                            'security': parts[2] if len(parts) > 2 else 'Open',
                            'connected': parts[3] == '*' if len(parts) > 3 else False
                        })
        
        # Sort by signal strength
        networks.sort(key=lambda x: x['signal'], reverse=True)
        
        return jsonify({'networks': networks}), 200
        
    except Exception as e:
        logger.error(f"Error scanning WiFi: {e}")
        return jsonify({'error': str(e), 'networks': []}), 500

@app.route('/api/wifi/connect', methods=['POST'])
def connect_wifi():
    """Connect to a WiFi network"""
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        if not ssid:
            return jsonify({'error': 'SSID is required'}), 400
        
        logger.info(f"Connecting to WiFi: {ssid}")
        
        # Try to connect
        if password:
            stdout, stderr, code = run_nmcli(['dev', 'wifi', 'connect', ssid, 'password', password], timeout=30)
        else:
            stdout, stderr, code = run_nmcli(['dev', 'wifi', 'connect', ssid], timeout=30)
        
        if code == 0:
            logger.info(f"✅ Connected to WiFi: {ssid}")
            return jsonify({'message': f'Connected to {ssid}', 'connected': True}), 200
        else:
            logger.error(f"❌ Failed to connect to WiFi: {stderr}")
            return jsonify({'error': stderr or 'Connection failed', 'connected': False}), 400
        
    except Exception as e:
        logger.error(f"Error connecting to WiFi: {e}")
        return jsonify({'error': str(e), 'connected': False}), 500

@app.route('/api/wifi/disconnect', methods=['POST'])
def disconnect_wifi():
    """Disconnect from current WiFi network (connection only, not the device)"""
    try:
        # Get the active WiFi connection name
        stdout, stderr, code = run_nmcli(['-t', '-f', 'NAME,TYPE,DEVICE', 'connection', 'show', '--active'])
        
        active_connection = None
        for line in stdout.strip().split('\n'):
            if line and ':802-11-wireless:' in line:
                active_connection = line.split(':')[0]
                break
        
        if not active_connection:
            return jsonify({'message': 'No active WiFi connection', 'connected': False}), 200
        
        # Disconnect the connection (not the device)
        stdout, stderr, code = run_nmcli(['connection', 'down', active_connection], timeout=10)
        
        if code == 0:
            logger.info(f"✅ Disconnected from WiFi: {active_connection}")
            return jsonify({'message': f'Disconnected from {active_connection}', 'connected': False}), 200
        else:
            return jsonify({'error': stderr or 'Disconnect failed'}), 400
        
    except Exception as e:
        logger.error(f"Error disconnecting WiFi: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/wifi/saved', methods=['GET'])
def get_saved_networks():
    """Get list of saved WiFi networks"""
    try:
        stdout, stderr, code = run_nmcli(['-t', '-f', 'NAME,TYPE', 'connection', 'show'])
        
        if code != 0:
            return jsonify({'error': stderr, 'networks': []}), 500
        
        networks = []
        for line in stdout.strip().split('\n'):
            if line and ':802-11-wireless' in line:
                name = line.split(':')[0]
                if name:
                    networks.append({'name': name})
        
        return jsonify({'networks': networks}), 200
        
    except Exception as e:
        logger.error(f"Error getting saved networks: {e}")
        return jsonify({'error': str(e), 'networks': []}), 500

@app.route('/api/wifi/forget', methods=['POST'])
def forget_network():
    """Forget/delete a saved WiFi network"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Network name is required'}), 400
        
        stdout, stderr, code = run_nmcli(['connection', 'delete', name], timeout=10)
        
        if code == 0:
            logger.info(f"✅ Forgot network: {name}")
            return jsonify({'message': f'Forgot network: {name}'}), 200
        else:
            return jsonify({'error': stderr or 'Failed to forget network'}), 400
        
    except Exception as e:
        logger.error(f"Error forgetting network: {e}")
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

# ---------------------------------------------------------------------------
# THREADED PIPELINE  (Camera → Inference → Emit)
# ---------------------------------------------------------------------------
# Thread 1 – camera_capture_thread:
#     Continuously grabs frames from the camera and stores the latest one.
# Thread 2 – inference_thread:
#     Reads the latest frame, runs Hailo / NCNN / YOLO inference, annotates,
#     and stores the result.
# Background task – stream_video (socketio greenlet):
#     Encodes the latest annotated frame to JPEG, emits it via WebSocket,
#     and logs metrics + violations.
# ---------------------------------------------------------------------------

def _camera_capture_loop():
    """Producer thread: grab frames as fast as the camera delivers them."""
    global _latest_frame, _pipeline_frame_count, is_streaming
    logger.info("[CamThread] Camera capture thread started")
    while is_streaming:
        try:
            frame = camera.get_frame()
            if frame is None:
                continue
            with _latest_frame_lock:
                _latest_frame = frame
            _pipeline_frame_count += 1
        except Exception as e:
            logger.error(f"[CamThread] Error: {e}")
            import time; time.sleep(0.05)
    logger.info("[CamThread] Camera capture thread stopped")


def _inference_loop():
    """Inference thread: detect objects on the latest camera frame."""
    global _latest_detections, _latest_annotated, _pipeline_infer_count, is_streaming
    logger.info("[InferThread] Inference thread started")
    _prev_frame_id = -1
    while is_streaming:
        try:
            # Grab the most recent frame
            with _latest_frame_lock:
                frame = _latest_frame
                cur_id = _pipeline_frame_count
            if frame is None or cur_id == _prev_frame_id:
                import time; time.sleep(0.001)  # Yield briefly
                continue
            _prev_frame_id = cur_id

            detections = detector.detect(frame)
            annotated = detector.draw_detections(frame, detections)

            with _latest_result_lock:
                _latest_detections = detections
                _latest_annotated = annotated
            _pipeline_infer_count += 1
        except Exception as e:
            logger.error(f"[InferThread] Error: {e}")
            import time; time.sleep(0.05)
    logger.info("[InferThread] Inference thread stopped")


def stream_video():
    """SocketIO greenlet: encode + emit the latest annotated frame."""
    global is_streaming
    logger.info("[StreamLoop] Starting emit loop...")
    frame_count = 0
    total_detections = 0
    dropped_frames = 0
    last_fps_time = datetime.now()
    jpeg_quality = int(config.get('streaming.quality', 85))
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    process = psutil.Process(os.getpid())
    metrics_interval = max(1, int(config.get('streaming.metrics_interval', 30)))
    _prev_infer_id = -1

    while is_streaming:
        try:
            # Grab latest annotated frame + detections
            with _latest_result_lock:
                annotated_frame = _latest_annotated
                detections = list(_latest_detections)
                cur_infer_id = _pipeline_infer_count

            if annotated_frame is None or cur_infer_id == _prev_infer_id:
                # No new inference result yet — yield and retry
                socketio.sleep(0.005)
                dropped_frames += 1
                continue
            _prev_infer_id = cur_infer_id

            # JPEG encode (cv2.imencode benchmarked faster than simplejpeg on RPi5)
            jpeg_start = datetime.now()
            _, buf = cv2.imencode('.jpg', annotated_frame, encode_params)
            jpeg_bytes = buf.tobytes()
            jpeg_end = datetime.now()

            # Emit to clients
            frame_base64 = base64.b64encode(jpeg_bytes).decode('utf-8')
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

            # Violation logging (stub)
            try:
                stop_dets = [d for d in detections if d.get('class_name', '').lower() in ('stop', 'stop_sign')]
                if stop_dets:
                    top = max(stop_dets, key=lambda d: d.get('confidence', 0))
                    if top.get('confidence', 0) >= max(0.85, config.get('detection.confidence', 0.5)):
                        event_time = datetime.now()
                        event = {
                            'id': f"evt_{event_time.strftime('%Y%m%d_%H%M%S')}_{frame_count:06d}",
                            'timestamp': event_time.isoformat(),
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

            # Metrics (only every N frames to reduce psutil overhead)
            frame_count += 1
            total_detections += len(detections)
            if frame_count % metrics_interval == 0:
                now = datetime.now()
                elapsed = (now - last_fps_time).total_seconds()
                fps = (frame_count / elapsed) if elapsed > 0 else 0.0
                inference_time_ms = 0.0  # measured inside inference thread in future
                camera_frame_time_ms = 0.0  # measured inside camera thread in future
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

            # Yield to other greenlets (no artificial FPS cap)
            socketio.sleep(0)

        except Exception as e:
            logger.error(f"[StreamLoop] Error: {e}")
            socketio.sleep(0.1)

    logger.info("[StreamLoop] Emit loop stopped")
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
