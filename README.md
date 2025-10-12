# Sign Detection System for Raspberry Pi 5

A real-time traffic sign detection web application designed to run on Raspberry Pi 5 with a camera module. The project uses YOLOv8 for detection, a Flask-based Python camera server for video capture and inference, a Node.js/Express backend that proxies and provides API endpoints, and a React dashboard for live monitoring and visualization.

# 🎯 Features

- Real-time detection with YOLOv8
- Camera integration (Picamera2 / libcamera for the Pi Camera, USB webcam fallback)
- React dashboard showing live feed, detection list and confidence
- Node.js backend that proxies the Python camera server and exposes REST endpoints
- MJPEG video streaming with bounding-box overlays
- System status endpoints and WebSocket integration for live updates
- Performance tuning options (resolution, FPS, confidence threshold)
- Systemd services for auto-start and reliable operation on boot

## ⚡ Performance (typical)

- FPS: 20–30 FPS depending on resolution and model size
- Latency: ~80–200 ms depending on model (YOLOv8n is fastest)
- Memory: ~200–600 MB depending on active services and model
- CPU: varies by mode and model size; tuning recommended

See [OPTIMIZATION.md](OPTIMIZATION.md) for tuning tips and trade-offs. Your mileage will vary depending on model size (n, s, m, l), resolution, and whether you convert models to ONNX/TFLite.

## 📋 System Requirements

### Raspberry Pi 5 (recommended hardware)

- Raspberry Pi 5 (4 GB+ recommended)
- Raspberry Pi Camera Module 3 or a USB UVC webcam
- 32 GB+ microSD card (use an A1/A2 card for better IO)
- 64-bit OS recommended: Raspberry Pi OS (64-bit) or Ubuntu 24.04 (arm64)
- Optional HDMI display or official Raspberry Pi touchscreen for kiosk mode

### Development Machine (Optional)
- Windows/Mac/Linux with Node.js and Python
- For testing before deploying to Pi

## 🚀 Quick Start on Raspberry Pi

### 1. Clone the repository

Pick a directory on your Pi and clone your fork or the project repository. Replace <your-repo-url> with your repository URL.

```bash
cd ~
git clone <your-repo-url> tcdd-dev
cd tcdd-dev
```

### 2. Run the automated setup (on the Pi)

The repository includes a helper script that attempts to install system packages, Python dependencies, Node.js, and create systemd services. Review the script before running it.

```bash
chmod +x deploy-pi.sh
./deploy-pi.sh
```

What the script does (high level):

- Installs system packages (git, build tools, ffmpeg, libatlas/blas if available)
- Installs or configures Picamera2 / libcamera where applicable
- Installs Python packages from `backend/python/requirements.txt`
- Installs Node.js (NodeSource) and builds the React frontend
- Creates and enables `sign-detection-camera` and `sign-detection-backend` systemd services

**Note:** The script builds the React frontend for production (`npm run build`). This creates optimized static files without the security vulnerabilities present in development dependencies.

If you prefer manual steps, see the "Manual installation" section below.

### 3. Add your trained model

Copy your trained YOLOv8 model into the Python model folder. If there is no `best.pt` present, the camera server will fall back to a small pretrained YOLOv8 model (YOLOv8n) if configured.

```bash
cp /path/to/your/best.pt backend/python/model/best.pt
```

Update `backend/python/model/labels.txt` to match your classes.

### 4. Start the services

Start both systemd services. These commands can be run from any directory since systemd services use absolute paths.

```bash
# Start camera server
sudo systemctl start sign-detection-camera

# Start backend API
sudo systemctl start sign-detection-backend

# Check status
sudo systemctl daemon-reload
sudo systemctl start sign-detection-camera
sudo systemctl status sign-detection-camera
sudo systemctl status sign-detection-backend

# Follow logs (Ctrl-C to stop)
sudo journalctl -u sign-detection-camera -f
sudo journalctl -u sign-detection-backend -f
```

**Note:** If the services fail to start, check the logs with `journalctl -u <service-name> -n 50` to see the last 50 log lines.

**Common issues:**
- **Exit code 1/FAILURE**: Check logs with `sudo journalctl -u sign-detection-camera -n 50`
- **Working directory wrong**: Ensure the systemd service file has the correct `WorkingDirectory` set to your project path
- **Python environment**: Verify the service is using the correct Python interpreter and venv (if applicable)
- **Missing dependencies**: Ensure all pip packages were installed successfully

### 5. Access the dashboard

Open a browser on your Pi at:

```
http://localhost:5000
```

Or access from another device using the Pi's IP address or mDNS name (if available):

```
http://<PI_IP_ADDRESS>:5000
http://raspberrypi.local:5000
```

## 🛠️ Development setup (Windows / macOS / Linux)

### Prerequisites

- Node.js 18+ (Node 20 LTS recommended)
- Python 3.10+ (Python 3.11 recommended on Pi 5)
- Git

### Install dependencies (dev machine)

1. Install Node packages for the backend (proxy/server):

```bash
cd backend
npm install
```

2. Install Python dependencies for the camera server:

```bash
cd backend/python
python3 -m venv venv
source venv/bin/activate   # on Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

3. Install frontend deps and run the React development server:

```bash
cd frontend
npm install
npm start
```

### Running locally (three processes)

- Python camera server (port 5001): `python backend/python/camera_server.py`
- Node backend/proxy (port 5000): `npm start` from `backend/`
- React frontend (port 3000): `npm start` from `frontend/`

The Node backend proxies `/video_feed` and API routes to the Python server.

## 📁 Project structure

```
tcdd-dev/
├── backend/                      # Node.js + Express server and proxy
│   ├── server.js                 # Main server (proxies to Python)
│   ├── package.json
│   ├── utils/
│   │   └── socketHandler.js      # WebSocket support
│   └── python/
│       ├── camera_server.py      # Flask server with camera + YOLOv8
│       ├── requirements.txt
│       ├── model/
│       │   ├── best.pt           # Your trained model (add this)
│       │   ├── labels.txt        # Class labels
│       │   └── README.md         # Model setup guide
│       └── scripts/
│           └── test_setup.py     # Pre-deployment test script
├── frontend/                      # React web app
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── App.js
│       ├── index.js
│       ├── components/
│       │   ├── DetectionCard.jsx
│       │   ├── ConfidenceBar.jsx
│       │   └── LiveFeed.jsx
│       ├── pages/
│       │   └── Dashboard.jsx
│       └── styles/
│           └── App.css
├── shared/
│   ├── config.json
│   └── README.md
├── deploy-pi.sh
├── start-dev.sh
├── start-dev.ps1
├── .env.example
├── .gitignore
├── QUICKREF.md
└── README.md
```

## 🔌 API endpoints

### Node.js backend (port 5000)

- GET /video_feed — Proxy to Python video stream (MJPEG)
- GET /api/python/detections — Proxy to Python server detections
- GET /api/python/status — Get system status
- GET /health — Health check

### Python camera server (port 5001)

- GET /video_feed — MJPEG video stream with detections
- GET /api/detections — Current detection results (JSON)
- GET /api/status — Camera and model status
- GET /health — Health check

## ⚙️ Configuration

### Camera settings

Edit `backend/python/camera_server.py` to adjust resolution, framerate and confidence.

Example values:

```python
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CONFIDENCE_THRESHOLD = 0.5
```

### Model configuration

- Place your trained model at `backend/python/model/best.pt`
- Update labels at `backend/python/model/labels.txt`
- Optionally convert to ONNX/TFLite for faster inference. See `OPTIMIZATION.md`.

### Display Optimization

The frontend is optimized for:
- Raspberry Pi Official 7" Touchscreen (800x480)
- HDMI displays up to 1920x1080
- Responsive design adapts to screen size

## 📊 Using your custom model

If you trained a model using Ultralytics/YOLO training, copy the final weights into the model folder and provide a matching `labels.txt`.

```bash
# from project root
cp ../runs/detect/train/weights/best.pt backend/python/model/best.pt

# create labels file (example)
cat > backend/python/model/labels.txt << EOF
stop
yield
speed_limit_30
speed_limit_50
no_entry
EOF
```

## 🔧 Troubleshooting

### npm audit vulnerabilities (frontend dependencies)

When running `npm install` in the frontend, you may see security warnings about vulnerable packages (nth-check, postcss, webpack-dev-server). These are in **development dependencies** only and do not affect production builds.

**Important:** Do NOT run `npm audit fix --force` as it will break react-scripts.

**Recommended approach:**
- For production on the Pi, use `npm run build` to create optimized static files
- The vulnerabilities are in the dev server, not the production build
- If running locally on a closed network, the risk is minimal

**To deploy production build:**
```bash
cd frontend
npm run build
# Serve the build/ folder via the Node backend (already configured)
```

The Node backend in this project serves the production build automatically when available.

### Pip hash mismatch errors (piwheels)

If you see `ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE` when installing dependencies on the Pi, this is because the Pi uses **piwheels.org** (precompiled wheels for Raspberry Pi) which may have different hashes than PyPI.

**Solution:** Install packages without hash checking or regenerate requirements on the Pi:

```bash
cd backend/python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install packages individually
pip install flask==3.0.0 flask-cors==4.0.0 numpy opencv-python ultralytics torch torchvision

# For Raspberry Pi camera support (Pi only)
pip install picamera2

# Generate fresh requirements.txt (optional)
pip freeze > requirements.txt
```

Alternatively, install with `--no-cache-dir` to bypass cache issues:

```bash
pip install --no-cache-dir -r requirements.txt
```

### Camera not working

```bash
# Check basic libcamera functionality
libcamera-hello

# Verify Picamera2 import (inside venv if used)
python3 -c "from picamera2 import Picamera2; print('OK')"

# Add your user to video group (log out/in after running)
sudo usermod -a -G video $USER
```

### Model loading errors

```bash
# Test model loading quickly
cd backend/python
python3 -c "from ultralytics import YOLO; model = YOLO('model/best.pt'); print('Model loaded:', model.names)"
```

### Port already in use

```bash
# Kill processes on ports (install lsof if missing)
sudo lsof -ti:5000 | xargs -r kill -9
sudo lsof -ti:5001 | xargs -r kill -9
```

### Performance issues on Pi

- Reduce camera resolution (try 320x240)
- Lower FPS to 15
- Use ONNX or TFLite model format
- Reduce confidence threshold

### Systemd service fails to start

If `sudo systemctl status sign-detection-camera` shows `exit-code` or `FAILURE`:

**1. Check the detailed logs:**
```bash
sudo journalctl -u sign-detection-camera -n 50 --no-pager
```

**2. Common fixes:**

**Missing dependencies:**
```bash
cd ~/tcdd-dev/backend/python
source venv/bin/activate
pip install -r requirements.txt
pip install picamera2
```

**Wrong working directory in service file:**
```bash
sudo nano /etc/systemd/system/sign-detection-camera.service
# Ensure WorkingDirectory=/home/pi/tcdd-dev/backend/python
# Ensure ExecStart uses full path: /home/pi/tcdd-dev/backend/python/venv/bin/python camera_server.py
sudo systemctl daemon-reload
sudo systemctl restart sign-detection-camera
```

**Permission issues:**
```bash
sudo usermod -a -G video $USER
# Log out and back in, then try again
```

**Test manually first:**
```bash
cd ~/tcdd-dev/backend/python
source venv/bin/activate
python camera_server.py
# If this works, the systemd service file needs updating
```

### Missing libcap-dev (build errors during pip install)

If you see "You need to install libcap development headers":

```bash
sudo apt update
sudo apt install -y libcap-dev build-essential python3-dev
cd ~/tcdd-dev/backend/python
source venv/bin/activate
pip install -r requirements.txt
```

## 🌐 Network access

1. Find your Pi's IP address:

```bash
hostname -I
```

2. Update the frontend environment variable if you want the built app to point to a specific API host. Edit `frontend/.env` or `frontend/.env.production` and set:

```
REACT_APP_API_URL=http://<PI_IP_ADDRESS>:5000
```

3. Rebuild frontend for production on the Pi (optional):

```bash
cd frontend
npm run build
```

## 🚦 Running as a kiosk

Install `unclutter` to hide the cursor and add the dashboard URL to your desktop environment autostart. Example (LXDE / Raspberry Pi OS):

```bash
sudo apt-get install unclutter
mkdir -p ~/.config/lxsession/LXDE-pi
cat >> ~/.config/lxsession/LXDE-pi/autostart <<EOF
@chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:5000
@unclutter -idle 0
EOF
```

## 📝 systemd service management

The `deploy-pi.sh` script attempts to create two services:

- `sign-detection-camera` — the Python camera & inference server
- `sign-detection-backend` — the Node.js proxy/backend

Common service commands:

```bash
sudo systemctl start sign-detection-camera
sudo systemctl start sign-detection-backend

sudo systemctl stop sign-detection-camera
sudo systemctl stop sign-detection-backend

sudo systemctl enable sign-detection-camera
sudo systemctl enable sign-detection-backend

sudo journalctl -u sign-detection-camera -f
sudo journalctl -u sign-detection-backend -f
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make and test your changes (Pi recommended for hardware features)
4. Submit a pull request with a clear description and testing notes

## License

MIT — See the LICENSE file for details.

## Acknowledgments

- YOLOv8 (Ultralytics)
- Raspberry Pi Foundation
- React and Node.js communities

---

If you'd like, I can also:

- add a short `quick-start-pi.md` with exact apt packages and verified install commands for Raspberry Pi 5 (arm64), or
- generate a simple `systemd` unit file template for the camera service and backend if your `deploy-pi.sh` doesn't already provide them.

Tell me which of those you'd prefer and I will add it next.
