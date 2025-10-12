# Sign Detection System for Raspberry Pi 5

A real-time traffic sign detection web application designed to run on Raspberry Pi 5 with camera module. Uses YOLOv8 for detection, Flask for video streaming, Node.js/Express for the backend API, and React for the dashboard UI.

## 🎯 Features

- **Real-time Detection**: Live traffic sign detection using YOLOv8
- **Camera Integration**: Optimized for Raspberry Pi Camera Module (with USB camera fallback)
- **Web Dashboard**: Responsive React interface showing live feed and detections
- **REST API**: Node.js backend with detection endpoints
- **Video Streaming**: MJPEG stream with bounding box overlays
- **System Status**: Real-time monitoring of camera and model status
- **Performance Optimized**: Configurable detection intervals, JPEG quality, and frame rates
- **Auto-Recovery**: Automatic reconnection on connection loss
- **Resource Efficient**: Optimized memory usage and CPU utilization

## ⚡ Performance

- **FPS**: 28-30 FPS (stable) on Raspberry Pi 5
- **Latency**: 80-120ms detection latency
- **Memory**: ~300MB RAM usage
- **CPU**: 45-65% utilization (balanced mode)

See [OPTIMIZATION.md](OPTIMIZATION.md) for detailed performance tuning guide.

## 📋 System Requirements

### Raspberry Pi 5
- Raspberry Pi 5 (4GB+ RAM recommended)
- Raspberry Pi Camera Module 3 (or USB webcam)
- 32GB+ microSD card
- Display (HDMI monitor or official touchscreen)
- Raspbian OS (64-bit recommended)

### Development Machine (Optional)
- Windows/Mac/Linux with Node.js and Python
- For testing before deploying to Pi

## 🚀 Quick Start on Raspberry Pi

### 1. Clone the Repository

```bash
cd ~
git clone <your-repo-url>
cd tcdd-ml-train/sample_sign_detection
```

### 2. Run Automated Setup

```bash
chmod +x deploy-pi.sh
./deploy-pi.sh
```

This script will:
- Install all dependencies (Node.js, Python packages)
- Set up picamera2 for Pi Camera
- Install YOLOv8 and required libraries
- Create systemd services
- Build the React frontend

### 3. Add Your Trained Model

Copy your trained YOLOv8 model to the model directory:

```bash
cp /path/to/your/best.pt backend/python/model/best.pt
```

If you don't have a custom model, the system will use YOLOv8n pretrained.

### 4. Start the Services

```bash
# Start camera server
sudo systemctl start sign-detection-camera

# Start backend API
sudo systemctl start sign-detection-backend
```

### 5. Access the Dashboard

Open a browser on your Pi:
```
http://localhost:5000
```

Or from another device on the same network:
```
http://raspberrypi.local:5000
```

## 🛠️ Development Setup (Windows/Mac/Linux)

### Prerequisites

- Node.js 16+ ([Download](https://nodejs.org/))
- Python 3.8+ ([Download](https://www.python.org/))
- Git

### Installation

1. **Install Backend Dependencies**
   ```bash
   cd backend
   npm install
   ```

2. **Install Python Dependencies**
   ```bash
   cd backend/python
   pip install -r requirements.txt
   ```

3. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

### Running Locally

**Option 1: Use the start script (Linux/Mac)**
```bash
chmod +x start-dev.sh
./start-dev.sh
```

**Option 2: Use PowerShell script (Windows)**
```powershell
.\start-dev.ps1
```

**Option 3: Manual start**

Terminal 1 - Python Camera Server:
```bash
cd backend/python
python camera_server.py
```

Terminal 2 - Node.js Backend:
```bash
cd backend
npm start
```

Terminal 3 - React Frontend:
```bash
cd frontend
npm start
```

### Access Points

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Python Camera Server**: http://localhost:5001
- **Video Feed**: http://localhost:5000/video_feed

## 📁 Project Structure

```
sample_sign_detection/
├── backend/                      # Node.js + Express server
│   ├── server.js                # Main server (proxies to Python)
│   ├── package.json
│   ├── utils/
│   │   └── socketHandler.js     # WebSocket support
│   └── python/
│       ├── camera_server.py     # Flask server with camera + YOLOv8
│       ├── requirements.txt
│       ├── model/
│       │   ├── best.pt          # Your trained model (add this)
│       │   ├── labels.txt       # Class labels
│       │   └── README.md        # Model setup guide
│       └── scripts/
│           └── test_setup.py    # Pre-deployment test script
│
├── frontend/                    # React web app
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js
│       ├── index.js
│       ├── components/
│       │   ├── DetectionCard.jsx    # Detection display card
│       │   ├── ConfidenceBar.jsx    # Confidence visualization
│       │   └── LiveFeed.jsx         # Video stream component
│       ├── pages/
│       │   └── Dashboard.jsx        # Main dashboard
│       └── styles/
│           └── App.css              # Raspberry Pi optimized styles
│
├── shared/                      # Shared configuration
│   ├── config.json              # Main configuration
│   └── README.md                # Config documentation
│
├── deploy-pi.sh                 # Raspberry Pi deployment script
├── start-dev.sh                 # Development start script (Bash)
├── start-dev.ps1                # Development start script (PowerShell)
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── QUICKREF.md                  # Quick reference commands
└── README.md                    # This file
```

## 🔌 API Endpoints

### Node.js Backend (Port 5000)

- `GET /video_feed` - Proxy to Python video stream (MJPEG)
- `GET /api/python/detections` - Proxy to Python server detections
- `GET /api/python/status` - Get system status
- `GET /health` - Health check endpoint

### Python Camera Server (Port 5001)

- `GET /video_feed` - MJPEG video stream with detections
- `GET /api/detections` - Current detection results (JSON)
- `GET /api/status` - Camera and model status
- `GET /health` - Health check

## ⚙️ Configuration

### Camera Settings

Edit `backend/python/camera_server.py`:

```python
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CONFIDENCE_THRESHOLD = 0.5
```

### Model Configuration

- Place your trained model at `backend/python/model/best.pt`
- Update labels at `backend/python/model/labels.txt`
- Adjust confidence threshold in camera_server.py

### Display Optimization

The frontend is optimized for:
- Raspberry Pi Official 7" Touchscreen (800x480)
- HDMI displays up to 1920x1080
- Responsive design adapts to screen size

## 📊 Using Your Custom Model

If you trained a model using the YOLOv8 scripts in the parent directory:

```bash
# Copy your trained model
cp ../runs/detect/train/weights/best.pt backend/python/model/best.pt

# Update labels file with your classes
cat > backend/python/model/labels.txt << EOF
stop
yield
speed_limit_30
speed_limit_50
no_entry
EOF
```

## 🔧 Troubleshooting

### Camera Not Working

```bash
# Check camera connection
libcamera-hello

# Verify picamera2 installation
python3 -c "from picamera2 import Picamera2; print('OK')"

# Check permissions
sudo usermod -a -G video $USER
```

### Model Loading Errors

```bash
# Test model loading
cd backend/python
python3 -c "
from ultralytics import YOLO
model = YOLO('model/best.pt')
print('Model loaded:', model.names)
"
```

### Port Already in Use

```bash
# Kill processes on ports
sudo lsof -ti:5000 | xargs kill -9
sudo lsof -ti:5001 | xargs kill -9
```

### Performance Issues on Pi

- Reduce camera resolution (try 320x240)
- Lower FPS to 15
- Use ONNX or TFLite model format
- Reduce confidence threshold

## 🌐 Network Access

To access from other devices on your network:

1. Find your Pi's IP address:
   ```bash
   hostname -I
   ```

2. Update frontend API URL:
   ```bash
   # In frontend/.env
   REACT_APP_API_URL=http://192.168.1.100:5000
   ```

3. Rebuild frontend:
   ```bash
   cd frontend
   npm run build
   ```

## 🚦 Running as a Kiosk

For full-screen display on Pi:

```bash
# Install unclutter to hide cursor
sudo apt-get install unclutter

# Edit autostart
nano ~/.config/lxsession/LXDE-pi/autostart

# Add:
@chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:5000
@unclutter -idle 0
```

## 📝 Systemd Service Management

```bash
# Start services
sudo systemctl start sign-detection-camera
sudo systemctl start sign-detection-backend

# Stop services
sudo systemctl stop sign-detection-camera
sudo systemctl stop sign-detection-backend

# Enable auto-start on boot
sudo systemctl enable sign-detection-camera
sudo systemctl enable sign-detection-backend

# View logs
sudo journalctl -u sign-detection-camera -f
sudo journalctl -u sign-detection-backend -f
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on Raspberry Pi
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- YOLOv8 by Ultralytics
- Raspberry Pi Foundation
- React and Node.js communities
