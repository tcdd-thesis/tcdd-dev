# Quick Setup Guide

## ✅ What Just Got Created

Your simplified sign detection system is ready! Here's what was created:

### Backend (Python)
- ✅ `backend/main.py` - Main Flask server (serves everything)
- ✅ `backend/camera.py` - Camera handler (PiCamera2/OpenCV/Mock)
- ✅ `backend/detector.py` - YOLO detection engine
- ✅ `backend/config.py` - Configuration manager
- ✅ `backend/requirements.txt` - Python dependencies

### Frontend (Vanilla JS - No Build!)
- ✅ `frontend/templates/index.html` - Single page app
- ✅ `frontend/static/js/app.js` - All JavaScript
- ✅ `frontend/static/css/style.css` - All styles

### Configuration
- ✅ `config.json` - Single config file
- ✅ `start.sh` - Linux/RPi startup script
- ✅ `start.ps1` - Windows startup script

### Data Directories
- ✅ `data/logs/` - Application logs
- ✅ `data/captures/` - Saved images
- ✅ `backend/models/` - YOLO models

## 🚀 Next Steps

### 1. Install Dependencies

First, activate your virtual environment (you already have one at the root):

```powershell
# You already have venv activated, so just install:
pip install -r backend/requirements.txt
```

This will install:
- Flask & Flask-SocketIO (web server + real-time communication)
- OpenCV (computer vision)
- Ultralytics (YOLO detection)
- NumPy (array operations)

### 2. Download YOLO Model (Optional)

The first time you run the app, YOLO will auto-download `yolov8n.pt`. 

Or manually download:
```powershell
# Navigate to models directory
cd backend\models

# Download YOLOv8 nano model (smallest, fastest)
# It will auto-download on first run, or you can manually get it:
# wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### 3. Run the Application

```powershell
# From project root
.\start.ps1
```

Or manually:
```powershell
cd backend
python main.py
```

### 4. Open in Browser

Navigate to: **http://localhost:5000**

You'll see three pages:
- **Live Feed** - Camera + real-time detection
- **Logs** - System logs
- **Settings** - Configuration

## 📝 Testing on Windows

Since you're on Windows without a Raspberry Pi camera, the system will use a **mock camera**. You'll see:
- A black frame with timestamp
- Occasional mock detections (for testing)
- All UI features working

This lets you develop and test the full system before deploying to Raspberry Pi!

## 🔄 Development Workflow

1. **Edit code** - Just save the file
2. **Refresh browser** - No build step needed!
3. **Python changes** - Restart the server (Ctrl+C, then `python main.py`)

## 📂 File Organization

```
Your tcdd-dev/
├── backend/              ← Python backend (4 files)
│   ├── main.py          ← Server
│   ├── camera.py        ← Camera
│   ├── detector.py      ← YOLO
│   └── config.py        ← Config loader
├── frontend/            ← Web interface (3 files)
│   ├── templates/
│   │   └── index.html   ← HTML
│   └── static/
│       ├── js/
│       │   └── app.js   ← JavaScript
│       └── css/
│           └── style.css ← Styles
├── data/                ← Runtime data
│   ├── logs/            ← Log files
│   └── captures/        ← Screenshots
├── config.json          ← Settings
└── start.ps1            ← Run this!
```

## 🎨 Customization Ideas

### Change Detection Model
1. Download different YOLO model (yolov8s.pt, yolov8m.pt, etc.)
2. Place in `backend/models/`
3. Update `config.json`:
   ```json
   "detection": {
     "model": "backend/models/yolov8s.pt"
   }
   ```

### Adjust Camera Settings
In `config.json`:
```json
"camera": {
  "width": 1280,    // Higher resolution
  "height": 720,
  "fps": 15         // Lower for better performance
}
```

### Change Detection Threshold
In `config.json` or via Settings page:
```json
"detection": {
  "confidence": 0.7  // Only show high-confidence detections
}
```

## 🐛 Common Issues

### Import errors
```
ModuleNotFoundError: No module named 'flask'
```
**Solution**: Install requirements
```powershell
pip install -r backend/requirements.txt
```

### Port in use
```
Address already in use
```
**Solution**: Change port in `config.json` or kill process
```powershell
# Find process
netstat -ano | findstr :5000

# Kill it (replace PID)
taskkill /PID <PID> /F
```

### NumPy version issues
```
A module that was compiled using NumPy 1.x cannot be run...
```
**Solution**: Update OpenCV
```powershell
pip uninstall opencv-python -y
pip install opencv-python --no-cache-dir
```

## 📊 What Each File Does

| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | Web server, API, WebSocket | ~260 |
| `camera.py` | Capture frames from camera | ~200 |
| `detector.py` | Run YOLO detection | ~200 |
| `config.py` | Load/save configuration | ~100 |
| `index.html` | UI structure | ~150 |
| `app.js` | UI logic + API calls | ~350 |
| `style.css` | Styling | ~400 |

**Total: ~1,660 lines** for complete system!

## 🎯 Features Included

- ✅ Real-time camera feed
- ✅ YOLO object detection
- ✅ WebSocket streaming
- ✅ Live bounding boxes
- ✅ FPS counter
- ✅ Detection count
- ✅ System logs viewer
- ✅ Settings management
- ✅ Image capture
- ✅ Toast notifications
- ✅ Responsive design
- ✅ Mock camera for testing
- ✅ No build process!

## 🚀 Ready to Go!

Everything is set up. Just run:

```powershell
.\start.ps1
```

Then open **http://localhost:5000** in your browser!

---

**Questions?** Check the main README.md or logs in `data/logs/app.log`
