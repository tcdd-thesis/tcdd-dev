# Virtual Environment Setup Guide

## Quick Start (Windows)

### 1. Activate Virtual Environment

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
# or
.\.venv\Scripts\Activate.ps1
```

**If you get execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Command Prompt (cmd):**
```cmd
venv\Scripts\activate.bat
```

### 2. Install Dependencies

```powershell
# Make sure venv is activated first (you should see (venv) in prompt)
pip install --no-cache-dir -r backend/python/requirements.txt
```

### 3. Verify Installation

```powershell
python -c "import ultralytics; print('✓ ultralytics installed')"
python -c "import cv2; print('✓ opencv installed')"
python -c "import torch; print('✓ torch installed')"
```

### 4. Run Scripts

```powershell
# Show model classes
python backend/python/scripts/show_model_classes.py

# Test config loader
python backend/python/config_loader.py

# Start camera server
python backend/python/camera_server.py
```

### 5. Deactivate When Done

```powershell
deactivate
```

---

## Quick Start (Linux/Mac)

### 1. Create Virtual Environment (if needed)

```bash
python3 -m venv venv
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --no-cache-dir -r backend/python/requirements.txt
```

### 4. Run Scripts

```bash
python backend/python/scripts/show_model_classes.py
```

---

## Troubleshooting

### "Execution policy" error (Windows)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual environment not activating

Try using the full path:
```powershell
C:\Projects\tcdd-dev\venv\Scripts\Activate.ps1
```

### Wrong Python being used

Check which Python:
```powershell
Get-Command python
```

After activation, you should see:
```
C:\Projects\tcdd-dev\venv\Scripts\python.exe
```

### Dependencies failing to install

Install one at a time to identify the issue:
```powershell
pip install flask flask-cors
pip install numpy opencv-python Pillow
pip install torch torchvision  # This one takes longest
pip install ultralytics
```

---

## VS Code Integration

### Option 1: Select Interpreter

1. Press `Ctrl+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose `.\venv\Scripts\python.exe`

### Option 2: Workspace Settings

Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true
}
```

---

## What's Installed

The virtual environment includes:
- ✅ Flask & Flask-CORS (web server)
- ✅ NumPy (numerical computing)
- ✅ OpenCV (computer vision)
- ✅ Pillow (image processing)
- ✅ PyTorch (deep learning framework)
- ✅ Ultralytics (YOLOv8)

---

## Project Structure with venv

```
tcdd-dev/
├── venv/                    # Virtual environment (gitignored)
│   ├── Scripts/
│   │   ├── python.exe
│   │   ├── pip.exe
│   │   └── activate
│   └── Lib/
├── backend/
│   └── python/
│       ├── requirements.txt
│       ├── camera_server.py
│       └── ...
└── ...
```

---

## Daily Workflow

```powershell
# 1. Navigate to project
cd C:\Projects\tcdd-dev

# 2. Activate venv
.\venv\Scripts\Activate.ps1

# 3. Work on your project
python backend/python/camera_server.py

# 4. Deactivate when done
deactivate
```

---

## Notes

- The `venv` folder is gitignored (won't be committed)
- Virtual environment is project-specific
- Keeps dependencies isolated from system Python
- Each project should have its own venv
