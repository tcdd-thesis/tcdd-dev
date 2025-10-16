# Sign Detection System for Raspberry Pi 5

A real-time traffic sign detection web application designed to run on Raspberry Pi 5 with a camera module. The project uses YOLOv8 for detection, a Flask-based Python backend for video capture, inference, and API endpoints, and a vanilla JavaScript frontend for live monitoring and visualization.

## ⭐ Key Highlights

- 🎯 **Centralized Configuration** - `config.json` is the single source of truth; changes reflect automatically!
- 🚀 **Real-time Updates** - Edit config.json, components restart automatically, no server restart needed
- 📹 **Live Video Feed** - WebSocket streaming with YOLO bounding boxes
- 🎨 **No Build Process** - Vanilla JavaScript frontend, just save and refresh
- 🔧 **Simple Architecture** - Python Flask serves everything (API + static files)
- 📊 **Web Interface** - Live Feed, Logs, and Settings pages

## 🎯 Features

- Real-time detection with YOLOv8
- Camera integration (PiCamera2 for Raspberry Pi, OpenCV/Mock fallback for development)
- Clean, responsive web UI with vanilla JavaScript
- **🌟 Dynamic configuration updates** - change settings on-the-fly!
- WebSocket-based video streaming
- REST API for system control
- Complete logging system
- Settings management via web interface

## ⚙️ Centralized Configuration System

The **`config.json`** file is the **single source of truth** for all system configuration!

### How It Works

```
Edit config.json → Save → Components restart automatically → Changes reflected everywhere!
```

**No server restart needed!** The system detects file changes and:
- ✅ Automatically reloads configuration
- ✅ Restarts affected components (camera, detector)
- ✅ Notifies all connected browsers via WebSocket
- ✅ Creates backup before each save

### Quick Example

```json
{
  "camera": { "width": 1280, "height": 720 },  ← Change this
  "detection": { "confidence": 0.7 }           ← And this
}
```

**Result:** Camera restarts with new resolution, detector uses new threshold, UI updates automatically!

📚 **Configuration Documentation:**
- **[CONFIG_INDEX.md](CONFIG_INDEX.md)** - Start here! Complete documentation index
- **[CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md)** - 5-minute quick start guide
- **[CONFIG_OPTIONS.md](CONFIG_OPTIONS.md)** - All 60+ options documented
- **[CONFIG_PRESETS.md](CONFIG_PRESETS.md)** - 10 ready-to-use configurations
- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - In-depth guide
- **[CONFIG_QUICKREF.md](CONFIG_QUICKREF.md)** - Quick reference

### Available Configuration Options (70+ Settings!)

| Category | Options | Auto-Restart? |
|----------|---------|---------------|
| **Server** | port, host, debug | ❌ Manual |
| **Camera** | resolution, FPS, rotation, brightness, contrast, etc. | ✅ Yes (~2s) |
| **Detection** | model, confidence, IOU, classes, visualization | ✅ Yes (~1s) |
| **Streaming** | quality, FPS, buffering | ✅ Immediate |
| **Capture** | auto-save, format, path | ✅ Immediate |
| **Logging** | level, file, rotation | ✅ Immediate |
| **Performance** | GPU, threads, device | ✅ Yes (~1s) |
| **Alerts** | webhooks, thresholds | ✅ Immediate |
| **UI** | theme, auto-start, notifications | ✅ Immediate |

See [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) for complete details on all options.

## 📁 Project Structure

```
tcdd-dev/
├── config.json              # ⭐ CENTRAL CONFIGURATION
├── backend/
│   ├── main.py             # Flask server (API + WebSocket)
│   ├── camera.py           # Camera handler
│   ├── detector.py         # YOLO detection
│   ├── config.py           # Config manager (auto-reload)
│   └── requirements.txt    # Dependencies
├── frontend/
│   ├── templates/index.html # Single page app
│   └── static/
│       ├── js/app.js       # Vanilla JavaScript
│       └── css/style.css   # Styling
└── data/
    ├── logs/               # Application logs
    └── captures/           # Saved images
```

## 🚀 Quick Start on Raspberry Pi

## 🚀 Quick Start

### 1. Clone the repository

### 1. Setup Virtual Environment

Pick a directory on your Pi and clone your fork or the project repository. Replace <your-repo-url> with your repository URL.

```bash

# Create virtual environment```bash

python -m venv venvcd ~

git clone <your-repo-url> tcdd-dev

# Activate itcd tcdd-dev

source venv/bin/activate  # Linux/Mac```

# or

.\venv\Scripts\Activate.ps1  # Windows### 2. Run the automated setup (on the Pi)

```

The repository includes a helper script that attempts to install system packages, Python dependencies, Node.js, and create systemd services. Review the script before running it.

### 2. Install Dependencies

```bash

```bashchmod +x deploy-pi.sh

pip install -r backend/requirements.txt./deploy-pi.sh

``````



### 3. Run the Application**Alternative:** For step-by-step manual setup, see [PI_SETUP.md](PI_SETUP.md).



**Linux/Raspberry Pi:**What the script does (high level):

```bash

chmod +x start.sh- Installs system packages (git, build tools, ffmpeg, libatlas/blas if available)

./start.sh- Installs or configures Picamera2 / libcamera where applicable

```- Installs Python packages from `backend/python/requirements.txt`

- Installs Node.js for React frontend and builds the frontend

**Windows:**- Creates and enables `sign-detection-backend` systemd service

```powershell

.\start.ps1**Note:** The script builds the React frontend for production (`npm run build`). This creates optimized static files without the security vulnerabilities present in development dependencies.

```

If you prefer manual steps, see the "Manual installation" section below.

### 4. Access the Web Interface

### 3. Add your trained model

Open your browser and navigate to:

```Copy your trained YOLOv8 model into the Python model folder. If there is no `best.pt` present, the camera server will fall back to a small pretrained YOLOv8 model (YOLOv8n) if configured.

http://localhost:5000

```**From development machine to Pi:**



## 🎮 Usage```bash

# Linux/Mac

### Live Feed Pagescp /path/to/best.pt pi@raspberrypi.local:~/tcdd-dev/backend/python/model/best.pt

- Click **"Start Camera"** to begin detection

- View real-time detections with bounding boxes# Windows (PowerShell)

- Monitor FPS and detection count# scp C:\path\to\best.pt pi@raspberrypi.local:/home/pi/tcdd-dev/backend/python/model/best.pt

- **"Capture"** button saves current frame```



### Logs Page**Or directly on Pi:**

- View system logs in real-time

- Filter by log level (INFO, WARNING, ERROR)```bash

- Refresh or clear displaycp /path/to/your/best.pt backend/python/model/best.pt

```

### Settings Page

- Adjust camera resolution and FPS**Update labels to match your training classes:**

- Change detection confidence threshold

- Configure model path**Verify model loads correctly:**

- Save settings (restart required for some changes)

```bash

## ⚙️ Configurationcd ~/tcdd-dev/backend/python

source venv/bin/activate

Edit `config.json`:python3 -c "from ultralytics import YOLO; m=YOLO('model/best.pt'); print('✓ Model OK:', m.names)"

```

```json

{See [backend/python/model/README.md](backend/python/model/README.md) for detailed model management instructions.

  "port": 5000,

  "camera": {### 4. Start the service

    "width": 640,

    "height": 480,Start the systemd service. This command can be run from any directory since systemd services use absolute paths.

    "fps": 30

  },```bash

  "detection": {# Start backend service

    "model": "backend/models/yolov8n.pt",sudo systemctl start sign-detection-backend

    "confidence": 0.5

  }# Check status

}sudo systemctl daemon-reload

```sudo systemctl start sign-detection-backend

sudo systemctl status sign-detection-backend

## 📦 Adding Custom Models

# Follow logs (Ctrl-C to stop)

1. Place your YOLO model in `backend/models/`sudo journalctl -u sign-detection-backend -f

2. Update `config.json`:```

   ```json

   "detection": {**Note:** If the service fails to start, check the logs with `journalctl -u sign-detection-backend -n 50` to see the last 50 log lines.

     "model": "backend/models/your-model.pt"

   }**Common issues:**

   ```- **Exit code 1/FAILURE**: Check logs with `sudo journalctl -u sign-detection-backend -n 50`

3. Restart the application- **Working directory wrong**: Ensure the systemd service file has the correct `WorkingDirectory` set to your project path

- **Python environment**: Verify the service is using the correct Python interpreter and venv (if applicable)

## 🔧 Development- **Missing dependencies**: Ensure all pip packages were installed successfully



### On Windows (without camera)### 5. Access the dashboard

The system will use a mock camera for testing. You'll see a placeholder frame with timestamp.

Open a browser on your Pi at:

### On Raspberry Pi 5

Ensure `picamera2` is installed:```

```bashhttp://localhost:5000

pip install picamera2```

```

Or access from another device using the Pi's IP address or mDNS name (if available):

## 📊 API Endpoints

```

- `GET /` - Web interfacehttp://<PI_IP_ADDRESS>:5000

- `GET /api/status` - System statushttp://raspberrypi.local:5000

- `POST /api/camera/start` - Start camera```

- `POST /api/camera/stop` - Stop camera

- `GET /api/config` - Get configuration## 🛠️ Development setup (Windows / macOS / Linux)

- `PUT /api/config` - Update configuration

- `GET /api/logs` - Get recent logs### Prerequisites

- `WebSocket /` - Live video stream

- Node.js 18+ (Node 20 LTS recommended) - for React frontend only

## 🐛 Troubleshooting- Python 3.10+ (Python 3.11 recommended on Pi 5)

- Git

### Camera not detected

- Check if camera is properly connected### Install dependencies (dev machine)

- Run `libcamera-hello` to test camera

- Ensure user is in `video` group: `sudo usermod -aG video $USER`1. Install Python dependencies for the backend:



### Model not loading```bash

- Verify model path in `config.json`cd backend/python

- YOLO will auto-download `yolov8n.pt` on first run if not foundpython3 -m venv venv

- Check logs in `data/logs/app.log`source venv/bin/activate   # on Windows: .\venv\Scripts\Activate.ps1

pip install --upgrade pip

### Port already in use

- Change port in `config.json`# On Raspberry Pi, use --no-cache-dir to avoid hash mismatches

- Or kill process: `sudo lsof -ti:5000 | xargs kill -9`pip install --no-cache-dir --upgrade -r requirements.txt



## 📝 License# On Pi, also install picamera2

# pip install picamera2

MIT License - see LICENSE file for details```



## 🙏 Acknowledgments2. Install frontend deps:



- YOLOv8 (Ultralytics)```bash

- Raspberry Pi Foundationcd frontend

- Flask & SocketIO communitiesnpm install

```

### Running locally (two processes)

Use the provided startup scripts to run both services:

**Windows:**
```powershell
.\start-dev.ps1
```

**Linux/macOS:**
```bash
chmod +x start-dev.sh
./start-dev.sh
```

Or run manually:
- Python backend (port 5000): `python backend/python/camera_server.py`
- React frontend (port 3000): `npm start` from `frontend/`

The Python backend serves both the video feed and API endpoints directly.

## ⚙️ Configuration

**All settings are centralized in `shared/config.json`.**

This single file controls model paths, camera settings, detection parameters, server ports, and UI behavior. All components (Python backend and React frontend) read from this configuration.

### Quick Examples

**Change model:**
```json
"detection": {
  "modelPath": "backend/python/model/your-model.pt"
}
```

**Adjust camera resolution:**
```json
"camera": {
  "width": 1280,
  "height": 720,
  "fps": 30
}
```

**Tune detection confidence:**
```json
"detection": {
  "confidenceThreshold": 0.7
}
```

**📖 Complete configuration guide: [CONFIG.md](CONFIG.md)**

After editing config, restart the affected service (usually the Python camera server).

## 📁 Project structure

```
tcdd-dev/
├── backend/                      # Python Flask backend
│   └── python/
│       ├── camera_server.py      # Flask server with camera + YOLOv8
│       ├── config_loader.py      # Configuration loader
│       ├── requirements.txt
│       ├── model/
│       │   ├── v0-20250827.1a.pt # Your trained model
│       │   ├── labels.txt        # Model class labels
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
│       │   ├── Home.jsx
│       │   ├── LiveFeed.jsx
│       │   ├── DrivingMode.jsx
│       │   ├── Logs.jsx
│       │   └── Settings.jsx
│       ├── services/
│       │   └── configService.js
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

### Python backend (port 5000)

- GET /video_feed — MJPEG video stream with detections
- GET /api/detections — Current detection results (JSON)
- GET /api/status — Camera and model status
- GET /api/config — Configuration for frontend
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
- Model path is configured in `shared/config.json`
- Class names are embedded in the `.pt` file (use `show_model_classes.py` to view)
- Optionally convert to ONNX/TFLite for faster inference. See `OPTIMIZATION.md`.

### Display Optimization

The frontend is optimized for:
- Raspberry Pi Official 7" Touchscreen (800x480)
- HDMI displays up to 1920x1080
- Responsive design adapts to screen size

## 📊 Using your custom model

### Training a Model

If you trained a model using Ultralytics/YOLO training (locally, Colab, or Kaggle), copy the final weights (`.pt` file) into the model folder. **Note:** YOLOv8 models have class names embedded in the `.pt` file, so no separate labels file is needed.

### Adding Model to Project

**Option 1: From training directory (same machine)**

```bash
# Navigate to project
cd ~/tcdd-dev/backend/python/model

# Copy trained weights
cp /path/to/training/runs/detect/train/weights/best.pt ./best.pt
```

**Option 2: Transfer from development machine to Pi**

```bash
# From your dev machine (Linux/Mac)
scp /path/to/best.pt pi@raspberrypi.local:~/tcdd-dev/backend/python/model/best.pt

# From Windows (PowerShell)
scp C:\path\to\best.pt pi@raspberrypi.local:/home/pi/tcdd-dev/backend/python/model/best.pt
```

**Option 3: Download from cloud storage**

```bash
# On Pi
cd ~/tcdd-dev/backend/python/model
wget https://your-storage-url/best.pt -O best.pt
```

### Verify Model

Check what classes your model detects:

```bash
cd ~/tcdd-dev
source venv/bin/activate  # or .venv/bin/activate
python backend/python/scripts/show_model_classes.py
```

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
- Verify you're using the correct model file for this project
- Use `python scripts/show_model_classes.py model/best.pt` to check classes
- Don't mix models from different training runs

**Low detection accuracy:**
- Check camera focus and lighting
- Adjust confidence threshold (0.3-0.7 range)
- Test model with sample images offline first
- Use `show_model_classes.py` script to verify model classes

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
# The build/ folder can be served by any static file server or integrated with the Python backend
```

The Python backend can be configured to serve the production build if needed.

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
sudo lsof -ti:3000 | xargs -r kill -9
```

### Performance issues on Pi

- Reduce camera resolution (try 320x240)
- Lower FPS to 15
- Use ONNX or TFLite model format
- Reduce confidence threshold

### Systemd service fails to start

If `sudo systemctl status sign-detection-backend` shows `exit-code` or `FAILURE`:

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

The `deploy-pi.sh` script attempts to create the service:

- `sign-detection-backend` — the Python backend server (camera, inference, and API)

Common service commands:

```bash
sudo systemctl start sign-detection-backend
sudo systemctl stop sign-detection-backend
sudo systemctl enable sign-detection-backend
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
- React community

---

**Need help?** Check [PI_SETUP.md](PI_SETUP.md) for detailed Raspberry Pi 5 setup instructions and troubleshooting.
