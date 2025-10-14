# Configuration Guide

## 📍 Quick Start

**All settings are in one place:** `shared/config.json`

### Most Common Tasks

| Task | What to Edit | Restart Required |
|------|-------------|------------------|
| **Change model** | `detection.modelPath` | Python server |
| **Adjust confidence** | `detection.confidenceThreshold` | Python server |
| **Change resolution** | `camera.width`, `camera.height` | Python server |
| **UI refresh rate** | `detection.pollIntervalMs` | Browser only |

**After editing config:** Restart the affected service (see table above).

---

## 📋 Configuration Reference

### Port Configuration

```json
{
  "backendPort": 5000,
  "pythonServerPort": 5001,
  "frontendPort": 3000
}
```

| Setting | Default | Description | Used By |
|---------|---------|-------------|---------|
| `backendPort` | 5000 | Node.js backend server port | Backend server |
| `pythonServerPort` | 5001 | Python camera/detection server port | Python server, Backend |
| `frontendPort` | 3000 | React dev server port (dev only) | Frontend dev |

**Restart all servers** after changing ports.

---

### Camera Configuration

```json
"camera": {
  "width": 640,
  "height": 480,
  "fps": 30,
  "bufferSize": 1
}
```

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `width` | 640 | 320-1920 | Camera resolution width |
| `height` | 480 | 240-1080 | Camera resolution height |
| `fps` | 30 | 10-60 | Frames per second |
| `bufferSize` | 1 | 1-5 | Frame buffer size (keep at 1 for low latency) |

**💡 Tip:** Lower resolution = faster processing. Start with 640x480, increase if needed.

**Restart Python server** after changes.

---

### Detection Configuration

```json
"detection": {
  "modelPath": "backend/python/model/v0-20250827.1a.pt",
  "confidenceThreshold": 0.5,
  "pollIntervalMs": 500,
  "maxDetectionsDisplay": 5,
  "detectionInterval": 1,
  "jpegQuality": 80
}
```

| Setting | Default | Range | Description | Restart |
|---------|---------|-------|-------------|---------|
| `modelPath` | `backend/python/model/v0-20250827.1a.pt` | - | Path to YOLOv8 model file | Python |
| `confidenceThreshold` | 0.5 | 0.0-1.0 | Minimum confidence to show detection | Python |
| `detectionInterval` | 1 | 1-10 | Run detection every N frames (higher = faster) | Python |
| `jpegQuality` | 80 | 1-100 | JPEG compression quality | Python |
| `pollIntervalMs` | 500 | 100-5000 | Frontend polling interval (milliseconds) | Browser |
| `maxDetectionsDisplay` | 5 | 1-20 | Max detections shown in UI | Browser |

**💡 Performance Tips:**
- Higher `detectionInterval` = faster FPS but might miss detections
- Lower `jpegQuality` = faster streaming but lower image quality
- Higher `confidenceThreshold` = fewer false positives

---

### Display Configuration

```json
"display": {
  "fullscreen": false,
  "optimizedForPi": true,
  "theme": "dark"
}
```

| Setting | Default | Options | Description |
|---------|---------|---------|-------------|
| `fullscreen` | false | true/false | Fullscreen mode for kiosk |
| `optimizedForPi` | true | true/false | Pi-specific optimizations |
| `theme` | "dark" | "dark"/"light" | UI color theme |

---

### Performance Configuration

```json
"performance": {
  "enableGPU": false,
  "modelFormat": "pt",
  "maxCacheSize": 100,
  "compressionLevel": 6
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `enableGPU` | false | Enable GPU acceleration (if available) |
| `modelFormat` | "pt" | Model format: "pt", "onnx", "tflite" |
| `maxCacheSize` | 100 | Maximum cached detections |
| `compressionLevel` | 6 | Compression level (0-9) |

**Note:** GPU support depends on hardware and drivers.

---

## 🎯 Common Scenarios

### Scenario 1: Switch to a Different Model

**Step 1:** Download the model
```bash
./curl-model.sh -d new-model.pt
```

**Step 2:** Edit `shared/config.json`
```json
{
  "detection": {
    "modelPath": "backend/python/model/new-model.pt"
  }
}
```

**Step 3:** Restart Python server
```bash
# Stop with Ctrl+C, then:
python backend/python/camera_server.py
```

---

### Scenario 2: Optimize for Performance

**Goal:** Maximize FPS on Raspberry Pi

Edit `shared/config.json`:
```json
{
  "camera": {
    "width": 416,
    "height": 416,
    "fps": 20
  },
  "detection": {
    "detectionInterval": 3,
    "jpegQuality": 70,
    "confidenceThreshold": 0.6
  }
}
```

**Why these values:**
- 416x416: Optimal for YOLOv8
- Lower FPS: Less CPU load
- detectionInterval: 3 = run detection every 3rd frame
- Lower JPEG quality: Faster encoding
- Higher confidence: Fewer false positives to process

**Restart Python server**

---

### Scenario 3: Optimize for Accuracy

**Goal:** Best detection quality, FPS not critical

Edit `shared/config.json`:
```json
{
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 30
  },
  "detection": {
    "detectionInterval": 1,
    "jpegQuality": 95,
    "confidenceThreshold": 0.4
  }
}
```

**Why these values:**
- Higher resolution: More detail for detection
- detectionInterval: 1 = every frame
- Higher JPEG quality: Better image quality
- Lower confidence: Catch more detections (review false positives)

**Restart Python server**

---

### Scenario 4: Testing Different Confidence Thresholds

Quick comparison without restart:

**Method 1:** Edit config and restart
```json
"confidenceThreshold": 0.7
```

**Method 2:** Use environment variable (temporary)
```bash
CONFIDENCE_THRESHOLD=0.7 python backend/python/camera_server.py
```

**Recommended values:**
- `0.3-0.4`: Catch everything (expect false positives)
- `0.5`: Balanced (default)
- `0.6-0.7`: High confidence only
- `0.8+`: Very strict (might miss some detections)

---

## 🔄 Configuration Workflow

### Development Workflow

1. **Edit** `shared/config.json`
2. **Restart** affected service:
   - Python: `Ctrl+C` → `python backend/python/camera_server.py`
   - Backend: `Ctrl+C` → `node backend/server.js`
   - Frontend: Refresh browser (Ctrl+R)
3. **Test** changes
4. **Iterate**

### Production Workflow (Raspberry Pi)

1. **Edit** `shared/config.json`
2. **Restart services:**
   ```bash
   sudo systemctl restart sign-detection-camera
   sudo systemctl restart sign-detection-backend
   ```
3. **Verify:**
   ```bash
   sudo systemctl status sign-detection-camera
   sudo journalctl -u sign-detection-camera -f
   ```

---

## 🔍 Verification

### Test Configuration Loading

**Python config:**
```bash
python backend/python/config_loader.py
```

Expected output:
```
============================================================
Configuration Loader Test
============================================================
✓ Configuration loaded from: C:\Projects\tcdd-dev\shared\config.json

Ports:
  Backend Port:        5000
  Python Server Port:  5001

Model Configuration:
  Model Path:          C:\Projects\tcdd-dev\backend\python\model\v0-20250827.1a.pt
  ...
============================================================
```

**Start services and check logs:**

Python server should show:
```
============================================================
Camera Server Configuration:
============================================================
Model Path:            [your model path]
Camera Resolution:     640x480 @ 30 FPS
Confidence Threshold:  0.5
...
============================================================
```

Backend server should show:
```
============================================================
Backend Server Started
============================================================
Listening on port:     5000
Proxying Python from:  http://localhost:5001
Configuration loaded:  shared/config.json
============================================================
```

---

## 🔧 Advanced: Environment Variable Overrides

You can override any config value with environment variables (temporary, doesn't modify config file):

```bash
# Override model path
MODEL_PATH=/path/to/model.pt python backend/python/camera_server.py

# Override ports
PORT=8080 node backend/server.js

# Override camera settings
CAMERA_WIDTH=1920 CAMERA_HEIGHT=1080 CAMERA_FPS=60 python backend/python/camera_server.py

# Override detection settings
CONFIDENCE_THRESHOLD=0.7 DETECTION_INTERVAL=2 python backend/python/camera_server.py
```

**Use cases:**
- Quick testing without modifying config
- Different settings for different environments
- CI/CD deployments

---

## ❓ Troubleshooting

### Config not loading?

**Check file exists:**
```bash
ls shared/config.json
```

**Check JSON syntax:**
```bash
# Python
python -m json.tool shared/config.json

# Or use an online JSON validator
```

**Check for typos:** Ensure field names match exactly (case-sensitive)

---

### Model not loading?

**Verify model path in config:**
```json
"modelPath": "backend/python/model/v0-20250827.1a.pt"
```

**Check file exists:**
```bash
ls backend/python/model/v0-20250827.1a.pt
```

**Check Python server logs** for error messages about model loading.

---

### Changes not taking effect?

1. **Did you restart?** Most changes require service restart
2. **Check for cached config:** Hard refresh browser (Ctrl+Shift+R)
3. **Verify config file saved:** Check file timestamp
4. **Check logs:** Look for "Configuration loaded" messages

---

### Port conflicts?

**Error:** `Address already in use`

**Solution:**
1. Change port in config:
   ```json
   "pythonServerPort": 5002
   ```
2. Or kill the process using that port:
   ```bash
   # Find process
   sudo lsof -i :5001
   # Kill it
   sudo kill -9 <PID>
   ```

---

## 📚 Integration Details

### How Components Use Config

**Python (`camera_server.py`):**
```python
from config_loader import get_config_loader
config = get_config_loader()
MODEL_PATH = config.get_model_path()
CAMERA_WIDTH = config.get_camera_width()
```

**Node.js (`server.js`):**
```javascript
const config = require('./utils/configLoader');
const PORT = config.getBackendPort();
const PYTHON_SERVER = config.getPythonServerUrl();
```

**React (`Dashboard.jsx`):**
```javascript
import configService from '../services/configService';
await configService.ensureLoaded();
const pollInterval = configService.getPollInterval();
```

---

## 📖 Complete Configuration Example

```json
{
  "backendPort": 5000,
  "pythonServerPort": 5001,
  "frontendPort": 3000,
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30,
    "bufferSize": 1
  },
  "detection": {
    "modelPath": "backend/python/model/v0-20250827.1a.pt",
    "confidenceThreshold": 0.5,
    "pollIntervalMs": 500,
    "maxDetectionsDisplay": 5,
    "detectionInterval": 1,
    "jpegQuality": 80
  },
  "display": {
    "fullscreen": false,
    "optimizedForPi": true,
    "theme": "dark"
  },
  "performance": {
    "enableGPU": false,
    "modelFormat": "pt",
    "maxCacheSize": 100,
    "compressionLevel": 6
  }
}
```

---

## 🎓 Best Practices

1. **Start with defaults** - Use default config, only change what you need
2. **One change at a time** - Test each change before making another
3. **Document your changes** - Comment why you changed values (in a separate notes file)
4. **Backup working configs** - Copy `config.json` when system works well
5. **Use version control** - Commit config changes with descriptive messages
6. **Test on Pi** - Desktop performance ≠ Pi performance

---

## 📝 Notes

- **All paths are relative to project root** unless absolute
- **Config is read at startup** - changes require restart
- **No hot-reload** - planned for future versions
- **Environment variables override config** - useful for testing
- **No separate modelName field** - filename is in `modelPath`
