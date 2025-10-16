# Dependencies Guide

## Current Versions (Updated: October 2025)

### Core Dependencies
```
Flask==3.0.0
Flask-Cors==4.0.0
Flask-SocketIO==5.3.5
python-socketio==5.10.0
```

### Computer Vision
```
opencv-python==4.12.0.88
numpy==2.2.6
```

### YOLO Detection
```
ultralytics==8.0.228
```

### Raspberry Pi Only
```
picamera2  # Install only on Raspberry Pi
```

## Installation

### Fresh Install

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Linux/Raspberry Pi:**
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# On Raspberry Pi only
pip install picamera2
```

## Common Issues & Solutions

### 1. NumPy/OpenCV Compatibility Error

**Symptoms:**
```
AttributeError: _ARRAY_API not found
ImportError: numpy.core.multiarray failed to import
```

**Solution:**
```bash
pip uninstall numpy opencv-python -y
pip install numpy opencv-python --upgrade --no-cache-dir
```

**Verify:**
```bash
python -c "import cv2; import numpy as np; print('✓ OpenCV:', cv2.__version__); print('✓ NumPy:', np.__version__)"
```

### 2. Flask SocketIO Version Mismatch

**Symptoms:**
```
TypeError: _SocketIOMiddleware() takes no arguments
```

**Solution:**
```bash
pip install flask-socketio==5.3.5 python-socketio==5.10.0 --force-reinstall
```

### 3. Ultralytics YOLO Issues

**Symptoms:**
```
ModuleNotFoundError: No module named 'ultralytics'
```

**Solution:**
```bash
pip install ultralytics==8.0.228
```

**Auto-download models:**
```bash
# First run will download yolov8n.pt automatically
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 4. PiCamera2 Not Available (Windows)

**Expected behavior:** This is normal on Windows. The system will use mock camera.

**On Raspberry Pi:**
```bash
sudo apt update
sudo apt install -y python3-picamera2
pip install picamera2
```

## Updating Dependencies

### Update All Packages
```bash
pip install --upgrade -r backend/requirements.txt
```

### Update Specific Package
```bash
pip install --upgrade <package-name>
```

### Regenerate requirements.txt
```bash
pip freeze > backend/requirements.txt
```

## Clean Install (Nuclear Option)

If nothing else works:

**Windows:**
```powershell
# Deactivate venv if active
deactivate

# Remove venv
Remove-Item -Recurse -Force venv

# Start fresh
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Linux:**
```bash
# Deactivate venv if active
deactivate

# Remove venv
rm -rf venv

# Start fresh
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

## Python Version Requirements

- **Minimum:** Python 3.8
- **Recommended:** Python 3.10 or 3.11
- **Tested:** Python 3.13 (current)

Check your version:
```bash
python --version
```

## Dependency Tree

```
tcdd-dev
├── Flask (Web Framework)
│   ├── Flask-Cors (CORS handling)
│   └── Flask-SocketIO (WebSocket support)
│       └── python-socketio (Low-level SocketIO)
├── OpenCV (Computer Vision)
│   └── NumPy (Array operations)
├── Ultralytics (YOLO Detection)
│   ├── torch (PyTorch)
│   ├── torchvision
│   └── pillow (Image handling)
└── PiCamera2 (Raspberry Pi Camera - optional)
```

## Platform-Specific Notes

### Windows
- No PiCamera2 support (uses mock camera)
- OpenCV should work out of the box
- May need Visual C++ redistributables for some packages

### Raspberry Pi OS
- PiCamera2 is native
- May need system packages: `sudo apt install python3-opencv`
- Use `libcamera-hello` to test camera

### Linux (Other)
- OpenCV may require system packages
- Install dependencies: `sudo apt install python3-opencv libglib2.0-0`

## Verification Script

Save as `verify_deps.py`:

```python
#!/usr/bin/env python3
"""Verify all dependencies are installed correctly."""

import sys

def check_import(module_name, display_name=None):
    """Try to import a module and report status."""
    if display_name is None:
        display_name = module_name
    try:
        mod = __import__(module_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f"✓ {display_name}: {version}")
        return True
    except ImportError as e:
        print(f"✗ {display_name}: NOT FOUND - {e}")
        return False

print("=== Dependency Check ===\n")

checks = [
    ('flask', 'Flask'),
    ('flask_cors', 'Flask-Cors'),
    ('flask_socketio', 'Flask-SocketIO'),
    ('socketio', 'python-socketio'),
    ('cv2', 'OpenCV'),
    ('numpy', 'NumPy'),
    ('ultralytics', 'Ultralytics YOLO'),
]

results = []
for module, name in checks:
    results.append(check_import(module, name))

# Optional dependencies
print("\n=== Optional Dependencies ===\n")
check_import('picamera2', 'PiCamera2 (Raspberry Pi only)')

print("\n" + "="*30)
if all(results):
    print("✓ All required dependencies OK!")
    sys.exit(0)
else:
    print("✗ Some dependencies missing!")
    print("\nRun: pip install -r backend/requirements.txt")
    sys.exit(1)
```

**Run:**
```bash
python verify_deps.py
```

## Getting Help

If you're still having issues:

1. Check `data/logs/app.log` for detailed errors
2. Verify Python version: `python --version`
3. Check pip version: `pip --version`
4. List installed packages: `pip list`
5. Check virtual environment: `which python` (Linux) or `where python` (Windows)

## Links

- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [PiCamera2 Documentation](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
