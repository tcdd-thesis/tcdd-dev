# Configuration Guide - Central Configuration System

## 🎯 Overview

The `config.json` file is the **single source of truth** for all system configuration. When you change something in `config.json`, it automatically reflects throughout the entire system without requiring a restart!

## 📋 How It Works

```
config.json  (File on Disk)
     ↓
Config.py    (Python Configuration Manager)
     ↓
main.py      (Flask Backend)
     ↓
WebSocket    (Real-time Updates)
     ↓
app.js       (Frontend UI)
```

### Key Features

✅ **Automatic Reload** - File changes are detected automatically  
✅ **Thread-Safe** - Safe concurrent access from multiple components  
✅ **Real-time Updates** - All connected clients notified instantly  
✅ **Callback System** - Components react to configuration changes  
✅ **Backup on Save** - Creates `.backup` file before each save  
✅ **Dot Notation** - Easy access like `config.get('camera.width')`

## 📝 Configuration Structure

```json
{
  "port": 5000,
  "debug": false,
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "detection": {
    "model": "backend/models/yolov8n.pt",
    "confidence": 0.5
  },
  "logging": {
    "level": "INFO",
    "file": "data/logs/app.log"
  }
}
```

## 🔧 Three Ways to Update Configuration

### 1. Edit `config.json` Directly (Recommended)

Just open `config.json` in your editor and save it!

```json
{
  "camera": {
    "width": 1280,    ← Change this
    "height": 720,    ← And this
    "fps": 15
  }
}
```

**What Happens:**
1. File modification is detected within ~1 second
2. Configuration is reloaded automatically
3. Camera restarts with new settings (if running)
4. All connected browsers notified via WebSocket
5. Settings page updates automatically

**Logs:**
```
🔄 Config file changed, reloading...
✅ Configuration loaded from config.json
📷 Camera settings changed, restarting camera...
✅ Camera restarted with new settings
✅ Configuration update complete!
```

### 2. Via Web Interface (Settings Page)

1. Open http://localhost:5000
2. Navigate to **Settings** page
3. Change values in form
4. Click **💾 Save Settings**

**What Happens:**
1. JavaScript sends PUT request to `/api/config`
2. Backend updates configuration
3. Saves to `config.json` file
4. Triggers callback to restart affected components
5. Returns success with new config
6. Frontend shows toast notification

### 3. Via API (Programmatic)

```bash
# Update configuration via API
curl -X PUT http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "detection": {
      "confidence": 0.7
    }
  }'
```

**Response:**
```json
{
  "message": "Configuration updated successfully",
  "config": { ... },
  "metadata": {
    "file": "config.json",
    "last_modified": "2025-10-17T12:34:56.789",
    "callbacks_registered": 1
  }
}
```

## 🔄 Configuration Lifecycle

### On System Startup

```python
# backend/main.py
config = Config()  # Loads config.json

# Register callback for changes
config.register_change_callback(on_config_change)

# Initialize components with config
camera = Camera(config)
detector = Detector(config)
```

### On Configuration Change

```python
def on_config_change(old_config, new_config):
    """Called automatically when config changes"""
    
    # Detect what changed
    if old_config['camera'] != new_config['camera']:
        # Restart camera with new settings
        camera.stop()
        camera = Camera(config)
        camera.start()
    
    if old_config['detection'] != new_config['detection']:
        # Reload detector with new model/confidence
        detector = Detector(config)
    
    # Notify all connected browsers
    socketio.emit('config_updated', {
        'config': new_config
    })
```

### On File Save

```python
# Automatically creates backup
config.json        ← Current
config.json.backup ← Previous version

# Updates modification timestamp
_last_modified = os.path.getmtime(config_file)

# Notifies all callbacks
for callback in _change_callbacks:
    callback(old_config, new_config)
```

## 🎛️ Available Configuration Options

### Server Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `port` | int | 5000 | Web server port |
| `debug` | bool | false | Enable debug mode |

**Example:**
```json
{
  "port": 8080,
  "debug": true
}
```

### Camera Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `camera.width` | int | 640 | Camera resolution width |
| `camera.height` | int | 480 | Camera resolution height |
| `camera.fps` | int | 30 | Frames per second |

**Common Resolutions:**
```json
// 720p HD
{ "camera": { "width": 1280, "height": 720, "fps": 30 } }

// 1080p Full HD
{ "camera": { "width": 1920, "height": 1080, "fps": 15 } }

// 4K (RPi HQ Camera)
{ "camera": { "width": 3840, "height": 2160, "fps": 10 } }

// Low latency
{ "camera": { "width": 320, "height": 240, "fps": 60 } }
```

### Detection Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `detection.model` | string | `backend/models/yolov8n.pt` | Path to YOLO model |
| `detection.confidence` | float | 0.5 | Detection confidence threshold (0-1) |

**YOLO Models:**
```json
// Nano - Fastest, least accurate
{ "detection": { "model": "backend/models/yolov8n.pt" } }

// Small - Balanced
{ "detection": { "model": "backend/models/yolov8s.pt" } }

// Medium - More accurate
{ "detection": { "model": "backend/models/yolov8m.pt" } }

// Large - Most accurate, slowest
{ "detection": { "model": "backend/models/yolov8l.pt" } }

// Custom trained model
{ "detection": { "model": "backend/models/custom-signs-v2.pt" } }
```

**Confidence Thresholds:**
```json
// High precision (few false positives)
{ "detection": { "confidence": 0.8 } }

// Balanced
{ "detection": { "confidence": 0.5 } }

// High recall (catch everything)
{ "detection": { "confidence": 0.3 } }
```

### Logging Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `logging.level` | string | "INFO" | Log level (DEBUG, INFO, WARNING, ERROR) |
| `logging.file` | string | `data/logs/app.log` | Log file path |

**Log Levels:**
```json
// Development - See everything
{ "logging": { "level": "DEBUG" } }

// Production - Normal operation
{ "logging": { "level": "INFO" } }

// Errors only
{ "logging": { "level": "ERROR" } }
```

## 🔍 Monitoring Configuration

### View Current Configuration

**Via API:**
```bash
curl http://localhost:5000/api/config
```

**Response:**
```json
{
  "config": {
    "port": 5000,
    "camera": { ... },
    "detection": { ... }
  },
  "metadata": {
    "file": "config.json",
    "exists": true,
    "last_modified": "2025-10-17T12:34:56.789",
    "callbacks_registered": 1,
    "keys": ["port", "debug", "camera", "detection", "logging"]
  }
}
```

### Force Reload from File

**Via Web UI:**
1. Settings page → Click **📂 Reload from config.json**

**Via API:**
```bash
curl -X POST http://localhost:5000/api/config/reload
```

**When to Use:**
- After manually editing `config.json`
- After pulling changes from Git
- After restoring from backup

## 🚨 What Happens When You Change Each Setting

### Camera Settings (`camera.*`)

**Effect:** Camera restarts automatically  
**Downtime:** ~2-3 seconds  
**Affects:** Live feed, detection stream

```json
// Before: 640x480 @ 30fps
// After:  1280x720 @ 15fps
{
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 15
  }
}
```

**Log:**
```
📷 Camera settings changed, restarting camera...
✅ Camera restarted with new settings
```

### Detection Settings (`detection.*`)

**Model Change:** Detector reloads model  
**Confidence Change:** No reload needed, immediate effect

```json
// Switch to custom model
{
  "detection": {
    "model": "backend/models/traffic-signs-v3.pt",
    "confidence": 0.6
  }
}
```

**Log:**
```
🔍 Detector settings changed, reloading detector...
✅ Detector reloaded with new settings
```

### Server Settings (`port`, `debug`)

**Effect:** Requires full restart  
**Action:** Stop server, change config, restart

```bash
# Stop server (Ctrl+C)
# Edit config.json
# Restart
./start.ps1
```

### Logging Settings (`logging.*`)

**Effect:** Logging level changes immediately  
**Note:** Log file path requires restart

## 💡 Best Practices

### 1. Test Changes Incrementally

```json
// ❌ Don't change everything at once
{
  "camera": { "width": 1920, "height": 1080, "fps": 60 },
  "detection": { "model": "new-model.pt", "confidence": 0.9 }
}

// ✅ Change one thing at a time
{
  "camera": { "width": 1280, "height": 720, "fps": 30 }
}
// Test, then change next setting
```

### 2. Keep Backups

The system automatically creates `config.json.backup`, but you can create manual backups:

```bash
# Manual backup
cp config.json config.json.$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp config.json.backup config.json
```

### 3. Version Control

```bash
# Track config changes in Git
git add config.json
git commit -m "Increase detection confidence to 0.7"

# View config history
git log -p config.json
```

### 4. Use Environment-Specific Configs

```bash
# Development
config.dev.json

# Production
config.prod.json

# Copy to active config
cp config.prod.json config.json
```

## 🐛 Troubleshooting

### Config Not Updating

**Problem:** Changed `config.json` but system not responding

**Solution:**
```bash
# Check logs
tail -f data/logs/app.log

# Force reload via API
curl -X POST http://localhost:5000/api/config/reload

# Or via UI: Settings → Reload from config.json
```

### Invalid JSON

**Problem:** Syntax error in `config.json`

**Symptoms:**
```
❌ Error loading config: Expecting ',' delimiter: line 5 column 3
```

**Solution:**
```bash
# Validate JSON
python -m json.tool config.json

# Or use online validator: jsonlint.com

# Restore from backup if needed
cp config.json.backup config.json
```

### Camera Won't Restart

**Problem:** Camera settings changed but camera not restarting

**Solution:**
```bash
# Check if callback registered
# Should see in logs:
"Registered config change callback: on_config_change"

# Manual restart via API
curl -X POST http://localhost:5000/api/camera/stop
curl -X POST http://localhost:5000/api/camera/start
```

## 📊 Configuration Events Timeline

```
Time     Event                           Actor
------   -----------------------------   --------------
00:00    Edit config.json                User (VS Code)
00:01    File save                       File system
00:02    File change detected            Config.py
00:03    Config reloaded                 Config.py
00:04    Callback triggered              Config.py
00:05    Camera restart initiated        main.py
00:07    Camera running with new config  camera.py
00:08    WebSocket broadcast             main.py
00:09    UI updated                      app.js (browser)
00:10    Toast notification shown        Browser
```

## 🎯 Advanced Usage

### Custom Configuration Values

Add your own keys to `config.json`:

```json
{
  "custom": {
    "alert_threshold": 10,
    "notification_email": "admin@example.com",
    "save_detections": true
  }
}
```

Access in code:
```python
# Python
threshold = config.get('custom.alert_threshold', 5)

# JavaScript
const threshold = state.config.custom?.alert_threshold || 5;
```

### Multiple Callbacks

Register multiple components to react to config changes:

```python
def on_camera_config_change(old, new):
    if old['camera'] != new['camera']:
        # Handle camera changes
        pass

def on_detector_config_change(old, new):
    if old['detection'] != new['detection']:
        # Handle detector changes
        pass

config.register_change_callback(on_camera_config_change)
config.register_change_callback(on_detector_config_change)
```

## 📚 Summary

The `config.json` file is truly the **center of configuration**:

✅ **Single Source of Truth** - All settings in one place  
✅ **Live Updates** - Changes reflect automatically  
✅ **Safe** - Backups created, thread-safe access  
✅ **Monitored** - Metadata tracks changes  
✅ **Flexible** - Change via file, UI, or API  

Just edit `config.json` and watch your system update in real-time! 🚀
