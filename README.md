# Sign Detection System for Raspberry Pi 5

A real-time traffic sign detection web application designed to run on Raspberry Pi 5 with a camera module. The project uses YOLOv8 for detection, a Flask-based Python backend for video capture, inference, and API endpoints, and a vanilla JavaScript frontend for live monitoring and visualization.

## Key Highlights

- Centralized Configuration - config.json is the single source of truth; changes reflect automatically!
- Real-time Updates - Edit config.json, components restart automatically, no server restart needed
- Live Video Feed - WebSocket streaming with YOLO bounding boxes
- No Build Process - Vanilla JavaScript frontend, just save and refresh
- Simple Architecture - Python Flask serves everything (API + static files)
- Web Interface - Live Feed, Logs, and Settings pages

## Features

- Real-time detection with YOLOv8
- Camera integration (PiCamera2 for Raspberry Pi, OpenCV/Mock fallback for development)
- Clean, responsive web UI with vanilla JavaScript
- Dynamic configuration updates - change settings on-the-fly!
- WebSocket-based video streaming
- REST API for system control
- Complete logging system
- Settings management via web interface

## Centralized Configuration System

The config.json file is the single source of truth for all system configuration!

### How It Works

Edit config.json  Save  Components restart automatically  Changes reflected everywhere!

No server restart needed! The system detects file changes and:
- Automatically reloads configuration
- Restarts affected components (camera, detector)
- Notifies all connected browsers via WebSocket
- Creates backup before each save

### Quick Example

{
  "camera": { "width": 1280, "height": 720 },
  "detection": { "confidence": 0.7 }
}

Result: Camera restarts with new resolution, detector uses new threshold, UI updates automatically!

### Configuration Documentation

- CONFIG_INDEX.md - Start here! Complete documentation index
- CONFIG_QUICKSTART.md - 5-minute quick start guide
- CONFIG_OPTIONS.md - All 70+ options documented
- CONFIG_PRESETS.md - 10 ready-to-use configurations
- CONFIG_GUIDE.md - In-depth guide
- CONFIG_QUICKREF.md - Quick reference

### Available Configuration Options (70+ Settings!)

Server: port, host, debug (Manual restart)
Camera: resolution, FPS, rotation, brightness, contrast, etc. (Auto-restart ~2s)
Detection: model, confidence, IOU, classes, visualization (Auto-restart ~1s)
Streaming: quality, FPS, buffering (Immediate)
Capture: auto-save, format, path (Immediate)
Logging: level, file, rotation (Immediate)
Performance: GPU, threads, device (Auto-restart ~1s)
Alerts: webhooks, thresholds (Immediate)
UI: theme, auto-start, notifications (Immediate)

See CONFIG_OPTIONS.md for complete details on all options.

## Project Structure

tcdd-dev/
 config.json              # CENTRAL CONFIGURATION
 backend/
    main.py             # Flask server (API + WebSocket)
    camera.py           # Camera handler
    detector.py         # YOLO detection
    config.py           # Config manager (auto-reload)
    requirements.txt    # Dependencies
 frontend/
    templates/index.html # Single page app
    static/
        js/app.js       # Vanilla JavaScript
        css/style.css   # Styling
 data/
     logs/               # Application logs
     captures/           # Saved images

## Quick Start

### 1. Install Dependencies

Windows:
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r backend/requirements.txt

Linux/Raspberry Pi:
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r backend/requirements.txt

# On Raspberry Pi, also install PiCamera2
pip install picamera2

### 2. Configure (Optional)

Edit config.json to customize settings. See CONFIG_INDEX.md for all available options and presets!

### 3. Run the Application

Windows: .\start.ps1
Linux/Raspberry Pi: chmod +x start.sh && ./start.sh
Or manually: cd backend && python main.py

### 4. Access the Web Interface

Local: http://localhost:5000
Network: http://<YOUR_PI_IP>:5000

## Usage

### Live Feed Page
- Click "Start Camera" to begin detection
- View real-time detections with bounding boxes
- Monitor FPS and detection count
- Click "Capture" to save current frame

### Logs Page
- View system logs in real-time
- Filter by log level (INFO, WARNING, ERROR)
- Refresh or clear display

### Settings Page
- Adjust camera resolution and FPS
- Change detection confidence threshold
- Configure model path
- Click "Save Settings" - changes apply automatically!
- Or click "Reload from config.json" after manually editing the file

## Configuration

All configuration is centralized in config.json. Changes apply automatically without server restart!

See complete documentation:
- CONFIG_INDEX.md - Documentation index
- CONFIG_QUICKSTART.md - 5-minute guide
- CONFIG_OPTIONS.md - All 70+ options
- CONFIG_PRESETS.md - 10 ready-to-use configs

## Adding Custom Models

1. Place your YOLO model in backend/models/
2. Update config.json with the model path
3. Save the file - detector will reload automatically!

Verify model:
python -c "from ultralytics import YOLO; m=YOLO('backend/models/custom.pt'); print('Classes:', m.names)"

## Development

### On Windows (Mock Camera)
The system automatically uses a mock camera for testing without hardware.

### On Raspberry Pi
Ensure PiCamera2 is installed and test camera with: libcamera-hello

## API Endpoints

- GET / - Web interface
- GET /api/status - System status
- POST /api/camera/start - Start camera
- POST /api/camera/stop - Stop camera
- GET /api/config - Get configuration with metadata
- PUT /api/config - Update configuration (auto-saves and restarts components)
- POST /api/config/reload - Force reload from config.json
- GET /api/logs - Get recent logs
- WebSocket / - Live video stream

## Troubleshooting

### Camera Not Detected (Raspberry Pi)
libcamera-hello
python -c "from picamera2 import Picamera2; print('OK')"
sudo usermod -aG video $USER

### Model Not Loading
python -c "from ultralytics import YOLO; m=YOLO('backend/models/yolov8n.pt'); print('Model OK')"

### Port Already in Use
Windows: netstat -ano | findstr :5000 && taskkill /PID <PID> /F
Linux: sudo lsof -ti:5000 | xargs kill -9

### Configuration Not Updating
tail -f data/logs/app.log
curl -X POST http://localhost:5000/api/config/reload

### NumPy Version Issues
pip uninstall opencv-python -y
pip install opencv-python --no-cache-dir

## Performance Tips

For Raspberry Pi:
- Use lower resolution: "width": 320, "height": 240
- Reduce FPS: "fps": 15
- Use nano model: "model": "backend/models/yolov8n.pt"

For Better Accuracy:
- Higher resolution: "width": 1280, "height": 720
- Use larger model: "model": "backend/models/yolov8s.pt"
- Increase confidence: "confidence": 0.7

See CONFIG_PRESETS.md for complete presets!

## License

MIT License - see LICENSE file for details

## Acknowledgments

- YOLOv8 (Ultralytics)
- Raspberry Pi Foundation
- Flask & SocketIO community
