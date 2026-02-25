

#!/usr/bin/env python3
"""
Sign Detection System - Main Flask Application
Serves both frontend (HTML/CSS/JS) and backend API
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, disconnect
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
from pairing import PairingManager, get_pairing_manager, HOTSPOT_IP, HOTSPOT_DOMAIN
from hotspot import HotspotManager, get_hotspot_manager
import psutil

# For QR code image generation
import io
import qrcode
from flask import send_file

# ----------------------------------------------------------------------------
# HOTSPOT QR CODE IMAGE API (moved for clarity)
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
        qr_data = f"http://{ip}:5000/"
    else:
        # WiFi QR code format
        qr_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    img = qrcode.make(qr_data)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=False, download_name=f"hotspot_{qr_type}_qr.png")

# Initialize Flask app
app = Flask(__name__,
            static_folder='../frontend/static',
            static_url_path='/static',
            template_folder='../frontend/templates')

# Enable CORS for development
CORS(app)

# Initialize SocketIO for real-time video streaming
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=True)
# WebSocket session pairing state
connected_sessions = {}

# ============================================================================
# WEB ROUTES (Serve Frontend)
# ============================================================================

# ============================================================================
# SOCKETIO EVENTS (WebSocket Authentication)
# ============================================================================

@socketio.on('connect')
def ws_connect():
    # Accept connection, but require authentication for sensitive actions
    emit('connected', {'message': 'WebSocket connected'})

@socketio.on('authenticate')
def ws_authenticate(data):
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
    connected_sessions.pop(request.sid, None)

# Example: Restrict sensitive command (system control)
@socketio.on('shutdown')
def ws_shutdown(data):
    session_token = connected_sessions.get(request.sid)
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('error', {'message': 'Authentication required for shutdown'})
        return
    # Only paired device can shutdown
    shutdown_system()

# Example: Restrict reboot command
@socketio.on('reboot')
def ws_reboot(data):
    session_token = connected_sessions.get(request.sid)
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('error', {'message': 'Authentication required for reboot'})
        return
    reboot_system()

# Example: Restrict config update
@socketio.on('update_config')
def ws_update_config(data):
    session_token = connected_sessions.get(request.sid)
    if not session_token or not pairing_manager.validate_session(session_token):
        emit('error', {'message': 'Authentication required for config update'})
        return
    update_config()

# All other events (e.g., video streaming, status) remain unrestricted

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

# Pairing and Hotspot managers (initialized after config)
pairing_manager = None
hotspot_manager = None

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
    global camera, detector, display_controller, is_streaming, pairing_manager, hotspot_manager
    try:
        logger.info("Initializing pairing manager...")
        pairing_manager = get_pairing_manager(data_dir='data')
        
        # Set disconnect callback to emit socketio event
        def disconnect_device(session_token):
            """Disconnect a paired device by session token"""
            socketio.emit('force_disconnect', {'reason': 'New device paired'}, room=session_token)
            logger.info(f"📤 Sent disconnect signal for session: {session_token[:8]}...")
        
        pairing_manager.set_disconnect_callback(disconnect_device)
        
        logger.info("Initializing hotspot manager...")
        hotspot_manager = get_hotspot_manager(config=config)
        
        # Hotspot will only start when toggled ON by user in UI
        logger.info("Hotspot auto-start is disabled. Use the UI toggle to enable hotspot.")
        
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

# ----------------------------------------------------------------------------
# PAIRING API
# ----------------------------------------------------------------------------

def is_local_request():
    """Check if request is from local machine (touchscreen)"""
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
        
        logger.info(f"🔑 Pairing token generated: {data['token']}")
        
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
            logger.info(f"✅ Device paired via API: {device_info['device_name']}")
            
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
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Unpairing can only be done from touchscreen'}), 403
    
    try:
        if pairing_manager.unpair():
            logger.info("🔓 Device unpaired via API")
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
    # For now, redirect to main page with token
    # Phase 5 will add a dedicated mobile pairing UI
    return render_template('index.html')

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
def toggle_hotspot():
    """
    Toggle hotspot enabled state (for settings UI).
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Hotspot control requires touchscreen access'}), 403
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        config.set('hotspot.enabled', enabled, save=True)
        hotspot_manager._enabled = enabled
        logger.info(f"Hotspot enabled set to {enabled}")
        return jsonify({'success': True, 'enabled': enabled}), 200
    except Exception as e:
        logger.error(f"Error toggling hotspot: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/hotspot/start', methods=['POST'])
def start_hotspot():
    """
    Start the WiFi hotspot.
    Only accessible from touchscreen (local).
    Checks hotspot.enabled config.
    """
    if not is_local_request():
        return jsonify({'error': 'Hotspot control requires touchscreen access'}), 403
    if not config.get('hotspot.enabled', True):
        return jsonify({'error': 'Hotspot is disabled in settings'}), 403
    try:
        # Check if WiFi is connected and prompt user (frontend handles prompt)
        wifi_status = hotspot_manager.is_wifi_connected() if hasattr(hotspot_manager, 'is_wifi_connected') else False
        if wifi_status:
            return jsonify({'prompt': 'Hotspot will disconnect WiFi. Proceed?'}), 200
        result = hotspot_manager.start()
        if result['success']:
            logger.info(f"📶 Hotspot started via API: {result.get('ssid')}")
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
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Hotspot control requires touchscreen access'}), 403
    
    try:
        result = hotspot_manager.stop()
        
        if result['success']:
            logger.info("📴 Hotspot stopped via API")
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
def set_hotspot_credentials():
    """
    Set custom hotspot credentials.
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Credential changes require touchscreen access'}), 403
    
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
def regenerate_hotspot_credentials():
    """
    Generate new random hotspot credentials.
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Credential regeneration requires touchscreen access'}), 403
    
    try:
        result = hotspot_manager.regenerate_credentials()
        
        if result['success']:
            logger.info(f"🔑 Hotspot credentials regenerated: {result.get('ssid')}")
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error regenerating hotspot credentials: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/hotspot/autostart', methods=['POST'])
def set_hotspot_autostart():
    """
    Set hotspot auto-start preference.
    Only accessible from touchscreen (local).
    """
    if not is_local_request():
        return jsonify({'error': 'Auto-start setting requires touchscreen access'}), 403
    
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
