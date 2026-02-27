

#!/usr/bin/env python3
"""
Sign Detection System - Main Flask Application
Serves both frontend (HTML/CSS/JS) and backend API
"""

# ============================================================================
# IMPORTS
# ============================================================================

from flask import Flask, render_template, jsonify, request, send_from_directory, send_file, redirect, abort
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
import os
import sys
import io
import logging
import threading
import time
import json
import cv2
import base64
import psutil
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
from config import Config
from camera import Camera
from detector import Detector
from display import DisplayController
from metrics_logger import MetricsLogger
from violations_logger import ViolationsLogger
from display import DisplayController
from tts import TTSEngine

from bluetooth_mgmt import get_bluetooth_manager
from pairing import get_pairing_manager, HOTSPOT_IP
from hotspot import get_hotspot_manager

try:
    import qrcode
except ImportError:
    qrcode = None

# ============================================================================
# APP INITIALIZATION
# ============================================================================

# Set project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

app = Flask(__name__,
            static_folder='../frontend/static',
            static_url_path='/static',
            template_folder='../frontend/templates')

# Enable CORS for development
CORS(app)

# Initialize SocketIO for real-time video streaming
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=True)

# WebSocket session pairing state: maps sid -> session_token
connected_sessions = {}

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

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

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

camera = None
detector = None
display_controller = None
tts_engine = None
is_streaming = True  # Always streaming in backend
metrics_logger = MetricsLogger(log_dir='data/logs', prefix='metrics', interval=1)
violations_logger = ViolationsLogger(log_dir='data/logs', prefix='violations')

# Pairing and Hotspot managers (initialized in initialize())
pairing_manager = None
hotspot_manager = None
bluetooth_manager = None

# Phone audio relay: when True, TTS alerts are emitted via socket to the paired phone
phone_audio_enabled = False

# Lifecycle flag: True only after initialize() completes and server is about to run
app_ready = False
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
    global camera, detector, display_controller, tts_engine
    
    # Guard: skip live updates if system isn't fully initialized yet
    if not app_ready:
        logger.debug("Config changed during startup, skipping live update")
        return
    
    logger.info("Configuration changed, updating components...")
    
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
            logger.info("Camera settings changed, restarting camera...")
            camera.stop()
            camera = Camera(config)
            camera.start()
            logger.info("Camera restarted with new settings")
        
        # Reload detector if model or confidence changed
        if detector_changed and detector:
            logger.info("Detector settings changed, reloading detector...")
            detector = Detector(config)
            logger.info("Detector reloaded with new settings")
        
        # Update display brightness if changed
        if display_changed and display_controller:
            new_brightness = new_config.get('display', {}).get('brightness', 100)
            old_brightness = old_config.get('display', {}).get('brightness', 100)
            if new_brightness != old_brightness:
                logger.info(f"Display brightness changed: {old_brightness}% -> {new_brightness}%")
                display_controller.set_brightness(new_brightness)
        
        # Check TTS settings changes
        tts_changed = (
            old_config.get('tts') != new_config.get('tts')
        )
        
        # Update TTS engine if settings changed
        if tts_changed and tts_engine:
            logger.info("TTS settings changed, updating TTS engine...")
            tts_engine.enabled = new_config.get('tts', {}).get('enabled', True)
            tts_engine.speech_rate = new_config.get('tts', {}).get('speech_rate', 160)
            tts_engine.volume = new_config.get('tts', {}).get('volume', 1.0)
            tts_engine.cooldown_seconds = new_config.get('tts', {}).get('cooldown_seconds', 10)
            logger.info("TTS settings updated")
        
        # Broadcast changes to all connected clients
        socketio.emit('config_updated', {
            'timestamp': datetime.now().isoformat(),
            'config': new_config
        })
        
        logger.info("Configuration update complete")
        
    except Exception as e:
        logger.error(f"Error updating components after config change: {e}")

# NOTE: Config change callback is registered at the end of initialize()
# to avoid firing during startup when components aren't ready yet.

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize():
    """Initialize camera and detector and start background streaming"""
    global camera, detector, display_controller, tts_engine, is_streaming, pairing_manager, hotspot_manager, bluetooth_manager

    try:
        logger.info("Initializing pairing manager...")
        pairing_manager = get_pairing_manager(data_dir='data')
        
        # Set disconnect callback to emit socketio event
        def disconnect_device(session_token):
            """Disconnect a paired device by session token.
            Looks up the sid from connected_sessions and emits force_disconnect."""
            for sid, tok in list(connected_sessions.items()):
                if tok == session_token:
                    socketio.emit('force_disconnect', {'reason': 'New device paired'}, to=sid)
                    try:
                        socketio.server.disconnect(sid)
                    except Exception:
                        pass
                    connected_sessions.pop(sid, None)
                    logger.info(f"Disconnected session {sid} for token: {session_token[:8]}...")
                    return
            logger.info(f"No active session found for token: {session_token[:8]}...")
        
        pairing_manager.set_disconnect_callback(disconnect_device)
        
        logger.info("Initializing hotspot manager...")
        hotspot_manager = get_hotspot_manager(config=config)
        
        # Explicitly disable hotspot auto-start
        if hasattr(hotspot_manager, 'set_auto_start'):
            hotspot_manager.set_auto_start(False)
        logger.info("Hotspot auto-start is disabled. Use the UI toggle to enable hotspot.")
        
        logger.info("Initializing bluetooth manager...")
        bluetooth_manager = get_bluetooth_manager(config=config)
        
        logger.info("Initializing display controller...")
        display_controller = DisplayController(config)
        
        logger.info("Initializing camera...")
        camera = Camera(config)
        
        logger.info("Initializing detector...")
        detector = Detector(config)
        
        logger.info("Initializing TTS engine...")
        tts_engine = TTSEngine(config)

        # Register TTS callback: relay alerts to phone when phone audio is enabled
        def on_tts_speak(text, label, priority):
            if phone_audio_enabled:
                socketio.emit('tts_alert', {
                    'text': text,
                    'label': label,
                    'priority': priority
                })
                logger.debug(f"Phone audio relay: [{label}] \"{text}\"")

        tts_engine.set_on_speak_callback(on_tts_speak)

        if tts_engine.is_ready():
            tts_engine.speak("System ready. Driver assistance activated.")
        
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
        
        # Register config change callback now that all components are ready
        config.register_change_callback(on_config_change)
        logger.info("Config change callback registered")
        
        return True
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False

# ============================================================================
# WEB ROUTES (Serve Frontend)
# ============================================================================

@app.route('/')
def index():
    """Serve the main application page (RPi touchscreen) or redirect mobile to pair"""
    if is_local_request():
        return render_template('index.html', is_touchscreen=True)
    # External device hitting root — redirect to mobile view if paired
    session_token = request.headers.get('X-Session-Token') or request.cookies.get('session_token')
    if session_token and pairing_manager and pairing_manager.validate_session(session_token):
        return redirect('/mobile')
    return redirect('/pair')



@app.route('/mobile')
def mobile_page():
    """Serve the mobile app page (after pairing)"""
    return render_template('mobile.html')

# ============================================================================
# CAPTIVE PORTAL DETECTION
# Phones check these URLs when connecting to WiFi. Redirect to /pair.
# ============================================================================

# Android captive portal checks
@app.route('/generate_204')
@app.route('/gen_204')
def captive_android():
    return redirect('/pair', code=302)

# iOS / macOS captive portal checks
@app.route('/hotspot-detect.html')
@app.route('/library/test/success.html')
def captive_ios():
    return redirect('/pair', code=302)

# Windows captive portal check
@app.route('/connecttest.txt')
@app.route('/ncsi.txt')
def captive_windows():
    return redirect('/pair', code=302)

# Microsoft captive portal
@app.route('/redirect')
def captive_redirect():
    return redirect('/pair', code=302)

@app.route('/<path:path>')
def catch_all(path):
    """Catch-all: serve static files, or redirect external requests to /pair"""
    if path.startswith('static/') or path.startswith('api/'):
        if path.startswith('static/'):
            return send_from_directory(app.static_folder, path.replace('static/', '', 1))
        abort(404)
    
    # Known app routes — serve normally
    if path in ('pair', 'mobile'):
        return redirect(f'/{path}')
    
    # Local (touchscreen) — serve the app
    if is_local_request():
        return render_template('index.html', is_touchscreen=True)
    
    # External device hitting unknown path — likely captive portal probe
    return redirect('/pair')

# ============================================================================
# SOCKETIO EVENTS (WebSocket Authentication)
# ============================================================================

@socketio.on('connect')
def ws_connect():
    """Accept connection, but require authentication for sensitive actions"""
    emit('connected', {'message': 'WebSocket connected'})

@socketio.on('authenticate')
def ws_authenticate(data):
    """Authenticate a WebSocket connection with a session token"""
    session_token = data.get('session_token')
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('auth_failed', {'message': 'Invalid or missing session token'})
        disconnect()
        return
    # Store session token for this sid
    connected_sessions[request.sid] = session_token
    emit('auth_success', {'message': 'Authenticated'})

@socketio.on('disconnect')
def ws_disconnect():
    """Clean up session tracking on disconnect"""
    connected_sessions.pop(request.sid, None)

# Restrict sensitive commands to authenticated (paired) devices
@socketio.on('shutdown')
def ws_shutdown(data):
    session_token = connected_sessions.get(request.sid)
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('error', {'message': 'Authentication required for shutdown'})
        return
    shutdown_system()

@socketio.on('reboot')
def ws_reboot(data):
    session_token = connected_sessions.get(request.sid)
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('error', {'message': 'Authentication required for reboot'})
        return
    reboot_system()

@socketio.on('update_config')
def ws_update_config(data):
    session_token = connected_sessions.get(request.sid)
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('error', {'message': 'Authentication required for config update'})
        return
    update_config()

# ============================================================================
# PAIRING HELPERS (must be defined before API routes that use @require_pairing)
# ============================================================================

def is_local_request():
    """Check if request is from local machine (touchscreen)"""
    if pairing_manager is None:
        return request.remote_addr in ('127.0.0.1', '::1', 'localhost')
    return pairing_manager.is_local_request(request.remote_addr)

def require_pairing(f):
    """
    Decorator to require pairing for remote requests.
    Local (touchscreen) requests always bypass.
    """
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        # Touchscreen bypass
        if is_local_request():
            return f(*args, **kwargs)
        
        # Check session token in header or cookie
        session_token = request.headers.get('X-Session-Token') or request.cookies.get('session_token')
        
        if not session_token:
            return jsonify({'error': 'Authentication required', 'code': 'NO_TOKEN'}), 401
        
        if not pairing_manager.validate_session(session_token):
            return jsonify({'error': 'Invalid or expired session', 'code': 'INVALID_TOKEN'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    try:
        model_info = detector.get_info() if detector else {'engine': 'unknown', 'model': 'not loaded'}
        tts_info = tts_engine.get_info() if tts_engine else {'enabled': False, 'ready': False}
        
        status = {
            'camera': camera.is_running() if camera else False,
            'detector': detector.is_loaded() if detector else False,
            'streaming': is_streaming,
            'engine': model_info['engine'],
            'model': model_info['model'],
            'tts': tts_info,
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shutdown', methods=['POST'])
@require_pairing
def shutdown_system():
    """Shutdown the Raspberry Pi with a 2-second delay for UI feedback.
    Only allowed from local (touchscreen) requests."""
    if not is_local_request():
        return jsonify({'error': 'Shutdown can only be triggered from the touchscreen'}), 403
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
@require_pairing
def reboot_system():
    """Reboot the Raspberry Pi using detached process.
    Only allowed from local (touchscreen) requests."""
    if not is_local_request():
        return jsonify({'error': 'Reboot can only be triggered from the touchscreen'}), 403
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
@require_pairing
def close_app():
    """Close the application: kill Chromium browser then stop the Flask server.
    Only allowed from local (touchscreen) requests."""
    if not is_local_request():
        return jsonify({'error': 'Close app can only be triggered from the touchscreen'}), 403
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
@require_pairing
def update_config():
    """
    Update configuration
    Changes are saved to config.json and automatically reflected in the system
    """
    try:
        data = request.get_json()
        
        # Update configuration (this will trigger callbacks and save to file)
        config.update(data, save=True)
        
        logger.info(f"Configuration updated via API: {list(data.keys())}")
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'config': config.get_all(),
            'metadata': config.get_metadata()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
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
            logger.info("Configuration reloaded from file")
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
        logger.error(f"Error reloading config: {e}")
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
        import time
        
        # Get saved networks first to flag them in the UI
        stdout, stderr, code = run_nmcli(['-t', '-f', 'NAME,TYPE', 'connection', 'show'])
        saved_ssids = set()
        if code == 0:
            for line in stdout.strip().split('\n'):
                if line and ':802-11-wireless' in line:
                    name = line.split(':')[0]
                    if name:
                        saved_ssids.add(name)
        
        # Rescan networks
        run_nmcli(['dev', 'wifi', 'rescan'], timeout=5)
        # Give the hardware a couple of seconds to actually update the BSSID lists
        time.sleep(2)
        
        # Get list of networks
        stdout, stderr, code = run_nmcli(['-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'dev', 'wifi', 'list'])
        
        if code != 0:
            return jsonify({'error': stderr, 'networks': []}), 500
        
        networks = []
        seen_ssids = set()
        
        for line in stdout.strip().split('\n'):
            if line:
                # `nmcli -t` escapes colons in SSID with a backslash if present. Unescaping is complex.
                # Just split by colon. A limitation is colons in SSID name will break parsing if not handled robustly
                # A safer split is separating by unescaped colons, or just matching parts from the end.
                # However, basic parsing is: SSID:SIGNAL:SECURITY:IN-USE
                
                # Use maxsplit to handle potential colons in SSID (although nmcli escapes them, this is safer)
                # First check if the line starts with a colon (empty SSID)
                if line.startswith(':'):
                    continue
                    
                # Find the last 3 colons which separate SIGNAL, SECURITY, IN-USE
                parts = []
                remaining = line
                for _ in range(3):
                    idx = remaining.rfind(':')
                    if idx != -1:
                        parts.insert(0, remaining[idx+1:])
                        remaining = remaining[:idx]
                    else:
                        break
                
                if len(parts) == 3:
                    ssid = remaining
                    signal_str, security, in_use = parts
                    
                    # Unescape colons in SSID
                    ssid = ssid.replace('\\:', ':')
                    
                    if ssid and ssid != '--' and ssid not in seen_ssids:
                        seen_ssids.add(ssid)
                        networks.append({
                            'ssid': ssid,
                            'signal': int(signal_str) if signal_str.isdigit() else 0,
                            'security': security if security and security != '--' else 'Open',
                            'connected': in_use == '*',
                            'saved': ssid in saved_ssids
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
        
        
        if not ssid or ssid == 'null' or ssid == 'undefined':
            return jsonify({'error': 'Valid SSID is required'}), 400
        
        logger.info(f"Connecting to WiFi: {ssid}")
        
        # Try to connect
        if password:
            stdout, stderr, code = run_nmcli(['dev', 'wifi', 'connect', ssid, 'password', password], timeout=30)
        else:
            stdout, stderr, code = run_nmcli(['dev', 'wifi', 'connect', ssid], timeout=30)
        
        if code == 0:
            logger.info(f"Connected to WiFi: {ssid}")
            # Save the connected SSID to config
            config.set('wifi.last_ssid', ssid, save=True)
            return jsonify({'message': f'Connected to {ssid}', 'connected': True}), 200
        else:
            logger.error(f"Failed to connect to WiFi: {stderr}")
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
            logger.info(f"Disconnected from WiFi: {active_connection}")
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
            logger.info(f"Forgot network: {name}")
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

# ----------------------------------------------------------------------------
# AUDIO DEVICE CHECK API
# ----------------------------------------------------------------------------

@app.route('/api/audio/check', methods=['GET'])
def check_audio_status():
    """
    Check whether any audio output device is available.
    Returns combined status of Bluetooth audio and phone audio relay.
    Used by the frontend to enforce audio-required gate on startup.
    """
    try:
        # 1. Check Bluetooth audio
        bt_info = {'enabled': False, 'connected': False, 'device': None}
        if bluetooth_manager and bluetooth_manager.enabled:
            bt_status = bluetooth_manager.status()
            bt_info = {
                'enabled': True,
                'connected': bt_status.get('connected', False),
                'device': bt_status.get('device') if bt_status.get('connected') else None
            }

        # 2. Check paired mobile device + phone audio toggle
        phone_info = {'paired': False, 'audio_enabled': False}
        if pairing_manager:
            pair_status = pairing_manager.get_status()
            is_paired = pair_status.get('is_paired', False)
            phone_info = {
                'paired': is_paired,
                'audio_enabled': phone_audio_enabled if is_paired else False
            }

        audio_ready = bt_info['connected'] or (phone_info['paired'] and phone_info['audio_enabled'])

        return jsonify({
            'audio_ready': audio_ready,
            'bluetooth': bt_info,
            'phone_audio': phone_info
        }), 200

    except Exception as e:
        logger.error(f"Error checking audio status: {e}")
        return jsonify({'error': str(e), 'audio_ready': False}), 500

# ----------------------------------------------------------------------------
# PHONE AUDIO RELAY API
# ----------------------------------------------------------------------------

@app.route('/api/phone-audio/status', methods=['GET'])
@require_pairing
def get_phone_audio_status():
    """Get current phone audio relay status."""
    return jsonify({'enabled': phone_audio_enabled}), 200


@app.route('/api/phone-audio/toggle', methods=['POST'])
@require_pairing
def toggle_phone_audio():
    """Enable or disable phone audio relay."""
    global phone_audio_enabled
    try:
        data = request.get_json()
        phone_audio_enabled = bool(data.get('enabled', False))
        logger.info(f"Phone audio relay {'enabled' if phone_audio_enabled else 'disabled'}")
        socketio.emit('phone_audio_state', {'enabled': phone_audio_enabled})
        return jsonify({'success': True, 'enabled': phone_audio_enabled}), 200
    except Exception as e:
        logger.error(f"Error toggling phone audio: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-audio/test', methods=['POST'])
@require_pairing
def test_phone_audio():
    """Send a test TTS alert to the paired phone."""
    try:
        test_text = 'This is a test alert. Phone audio is working.'
        socketio.emit('tts_alert', {
            'text': test_text,
            'label': 'test',
            'priority': 0
        })
        logger.info("Phone audio test alert sent")
        return jsonify({'success': True, 'text': test_text}), 200
    except Exception as e:
        logger.error(f"Error sending phone audio test: {e}")
        return jsonify({'error': str(e)}), 500

# ----------------------------------------------------------------------------
# PAIRING API
# ----------------------------------------------------------------------------

@app.route('/api/pair/generate', methods=['POST'])
def generate_pairing_token():
    """
    Generate a new pairing token and QR data.
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Pairing can only be initiated from touchscreen'}), 403
    
    try:
        port = config.get('port', 5000)
        domain = hotspot_manager.get_domain() if hotspot_manager else None
        data = pairing_manager.generate_pairing_data(port=port, domain=domain)
        
        logger.info(f"Pairing token generated: {data['token']}")
        
        return jsonify({
            'success': True,
            'token': data['token'],
            'url': data['url'],
            'ip_url': data.get('ip_url'),
            'qr_content': data['qr_content'],
            'ip': data['ip'],
            'domain': data.get('domain'),
            'port': data['port']
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating pairing token: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pair/status', methods=['GET'])
def get_pairing_status():
    """
    Get current pairing status.
    Shows different info based on local vs remote request.
    """
    try:
        status = pairing_manager.get_status()
        
        # Add whether this is a local request
        status['is_local'] = is_local_request()
        
        # For remote requests, check if they're the paired device
        if not is_local_request():
            session_token = request.headers.get('X-Session-Token') or request.cookies.get('session_token')
            status['is_paired_device'] = pairing_manager.validate_session(session_token) if session_token else False
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting pairing status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pair/validate', methods=['POST'])
def validate_pairing_token():
    """
    Validate a pairing token from phone/tablet.
    Called when phone scans QR code or enters token manually.
    """
    try:
        data = request.get_json()
        token = data.get('token', '').strip().upper()
        
        if not token:
            return jsonify({'success': False, 'message': 'Token is required'}), 400
        
        # Get device info
        device_info = {
            'device_id': data.get('device_id'),
            'device_name': data.get('device_name', 'Unknown Device'),
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # Validate and pair
        result = pairing_manager.validate_and_pair(token, device_info)
        
        if result['success']:
            logger.info(f"Device paired via API: {device_info['device_name']}")
            
            # Also emit event for touchscreen to update UI
            socketio.emit('device_paired', {
                'device_name': device_info['device_name'],
                'timestamp': datetime.now().isoformat()
            })
            
            response = jsonify(result)
            # Set session token as cookie too
            response.set_cookie('session_token', result['session_token'], 
                              httponly=True, samesite='Lax', max_age=31536000)  # 1 year
            return response, 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error validating pairing token: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/pair/unpair', methods=['POST'])
def unpair_device():
    """
    Unpair the currently paired device.
    Accessible from touchscreen (local) or from the paired mobile device.
    """
    if not is_local_request():
        # Also allow the paired mobile device to unpair itself
        session_token = request.headers.get('X-Session-Token') or request.cookies.get('session_token')
        if not session_token or not pairing_manager.validate_session(session_token):
            return jsonify({'error': 'Unpairing requires local access or valid session'}), 403
    
    try:
        if pairing_manager.unpair():
            logger.info("Device unpaired via API")
            socketio.emit('device_unpaired', {
                'timestamp': datetime.now().isoformat()
            })
            return jsonify({'success': True, 'message': 'Device unpaired'}), 200
        else:
            return jsonify({'success': False, 'message': 'No device was paired'}), 200
        
    except Exception as e:
        logger.error(f"Error unpairing device: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/pair')
def pair_landing_page():
    """
    Mobile landing page for pairing.
    Accessed when phone scans QR code.
    """
    token = request.args.get('token', '')
    return render_template('pair.html')

@app.route('/api/pair/qr')
def get_pairing_qr():
    """
    Serve a QR code image for device pairing.
    Query params:
        token: pairing token (required)
    """
    token = request.args.get('token', '')
    if not token:
        return jsonify({'error': 'Token is required'}), 400
    
    # Build the pairing URL explicitly with IP to avoid DNS_PROBE_FINISHED_NXDOMAIN
    port = config.get('port', 5000)
    qr_data = f"http://{HOTSPOT_IP}:{port}/pair?token={token}"
    
    if qrcode is None:
        return jsonify({'error': 'qrcode library not installed'}), 500
    
    img = qrcode.make(qr_data)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=False, download_name=f"pair_{token}_qr.png")

# ----------------------------------------------------------------------------
# HOTSPOT API
# ----------------------------------------------------------------------------

@app.route('/api/hotspot/status', methods=['GET'])
def get_hotspot_status():
    """Get current hotspot status"""
    try:
        status = hotspot_manager.get_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting hotspot status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/hotspot/toggle', methods=['POST'])
@require_pairing
def toggle_hotspot():
    """
    Toggle hotspot enabled state (for settings UI).
    """
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        config.set('pairing.enabled', enabled, save=True)
        hotspot_manager._enabled = enabled
        logger.info(f"Hotspot enabled set to {enabled}")
        return jsonify({'success': True, 'enabled': enabled}), 200
    except Exception as e:
        logger.error(f"Error toggling hotspot: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/hotspot/start', methods=['POST'])
@require_pairing
def start_hotspot():
    """
    Start the WiFi hotspot.
    Checks pairing.enabled config.
    """
    if not config.get('pairing.enabled', True):
        return jsonify({'error': 'Hotspot is disabled in settings'}), 403
    try:
        data = request.get_json(silent=True) or {}
        force = data.get('force', False)
        
        # Regenerate credentials to ensure old devices cannot auto-connect (enforces 1-device limit)
        hotspot_manager.regenerate_credentials()

        # Check if WiFi is connected and prompt user (frontend handles prompt)
        if not force:
            wifi_status = hotspot_manager.is_wifi_connected() if hasattr(hotspot_manager, 'is_wifi_connected') else False
            if wifi_status:
                return jsonify({'prompt': 'Hotspot will disconnect WiFi. Proceed?'}), 200
                
        result = hotspot_manager.start()
        if result['success']:
            logger.info(f"Hotspot started via API: {result.get('ssid')}")
            socketio.emit('hotspot_started', {
                'ssid': result.get('ssid'),
                'ip': result.get('ip'),
                'timestamp': datetime.now().isoformat()
            })
        return jsonify(result), 200 if result['success'] else 500
    except Exception as e:
        logger.error(f"Error starting hotspot: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/hotspot/stop', methods=['POST'])
def stop_hotspot():
    """
    Stop the WiFi hotspot.
    """
    
    try:
        result = hotspot_manager.stop()
        
        if result['success']:
            logger.info("Hotspot stopped via API")
            socketio.emit('hotspot_stopped', {
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error stopping hotspot: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/hotspot/credentials', methods=['GET'])
def get_hotspot_credentials():
    """Get hotspot SSID and password"""
    try:
        creds = hotspot_manager.get_credentials()
        status = hotspot_manager.get_status()
        return jsonify({
            **creds,
            'active': status['active'],
            'ip': HOTSPOT_IP
        }), 200
    except Exception as e:
        logger.error(f"Error getting hotspot credentials: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hotspot/credentials', methods=['POST'])
@require_pairing
def set_hotspot_credentials():
    """
    Set custom hotspot credentials.
    """
    
    try:
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password')
        
        result = hotspot_manager.set_credentials(ssid=ssid, password=password)
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error setting hotspot credentials: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hotspot/regenerate', methods=['POST'])
@require_pairing
def regenerate_hotspot_credentials():
    """
    Generate new random hotspot credentials.
    """
    
    try:
        result = hotspot_manager.regenerate_credentials()
        
        if result['success']:
            logger.info(f"Hotspot credentials regenerated: {result.get('ssid')}")
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error regenerating hotspot credentials: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hotspot/autostart', methods=['POST'])
@require_pairing
def set_hotspot_autostart():
    """
    Set hotspot auto-start preference.
    """
    
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        result = hotspot_manager.set_auto_start(enabled)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error setting hotspot auto-start: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hotspot/clients', methods=['GET'])
def get_hotspot_clients():
    """Get list of connected hotspot clients"""
    try:
        clients = hotspot_manager.get_connected_clients()
        return jsonify({
            'count': len(clients),
            'clients': clients
        }), 200
    except Exception as e:
        logger.error(f"Error getting hotspot clients: {e}")
        return jsonify({'error': str(e), 'clients': []}), 500

# ----------------------------------------------------------------------------
# HOTSPOT QR CODE API
# ----------------------------------------------------------------------------

@app.route('/api/hotspot/qr')
def get_hotspot_qr():
    """
    Serve QR code image for WiFi or webapp access.
    Query params:
        type: 'wifi' or 'webapp' (default: wifi)
    """
    qr_type = request.args.get('type', 'wifi')
    creds = hotspot_manager.get_credentials()
    ip = creds.get('ip', HOTSPOT_IP)
    ssid = creds.get('ssid')
    password = creds.get('password')
    if qr_type == 'webapp':
        # Port 80 redirect is set up by start.sh, so use clean URL without port
        qr_data = f"http://{ip}/"
    else:
        # WiFi QR code format
        qr_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    
    if qrcode is None:
        return jsonify({'error': 'qrcode library not installed'}), 500
    
    img = qrcode.make(qr_data)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=False, download_name=f"hotspot_{qr_type}_qr.png")

# ============================================================================
# BLUETOOTH API
# ============================================================================

@app.route('/api/bluetooth/status', methods=['GET'])
def get_bluetooth_status():
    """Get current Bluetooth connection status"""
    try:
        if not bluetooth_manager or not bluetooth_manager.enabled:
            return jsonify({'enabled': False, 'connected': False}), 200
        status = bluetooth_manager.status()
        status['enabled'] = True
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting Bluetooth status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bluetooth/scan', methods=['GET'])
def scan_bluetooth():
    """Scan for available Bluetooth devices"""
    try:
        if not bluetooth_manager or not bluetooth_manager.enabled:
            return jsonify({'error': 'Bluetooth is disabled'}), 400
        devices = bluetooth_manager.scan(duration=5)
        return jsonify({'devices': devices}), 200
    except Exception as e:
        logger.error(f"Error scanning Bluetooth: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bluetooth/connect', methods=['POST'])
@require_pairing
def connect_bluetooth():
    """Connect to a Bluetooth device"""
    try:
        if not bluetooth_manager or not bluetooth_manager.enabled:
            return jsonify({'error': 'Bluetooth is disabled'}), 400
            
        data = request.get_json()
        mac = data.get('mac')
        if not mac:
            return jsonify({'error': 'MAC address is required'}), 400
            
        success, message = bluetooth_manager.connect(mac)
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 500
    except Exception as e:
        logger.error(f"Error connecting Bluetooth: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bluetooth/disconnect', methods=['POST'])
@require_pairing
def disconnect_bluetooth():
    """Disconnect from a Bluetooth device"""
    try:
        if not bluetooth_manager or not bluetooth_manager.enabled:
            return jsonify({'error': 'Bluetooth is disabled'}), 400
            
        data = request.get_json()
        mac = data.get('mac')
        if not mac:
            return jsonify({'error': 'MAC address is required'}), 400
            
        success, message = bluetooth_manager.disconnect(mac)
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 500
    except Exception as e:
        logger.error(f"Error disconnecting Bluetooth: {e}")
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

            # --- TTS Alert ---
            # Pass detections to TTS engine; it picks the highest-priority
            # alert, checks cooldowns, and queues speech on its own thread.
            if tts_engine:
                tts_engine.process_detections(detections)
            # Simple example: derive and log violation events (stub)
            # In a real implementation, this would use tracked vehicles, signal state, and rules.
            # Here we log a synthetic violation when a STOP sign is detected with high confidence.
            
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
        
        # Mark system as fully ready — config callbacks can now broadcast
        app_ready = True
        
        try:
            socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            if tts_engine:
                tts_engine.stop()
            if camera:
                camera.stop()
            logger.info("Goodbye!")
    else:
        logger.error("Failed to initialize system. Exiting.")
        sys.exit(1)
