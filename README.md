# Sign Detection System for Raspberry Pi 5# Sign Detection System for Raspberry Pi 5



A real-time traffic sign detection web application designed to run on Raspberry Pi 5 with a camera module. The project uses YOLOv8 for detection, a Flask-based Python backend for video capture, inference, and API endpoints, and a vanilla JavaScript frontend for live monitoring and visualization.A real-time traffic sign detection web application designed to run on Raspberry Pi 5 with a camera module. The project uses YOLOv8 for detection, a Flask-based Python backend for video capture, inference, and API endpoints, and a vanilla JavaScript frontend for live monitoring and visualization.



## ⭐ Key Highlights## ⭐ Key Highlights



- 🎯 **Centralized Configuration** - `config.json` is the single source of truth; changes reflect automatically!- 🎯 **Centralized Configuration** - `config.json` is the single source of truth; changes reflect automatically!

- 🚀 **Real-time Updates** - Edit config.json, components restart automatically, no server restart needed- 🚀 **Real-time Updates** - Edit config.json, components restart automatically, no server restart needed

- 📹 **Live Video Feed** - WebSocket streaming with YOLO bounding boxes- 📹 **Live Video Feed** - WebSocket streaming with YOLO bounding boxes

- 🎨 **No Build Process** - Vanilla JavaScript frontend, just save and refresh- 🎨 **No Build Process** - Vanilla JavaScript frontend, just save and refresh

- 🔧 **Simple Architecture** - Python Flask serves everything (API + static files)- 🔧 **Simple Architecture** - Python Flask serves everything (API + static files)

- 📊 **Web Interface** - Live Feed, Logs, and Settings pages- 📊 **Web Interface** - Live Feed, Logs, and Settings pages



## 🎯 Features## 🎯 Features



- Real-time detection with YOLOv8- Real-time detection with YOLOv8

- Camera integration (PiCamera2 for Raspberry Pi, OpenCV/Mock fallback for development)- Camera integration (PiCamera2 for Raspberry Pi, OpenCV/Mock fallback for development)

- Clean, responsive web UI with vanilla JavaScript- Clean, responsive web UI with vanilla JavaScript

- **🌟 Dynamic configuration updates** - change settings on-the-fly!- **🌟 Dynamic configuration updates** - change settings on-the-fly!

- WebSocket-based video streaming- WebSocket-based video streaming

- REST API for system control- REST API for system control

- Complete logging system- Complete logging system

- Settings management via web interface- Settings management via web interface



## ⚙️ Centralized Configuration System## ⚙️ Centralized Configuration System



The **`config.json`** file is the **single source of truth** for all system configuration!The **`config.json`** file is the **single source of truth** for all system configuration!



### How It Works### How It Works



``````

Edit config.json → Save → Components restart automatically → Changes reflected everywhere!Edit config.json → Save → Components restart automatically → Changes reflected everywhere!

``````



**No server restart needed!** The system detects file changes and:**No server restart needed!** The system detects file changes and:

- ✅ Automatically reloads configuration- ✅ Automatically reloads configuration

- ✅ Restarts affected components (camera, detector)- ✅ Restarts affected components (camera, detector)

- ✅ Notifies all connected browsers via WebSocket- ✅ Notifies all connected browsers via WebSocket

- ✅ Creates backup before each save- ✅ Creates backup before each save



### Quick Example### Quick Example



```json```json

{{

  "camera": { "width": 1280, "height": 720 },  ← Change this  "camera": { "width": 1280, "height": 720 },  ← Change this

  "detection": { "confidence": 0.7 }           ← And this  "detection": { "confidence": 0.7 }           ← And this

}}

``````



**Result:** Camera restarts with new resolution, detector uses new threshold, UI updates automatically!**Result:** Camera restarts with new resolution, detector uses new threshold, UI updates automatically!



📚 **Configuration Documentation:**📚 **Configuration Documentation:**

- **[CONFIG_INDEX.md](CONFIG_INDEX.md)** - Start here! Complete documentation index- **[CONFIG_INDEX.md](CONFIG_INDEX.md)** - Start here! Complete documentation index

- **[CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md)** - 5-minute quick start guide- **[CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md)** - 5-minute quick start guide

- **[CONFIG_OPTIONS.md](CONFIG_OPTIONS.md)** - All 70+ options documented- **[CONFIG_OPTIONS.md](CONFIG_OPTIONS.md)** - All 60+ options documented

- **[CONFIG_PRESETS.md](CONFIG_PRESETS.md)** - 10 ready-to-use configurations- **[CONFIG_PRESETS.md](CONFIG_PRESETS.md)** - 10 ready-to-use configurations

- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - In-depth guide- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - In-depth guide

- **[CONFIG_QUICKREF.md](CONFIG_QUICKREF.md)** - Quick reference- **[CONFIG_QUICKREF.md](CONFIG_QUICKREF.md)** - Quick reference



### Available Configuration Options (70+ Settings!)### Available Configuration Options (70+ Settings!)



| Category | Options | Auto-Restart? || Category | Options | Auto-Restart? |

|----------|---------|---------------||----------|---------|---------------|

| **Server** | port, host, debug | ❌ Manual || **Server** | port, host, debug | ❌ Manual |

| **Camera** | resolution, FPS, rotation, brightness, contrast, etc. | ✅ Yes (~2s) || **Camera** | resolution, FPS, rotation, brightness, contrast, etc. | ✅ Yes (~2s) |

| **Detection** | model, confidence, IOU, classes, visualization | ✅ Yes (~1s) || **Detection** | model, confidence, IOU, classes, visualization | ✅ Yes (~1s) |

| **Streaming** | quality, FPS, buffering | ✅ Immediate || **Streaming** | quality, FPS, buffering | ✅ Immediate |

| **Capture** | auto-save, format, path | ✅ Immediate || **Capture** | auto-save, format, path | ✅ Immediate |

| **Logging** | level, file, rotation | ✅ Immediate || **Logging** | level, file, rotation | ✅ Immediate |

| **Performance** | GPU, threads, device | ✅ Yes (~1s) || **Performance** | GPU, threads, device | ✅ Yes (~1s) |

| **Alerts** | webhooks, thresholds | ✅ Immediate || **Alerts** | webhooks, thresholds | ✅ Immediate |

| **UI** | theme, auto-start, notifications | ✅ Immediate || **UI** | theme, auto-start, notifications | ✅ Immediate |



See [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) for complete details on all options.See [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) for complete details on all options.



## 📁 Project Structure## 📁 Project Structure



``````

tcdd-dev/tcdd-dev/

├── config.json              # ⭐ CENTRAL CONFIGURATION├── config.json              # ⭐ CENTRAL CONFIGURATION

├── backend/├── backend/

│   ├── main.py             # Flask server (API + WebSocket)│   ├── main.py             # Flask server (API + WebSocket)

│   ├── camera.py           # Camera handler│   ├── camera.py           # Camera handler

│   ├── detector.py         # YOLO detection│   ├── detector.py         # YOLO detection

│   ├── config.py           # Config manager (auto-reload)│   ├── config.py           # Config manager (auto-reload)

│   └── requirements.txt    # Dependencies│   └── requirements.txt    # Dependencies

├── frontend/├── frontend/

│   ├── templates/index.html # Single page app│   ├── templates/index.html # Single page app

│   └── static/│   └── static/

│       ├── js/app.js       # Vanilla JavaScript│       ├── js/app.js       # Vanilla JavaScript

│       └── css/style.css   # Styling│       └── css/style.css   # Styling

└── data/└── data/

    ├── logs/               # Application logs    ├── logs/               # Application logs

    └── captures/           # Saved images    └── captures/           # Saved images

``````



## 🚀 Quick Start## 🚀 Quick Start



### 1. Install Dependencies### 1. Install Dependencies



**Windows:****Windows:**

```powershell```powershell

# Create and activate virtual environment# Create and activate virtual environment

python -m venv venvpython -m venv venv

.\venv\Scripts\Activate.ps1.\venv\Scripts\Activate.ps1



# Upgrade pip# Upgrade pip

python -m pip install --upgrade pippython -m pip install --upgrade pip



# Install dependencies# Install dependencies

pip install -r backend/requirements.txtpip install -r backend/requirements.txt

``````



**Linux/Raspberry Pi:****Linux/Raspberry Pi:**

```bash```bash

# Create and activate virtual environment# Create and activate virtual environment

python3 -m venv venvpython3 -m venv venv

source venv/bin/activatesource venv/bin/activate



# Upgrade pip# Upgrade pip

python -m pip install --upgrade pippython -m pip install --upgrade pip



# Install dependencies# Install dependencies

pip install -r backend/requirements.txtpip install -r backend/requirements.txt



# On Raspberry Pi, also install PiCamera2# On Raspberry Pi, also install PiCamera2

pip install picamera2pip install picamera2

``````



### 2. Configure (Optional)### 2. Configure (Optional)



Edit `config.json` to customize settings:Edit `config.json` to customize settings:



```json```json

{{

  "camera": {  "camera": {

    "width": 640,    "width": 640,

    "height": 480,    "height": 480,

    "fps": 30    "fps": 30

  },  },

  "detection": {  "detection": {

    "model": "backend/models/yolov8n.pt",    "model": "backend/models/yolov8n.pt",

    "confidence": 0.5    "confidence": 0.5

  }  }

}}

``````



> 💡 **Tip:** See [CONFIG_INDEX.md](CONFIG_INDEX.md) for all available options and presets!> 💡 **Tip:** See [CONFIG_INDEX.md](CONFIG_INDEX.md) for all available options and presets!



### 3. Run the Application### 3. Run the Application



**Windows:****Windows:**

```powershell```powershell

.\start.ps1.\start.ps1

``````



**Linux/Raspberry Pi:****Linux/Raspberry Pi:**

```bash```bash

chmod +x start.shchmod +x start.sh

./start.sh./start.sh

``````



**Or run manually:****Or run manually:**

```bash```bash

cd backendcd backend

python main.pypython main.py

``````



### 4. Access the Web Interface### 4. Access the Web Interface



Open your browser and navigate to:Open your browser and navigate to:



``````

http://localhost:5000http://localhost:5000

``````



From another device on the network:From another device on the network:

``````

http://<YOUR_PI_IP>:5000http://<YOUR_PI_IP>:5000

``````



## 🎮 Usage## 🎮 Usage



### Live Feed Page### Live Feed Page

- Click **"Start Camera"** to begin detection- Click **"Start Camera"** to begin detection

- View real-time detections with bounding boxes- View real-time detections with bounding boxes

- Monitor FPS and detection count- Monitor FPS and detection count

- Click **"Capture"** to save current frame- Click **"Capture"** to save current frame



### Logs Page### Logs Page

- View system logs in real-time- View system logs in real-time

- Filter by log level (INFO, WARNING, ERROR)- Filter by log level (INFO, WARNING, ERROR)

- Refresh or clear display- Refresh or clear display



### Settings Page### Settings Page

- Adjust camera resolution and FPS- Adjust camera resolution and FPS

- Change detection confidence threshold- Change detection confidence threshold

- Configure model path- Configure model path

- Click **"Save Settings"** - changes apply automatically!- Click **"Save Settings"** - changes apply automatically!

- Or click **"Reload from config.json"** after manually editing the file- Or click **"Reload from config.json"** after manually editing the file



## ⚙️ Configuration## ⚙️ Configuration



All configuration is centralized in `config.json`. Changes apply automatically without server restart!All configuration is centralized in `config.json`. Changes apply automatically without server restart!



**Quick Examples:****Quick Examples:**



```json```json

{{

  "camera": { "width": 1280, "height": 720 },  // HD resolution  "camera": { "width": 1280, "height": 720 },  // HD resolution

  "detection": { "confidence": 0.7 }           // Higher confidence  "detection": { "confidence": 0.7 }           // Higher confidence

}}

``````



**📚 Complete Documentation:****📚 Complete Documentation:**

- [CONFIG_INDEX.md](CONFIG_INDEX.md) - Documentation index- [CONFIG_INDEX.md](CONFIG_INDEX.md) - Documentation index

- [CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md) - 5-minute guide- [CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md) - 5-minute guide

- [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) - All 70+ options- [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) - All 70+ options

- [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - 10 ready-to-use configs- [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - 10 ready-to-use configs



## 📦 Adding Custom Models## 📦 Adding Custom Models



1. Place your YOLO model in `backend/models/`:1. Place your YOLO model in `backend/models/`:

   ```bash   ```bash

   cp /path/to/your-model.pt backend/models/custom.pt   cp /path/to/your-model.pt backend/models/custom.pt

   ```   ```



2. Update `config.json`:2. Update `config.json`:

   ```json   ```json

   {   {

     "detection": {     "detection": {

       "model": "backend/models/custom.pt"       "model": "backend/models/custom.pt"

     }     }

   }   }

   ```   ```



3. Save the file - detector will reload automatically! 🚀3. Save the file - detector will reload automatically! 🚀



**Verify model:****Verify model:**

```bash```bash

python -c "from ultralytics import YOLO; m=YOLO('backend/models/custom.pt'); print('Classes:', m.names)"python -c "from ultralytics import YOLO; m=YOLO('backend/models/custom.pt'); print('Classes:', m.names)"

``````



## 🔧 Development## 🔧 Development



### On Windows (Mock Camera)### On Windows (Mock Camera)

The system automatically uses a mock camera for testing without hardware:The system automatically uses a mock camera for testing without hardware:

```powershell```powershell

.\venv\Scripts\Activate.ps1.\venv\Scripts\Activate.ps1

python backend/main.pypython backend/main.py

``````



### On Raspberry Pi### On Raspberry Pi

Ensure PiCamera2 is installed:Ensure PiCamera2 is installed:

```bash```bash

pip install picamera2pip install picamera2

```

```sudo systemctl start sign-detection-backend

Test camera:

```bashsudo systemctl status sign-detection-backend

libcamera-hello

```## 📦 Adding Custom Models



## 📊 API Endpoints# Follow logs (Ctrl-C to stop)



- `GET /` - Web interface1. Place your YOLO model in `backend/models/`sudo journalctl -u sign-detection-backend -f

- `GET /api/status` - System status

- `POST /api/camera/start` - Start camera2. Update `config.json`:```

- `POST /api/camera/stop` - Stop camera

- `GET /api/config` - Get configuration with metadata   ```json

- `PUT /api/config` - Update configuration (auto-saves and restarts components)

- `POST /api/config/reload` - Force reload from config.json   "detection": {**Note:** If the service fails to start, check the logs with `journalctl -u sign-detection-backend -n 50` to see the last 50 log lines.

- `GET /api/logs` - Get recent logs

- `WebSocket /` - Live video stream     "model": "backend/models/your-model.pt"



## 🐛 Troubleshooting   }**Common issues:**



### Camera Not Detected (Raspberry Pi)   ```- **Exit code 1/FAILURE**: Check logs with `sudo journalctl -u sign-detection-backend -n 50`

```bash

# Test camera3. Restart the application- **Working directory wrong**: Ensure the systemd service file has the correct `WorkingDirectory` set to your project path

libcamera-hello

- **Python environment**: Verify the service is using the correct Python interpreter and venv (if applicable)

# Verify PiCamera2

python -c "from picamera2 import Picamera2; print('OK')"## 🔧 Development- **Missing dependencies**: Ensure all pip packages were installed successfully



# Add user to video group

sudo usermod -aG video $USER

# Log out and back in### On Windows (without camera)### 5. Access the dashboard

```

The system will use a mock camera for testing. You'll see a placeholder frame with timestamp.

### Model Not Loading

```bashOpen a browser on your Pi at:

# Verify model file

python -c "from ultralytics import YOLO; m=YOLO('backend/models/yolov8n.pt'); print('Model OK')"### On Raspberry Pi 5



# YOLO will auto-download yolov8n.pt on first runEnsure `picamera2` is installed:```

# Check logs: data/logs/app.log

``````bashhttp://localhost:5000



### Port Already in Usepip install picamera2```

```bash

# Windows```

netstat -ano | findstr :5000

taskkill /PID <PID> /FOr access from another device using the Pi's IP address or mDNS name (if available):



# Linux## 📊 API Endpoints

sudo lsof -ti:5000 | xargs kill -9

``````



### Configuration Not Updating- `GET /` - Web interfacehttp://<PI_IP_ADDRESS>:5000

```bash

# Check logs- `GET /api/status` - System statushttp://raspberrypi.local:5000

tail -f data/logs/app.log

- `POST /api/camera/start` - Start camera```

# Force reload via API

curl -X POST http://localhost:5000/api/config/reload- `POST /api/camera/stop` - Stop camera

```

- `GET /api/config` - Get configuration## 🛠️ Development setup (Windows / macOS / Linux)

### NumPy Version Issues

```bash- `PUT /api/config` - Update configuration

pip uninstall opencv-python -y

pip install opencv-python --no-cache-dir- `GET /api/logs` - Get recent logs### Prerequisites

```

- `WebSocket /` - Live video stream

## 🚀 Performance Tips

- Node.js 18+ (Node 20 LTS recommended) - for React frontend only

**For Raspberry Pi:**

- Use lower resolution: `"width": 320, "height": 240`## 🐛 Troubleshooting- Python 3.10+ (Python 3.11 recommended on Pi 5)

- Reduce FPS: `"fps": 15`

- Use nano model: `"model": "backend/models/yolov8n.pt"`- Git



**For Better Accuracy:**### Camera not detected

- Higher resolution: `"width": 1280, "height": 720`

- Use larger model: `"model": "backend/models/yolov8s.pt"`- Check if camera is properly connected### Install dependencies (dev machine)

- Increase confidence: `"confidence": 0.7`

- Run `libcamera-hello` to test camera

See [CONFIG_PRESETS.md](CONFIG_PRESETS.md) for complete presets!

- Ensure user is in `video` group: `sudo usermod -aG video $USER`1. Install Python dependencies for the backend:

## 📝 License



MIT License - see LICENSE file for details

### Model not loading```bash

## 🙏 Acknowledgments

- Verify model path in `config.json`cd backend/python

- YOLOv8 (Ultralytics)

- Raspberry Pi Foundation- YOLO will auto-download `yolov8n.pt` on first run if not foundpython3 -m venv venv

- Flask & SocketIO community

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
