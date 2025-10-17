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
is_streaming = True  # Always streaming in backend

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
        status = {
            'camera': camera.is_running() if camera else False,
            'detector': detector.is_loaded() if detector else False,
            'streaming': is_streaming,
            'model': config.get('detection.model', 'Unknown'),
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

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent log entries"""
    try:
        log_file = config.get('logging.file', 'data/logs/app.log')
        limit = request.args.get('limit', 100, type=int)
        
        if not os.path.exists(log_file):
            return jsonify({'logs': []}), 200
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_logs = lines[-limit:]
        
        return jsonify({'logs': recent_logs}), 200
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'sign-detection'}), 200

# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("Client connected via WebSocket")
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected from WebSocket")

def stream_video():
    """Stream video frames with detections to connected clients"""
    global is_streaming
    
    logger.info("Starting video stream...")
    
    while is_streaming:
        try:
            # Capture frame from camera
            frame = camera.get_frame()
            
            if frame is None:
                continue
            
            # Run detection
            detections = detector.detect(frame)
            
            # Draw detections on frame
            annotated_frame = detector.draw_detections(frame, detections)
            
            # Encode frame as JPEG
            import cv2
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Convert to base64
            import base64
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Send to connected clients
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
            
            # Small delay to control frame rate
            socketio.sleep(1.0 / config.get('camera.fps', 30))
            
        except Exception as e:
            logger.error(f"Error in video stream: {e}")
            socketio.sleep(0.1)
    
    logger.info("Video stream stopped")

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
