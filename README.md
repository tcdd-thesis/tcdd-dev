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

**Alternative:** For step-by-step manual setup, see [PI_SETUP.md](PI_SETUP.md).

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

**From development machine to Pi:**

```bash
# Linux/Mac
scp /path/to/best.pt pi@raspberrypi.local:~/tcdd-dev/backend/python/model/best.pt

# Windows (PowerShell)
# scp C:\path\to\best.pt pi@raspberrypi.local:/home/pi/tcdd-dev/backend/python/model/best.pt
```

**Or directly on Pi:**

```bash
cp /path/to/your/best.pt backend/python/model/best.pt
```

**Update labels to match your training classes:**

```bash
cd ~/tcdd-dev/backend/python/model
cat > labels.txt << EOF
stop
yield
speed_limit_30
speed_limit_50
no_entry
pedestrian_crossing
school_zone
EOF
```

**Verify model loads correctly:**

```bash
cd ~/tcdd-dev/backend/python
source venv/bin/activate
python3 -c "from ultralytics import YOLO; m=YOLO('model/best.pt'); print('✓ Model OK:', m.names)"
```

See [backend/python/model/README.md](backend/python/model/README.md) for detailed model management instructions.

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

# On Raspberry Pi, use --no-cache-dir to avoid hash mismatches
pip install --no-cache-dir --upgrade -r requirements.txt

# On Pi, also install picamera2
# pip install picamera2
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

### Training a Model

If you trained a model using Ultralytics/YOLO training (locally, Colab, or Kaggle), copy the final weights into the model folder and provide a matching `labels.txt`.

### Adding Model to Project

**Option 1: From training directory (same machine)**

```bash
# Navigate to project
cd ~/tcdd-dev/backend/python/model

# Copy trained weights
cp /path/to/training/runs/detect/train/weights/best.pt ./best.pt

# Create labels file (match your training classes in order)
cat > labels.txt << EOF
stop
yield
speed_limit_30
speed_limit_50
no_entry
pedestrian_crossing
school_zone
EOF
```

**Option 2: Transfer from development machine to Pi**

```bash
# From your dev machine (Linux/Mac)
scp /path/to/best.pt pi@raspberrypi.local:~/tcdd-dev/backend/python/model/best.pt
scp /path/to/labels.txt pi@raspberrypi.local:~/tcdd-dev/backend/python/model/labels.txt

# From Windows (PowerShell)
scp C:\path\to\best.pt pi@raspberrypi.local:/home/pi/tcdd-dev/backend/python/model/best.pt
```

**Option 3: Download from cloud storage**

```bash
# On Pi
cd ~/tcdd-dev/backend/python/model
wget https://your-storage-url/best.pt -O best.pt
wget https://your-storage-url/labels.txt -O labels.txt
```

### Verify Model

Before restarting services, test that your model loads:

```bash
cd ~/tcdd-dev/backend/python
source venv/bin/activate

python3 << EOF
from ultralytics import YOLO
model = YOLO('model/best.pt')
print('✓ Model loaded successfully!')
print('Classes:', model.names)
print('Number of classes:', len(model.names))
EOF
```

### Update Running Service

After adding or updating your model:

```bash
# Restart camera service
sudo systemctl restart sign-detection-camera

# Check status
sudo systemctl status sign-detection-camera

# Watch logs for any errors
sudo journalctl -u sign-detection-camera -f
```

### Model Performance Tuning

Edit `backend/python/camera_server.py` to optimize for your model and Pi:

```python
# Resolution (lower = faster)
CAMERA_WIDTH = 640   # Try 320 for better FPS
CAMERA_HEIGHT = 480  # Try 240 for better FPS

# Detection confidence (higher = fewer false positives)
CONFIDENCE_THRESHOLD = 0.5  # Range: 0.3-0.8

# Frame rate
CAMERA_FPS = 30  # Try 15 for more stable detection
```

Restart service after changes:
```bash
sudo systemctl restart sign-detection-camera
```

### Model Formats and Conversion

**Export to ONNX for better performance:**

```bash
cd ~/tcdd-dev/backend/python
source venv/bin/activate

python3 << EOF
from ultralytics import YOLO
model = YOLO('model/best.pt')
model.export(format='onnx', imgsz=640)
print('✓ Model exported to ONNX')
EOF

# Update camera_server.py to use ONNX model:
# model = YOLO('model/best.onnx')
```

**Export to TFLite for embedded devices:**

```bash
python3 << EOF
from ultralytics import YOLO
model = YOLO('model/best.pt')
model.export(format='tflite', imgsz=640)
print('✓ Model exported to TFLite')
EOF
```

### Model Versioning

Keep backup versions for easy rollback:

```bash
cd ~/tcdd-dev/backend/python/model

# Backup current model
cp best.pt best_v1_$(date +%Y%m%d).pt

# Add new model
cp /path/to/new_model.pt best.pt

# Test new model
sudo systemctl restart sign-detection-camera

# If issues, rollback
cp best_v1_20251013.pt best.pt
sudo systemctl restart sign-detection-camera
```

### Troubleshooting Model Issues

**Model won't load:**
```bash
# Check file exists and size
ls -lh ~/tcdd-dev/backend/python/model/best.pt

# Verify it's a valid model file
file ~/tcdd-dev/backend/python/model/best.pt

# Check permissions
chmod 644 ~/tcdd-dev/backend/python/model/best.pt
```

**Wrong number of classes:**
- Ensure `labels.txt` matches your training classes exactly
- Check class order matches training data
- Don't mix models from different training runs

**Low detection accuracy:**
- Verify labels match exactly (case-sensitive)
- Check camera focus and lighting
- Adjust confidence threshold (0.3-0.7 range)
- Test model with sample images offline first

**Service crashes after model update:**
```bash
# Check detailed logs
sudo journalctl -u sign-detection-camera -n 100 --no-pager

# Test manually
cd ~/tcdd-dev/backend/python
source venv/bin/activate
python camera_server.py
```

For complete model management documentation, see [backend/python/model/README.md](backend/python/model/README.md).

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

If you see `ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE` when installing dependencies on the Pi, this is because the Pi uses **piwheels.org** (precompiled wheels for Raspberry Pi) which may have different SHA256 hashes than PyPI.

**Permanent solution (recommended):**

The `requirements.txt` file intentionally omits version pins and hashes to work with piwheels. Always install with `--no-cache-dir --upgrade`:

```bash
cd backend/python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install --no-cache-dir --upgrade -r requirements.txt
pip install picamera2
```

**If hash errors persist, install packages individually:**

```bash
pip install --no-cache-dir --upgrade \
  flask flask-cors numpy opencv-python pillow \
  ultralytics torch torchvision picamera2
```

**Why this happens:**
- Piwheels rebuilds packages for ARM architecture with different build IDs
- Hash mismatches are expected and safe when using official piwheels
- Using `--no-cache-dir` ensures fresh downloads
- No version pins allows pip to select compatible piwheels versions

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

**Need help?** Check [PI_SETUP.md](PI_SETUP.md) for detailed Raspberry Pi 5 setup instructions and troubleshooting.
