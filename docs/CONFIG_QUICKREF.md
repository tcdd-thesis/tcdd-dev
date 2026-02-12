# Configuration System - Quick Reference

## 🎯 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        config.json                               │
│  {                                                               │
│    "camera": { "width": 640, "height": 480 },                   │
│    "detection": { "confidence": 0.5 }                           │
│  }                                                               │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ 1. File Change Detected
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Config.py (Backend)                           │
│  • Detects file modification                                     │
│  • Reloads configuration                                         │
│  • Thread-safe access                                            │
│  • Creates backup                                                │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ 2. Triggers Callbacks
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│              on_config_change() Function                         │
│  • Compares old vs new config                                    │
│  • Restarts camera if camera settings changed                   │
│  • Reloads detector if detection settings changed               │
│  • Broadcasts update via WebSocket                              │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ 3. Updates Components
                  ↓
┌────────────────────────────┬────────────────────────────────────┐
│                            │                                     │
│      Camera Component      │     Detector Component             │
│  • Stops current camera    │  • Loads new model                 │
│  • Applies new resolution  │  • Updates confidence              │
│  • Restarts with new FPS   │  • Ready for detection             │
│                            │                                     │
└────────────────────────────┴────────────────────────────────────┘
                  │
                  │ 4. Notifies Clients
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                  WebSocket Broadcast                             │
│  socketio.emit('config_updated', new_config)                    │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ 5. Frontend Updates
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Browser (app.js)                               │
│  • Receives config update event                                  │
│  • Updates local state                                           │
│  • Refreshes Settings UI if visible                             │
│  • Shows toast notification                                      │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Three Ways to Update

### Method 1: Edit File Directly ⭐ RECOMMENDED
```bash
# Open config.json in any editor
code config.json

# Change values
{
  "camera": { "width": 1280, "height": 720 }
}

# Save (Ctrl+S)
# System updates automatically within 1 second!
```

### Method 2: Use Web Interface
```
1. Open http://localhost:5000
2. Navigate to Settings page
3. Change values in form
4. Click "💾 Save Settings"
5. Watch components restart automatically!
```

### Method 3: Call API
```bash
curl -X PUT http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"detection": {"confidence": 0.7}}'
```

## 📊 What Happens When You Change Settings

```
Setting Changed          Effect                    Restart Required?
─────────────────────   ─────────────────────────  ─────────────────
camera.width            Camera restarts            Auto (2 sec)
camera.height           Camera restarts            Auto (2 sec)
camera.fps              Camera restarts            Auto (2 sec)
detection.model         Detector reloads           Auto (1 sec)
detection.confidence    Takes effect immediately   No
port                    Server restart needed      Manual
debug                   Server restart needed      Manual
logging.level           Takes effect immediately   No
logging.file            Logger restart needed      Manual
```

## ⚡ Quick Examples

### Increase Resolution (Better Quality)
```json
{
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 30
  }
}
```

### Reduce Lag (Lower Resolution)
```json
{
  "camera": {
    "width": 320,
    "height": 240,
    "fps": 60
  }
}
```

### More Accurate Detections
```json
{
  "detection": {
    "confidence": 0.8
  }
}
```

### Catch Everything (More Detections)
```json
{
  "detection": {
    "confidence": 0.3
  }
}
```

### Switch to Custom Model
```json
{
  "detection": {
    "model": "backend/models/my-custom-signs.pt"
  }
}
```

### Debug Mode (Development)
```json
{
  "debug": true,
  "logging": {
    "level": "DEBUG"
  }
}
```

## 🔍 Monitoring

### Check Current Config
```bash
# Via API
curl http://localhost:5000/api/config

# Via Web UI
Settings page → Shows all current values
```

### Force Reload
```bash
# Via API
curl -X POST http://localhost:5000/api/config/reload

# Via Web UI
Settings page → "📂 Reload from config.json" button
```

### View Logs
```bash
# Real-time
tail -f data/logs/app.log

# Last 50 lines
tail -n 50 data/logs/app.log

# Via Web UI
Logs page → Auto-updates
```

## 🚨 Troubleshooting

### Config Not Updating?
```bash
# 1. Check JSON is valid
python -m json.tool config.json

# 2. Force reload
curl -X POST http://localhost:5000/api/config/reload

# 3. Check logs
tail -f data/logs/app.log
```

### Invalid JSON Error?
```bash
# Restore from backup
cp config.json.backup config.json

# Or validate before saving
python -m json.tool config.json
```

## 💡 Pro Tips

✅ Change one setting at a time  
✅ Backup automatically created on each save  
✅ Watch logs to see updates happen  
✅ Use Settings UI for validation  
✅ Version control your config.json  

## 🎯 Summary

**config.json IS the center of everything!**

- ✅ Auto-detected when changed
- ✅ Components restart automatically
- ✅ All clients notified in real-time
- ✅ Backups created on save
- ✅ No server restart needed (for most changes)

**Just edit, save, and watch it work! 🚀**
