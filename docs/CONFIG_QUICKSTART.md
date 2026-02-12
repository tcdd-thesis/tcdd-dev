# 🎯 Quick Start: Centralized Configuration

## What Changed?

Your `config.json` is now the **single source of truth** for the entire system!

## ⚡ Try It Right Now

### 1. Start the Server
```powershell
.\start.ps1
```

### 2. Open Config File
```powershell
code config.json
```

### 3. Make a Change
Change the camera width:
```json
{
  "camera": {
    "width": 1280,    ← Change from 640 to 1280
    "height": 720,    ← Change from 480 to 720
    "fps": 30
  }
}
```

### 4. Save File (Ctrl+S)

### 5. Watch What Happens!

**In Terminal (logs):**
```
🔄 Config file changed, reloading...
✅ Configuration loaded from config.json
📷 Camera settings changed, restarting camera...
✅ Camera restarted with new settings
✅ Configuration update complete!
```

**In Browser (if open):**
- Toast notification appears: "Configuration updated automatically"
- Settings page updates with new values
- Camera restarts with new resolution

**Time Elapsed:** ~2-3 seconds total

## 🎮 Three Ways to Update Config

### Method 1: Edit File (Recommended)
```powershell
code config.json
# Make changes, save
# Everything updates automatically!
```

### Method 2: Web Interface
```
1. Open http://localhost:5000
2. Click "Settings"
3. Change values
4. Click "💾 Save Settings"
```

### Method 3: API Call
```powershell
curl -X PUT http://localhost:5000/api/config `
  -H "Content-Type: application/json" `
  -d '{\"detection\": {\"confidence\": 0.7}}'
```

## 📊 What Can You Change?

| Setting | Example | Effect |
|---------|---------|--------|
| Camera resolution | `"width": 1280` | Camera restarts (~2s) |
| Detection confidence | `"confidence": 0.7` | Immediate effect |
| YOLO model | `"model": "backend/models/custom.pt"` | Detector reloads (~1s) |
| FPS | `"fps": 15` | Camera restarts (~2s) |

## 🔍 Monitor Changes

### Watch Logs in Real-time
```powershell
tail -f data/logs/app.log
```

### Check Current Config
```powershell
curl http://localhost:5000/api/config
```

### Force Reload from File
```powershell
curl -X POST http://localhost:5000/api/config/reload
```

## 📚 Documentation

- **CONFIG_GUIDE.md** - Complete guide (1,400+ lines)
- **CONFIG_QUICKREF.md** - Quick reference
- **CONFIG_IMPLEMENTATION.md** - Technical details

## 🎯 Example Scenarios

### Scenario 1: Increase Quality
```json
{ "camera": { "width": 1920, "height": 1080 } }
```
**Result:** HD video, camera restarts

### Scenario 2: Reduce Lag
```json
{ "camera": { "width": 320, "height": 240, "fps": 60 } }
```
**Result:** Low res, high FPS, smoother experience

### Scenario 3: Only Show High-Confidence Detections
```json
{ "detection": { "confidence": 0.8 } }
```
**Result:** Fewer false positives

### Scenario 4: Use Custom Model
```json
{ "detection": { "model": "backend/models/my-signs.pt" } }
```
**Result:** Detector loads your model

## ✅ Summary

**config.json** is now the center of everything:

- ✅ Edit and save → Components restart automatically
- ✅ No server restart needed (for most changes)
- ✅ All browsers notified in real-time
- ✅ Backup created automatically
- ✅ Changes logged for debugging

**Just edit config.json and watch the magic! 🚀**

---

## 🚀 Get Started NOW

1. Open terminal
2. Run `.\start.ps1`
3. Open `config.json` in another window
4. Change a value
5. Save
6. Watch the logs!

Enjoy your centralized configuration system! 🎉
