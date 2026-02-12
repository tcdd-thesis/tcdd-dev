# Configuration Documentation Index

Welcome to the complete configuration documentation! Your `config.json` is the **single source of truth** for the entire system.

---

## 📚 Documentation Files

### 🚀 Quick Start (Start Here!)
**[CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md)** - 3.5 KB  
5-minute guide to get started with centralized configuration.

**What's inside:**
- Try it right now (step-by-step)
- Three ways to update config
- Example scenarios
- Quick monitoring commands

👉 **Start here if you want to:** Get up and running immediately

---

### 📖 Quick Reference
**[CONFIG_QUICKREF.md](CONFIG_QUICKREF.md)** - 8.8 KB  
Visual guide with diagrams and quick examples.

**What's inside:**
- Configuration flow diagram
- What happens when you change settings
- Quick examples for common tasks
- Troubleshooting quick fixes

👉 **Start here if you want to:** Quick answers and visual guides

---

### 📋 All Available Options
**[CONFIG_OPTIONS.md](CONFIG_OPTIONS.md)** - 17.7 KB  
Complete reference of every configuration option.

**What's inside:**
- 60+ configuration options documented
- Auto-restart behavior for each option
- Valid values and ranges
- Examples for each setting
- Common configuration scenarios

👉 **Start here if you want to:** Know what every option does

---

### 🎯 Configuration Presets
**[CONFIG_PRESETS.md](CONFIG_PRESETS.md)** - 10.1 KB  
Ready-to-use configuration presets for common use cases.

**What's inside:**
- 10 complete configuration presets
- High Performance, Low Latency, High Accuracy, etc.
- Comparison table
- Mix and match tips

👉 **Start here if you want to:** Copy/paste working configurations

---

### 📘 Complete Guide
**[CONFIG_GUIDE.md](CONFIG_GUIDE.md)** - 12.9 KB  
In-depth guide covering all aspects of configuration.

**What's inside:**
- How the configuration system works
- Configuration lifecycle
- Detailed examples
- Best practices
- Advanced usage

👉 **Start here if you want to:** Deep understanding of the system

---

### 🔧 Implementation Details
**[CONFIG_IMPLEMENTATION.md](CONFIG_IMPLEMENTATION.md)** - 11.9 KB  
Technical documentation for developers.

**What's inside:**
- Architecture details
- Code examples
- API endpoints
- WebSocket events
- Testing strategies

👉 **Start here if you want to:** Understand or extend the implementation

---

## 🎯 Quick Navigation

### I want to...

**...get started quickly**  
→ [CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md)

**...understand what changed**  
→ [CONFIG_QUICKREF.md](CONFIG_QUICKREF.md) - See the flow diagram

**...know what a specific option does**  
→ [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) - Search for the option

**...copy a working configuration**  
→ [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - Pick a preset

**...increase performance**  
→ [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - High Performance or Low Latency

**...improve detection accuracy**  
→ [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - High Accuracy preset

**...debug issues**  
→ [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - Debug Mode preset

**...understand how it works**  
→ [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - Complete guide

**...extend the system**  
→ [CONFIG_IMPLEMENTATION.md](CONFIG_IMPLEMENTATION.md) - Technical docs

---

## 📊 Configuration Files in Your Project

```
tcdd-dev/
├── config.json              ⭐ THE MAIN CONFIG FILE (edit this!)
├── config.template.json     📝 Template with comments (for reference)
├── config.json.backup       💾 Auto-created backup
│
└── Documentation:
    ├── CONFIG_QUICKSTART.md    🚀 Start here (5 min)
    ├── CONFIG_QUICKREF.md      📖 Quick reference + diagrams
    ├── CONFIG_OPTIONS.md       📋 All 60+ options documented
    ├── CONFIG_PRESETS.md       🎯 10 ready-to-use presets
    ├── CONFIG_GUIDE.md         📘 Complete in-depth guide
    ├── CONFIG_IMPLEMENTATION.md 🔧 Technical/developer docs
    └── CONFIG_INDEX.md         📚 This file
```

---

## 🎨 Configuration Categories

### Server Settings
- `port`, `host`, `debug`
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#server-settings)

### Camera Settings
- Resolution, FPS, rotation, image adjustments
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#camera-settings-camera)

### Detection Settings
- Model, confidence, visualization
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#detection-settings-detection)

### Streaming Settings
- Quality, FPS, buffering
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#streaming-settings-streaming)

### Capture Settings
- Auto-save detections
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#capture-settings-capture)

### Logging Settings
- Log level, rotation, file management
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#logging-settings-logging)

### Performance Settings
- GPU, threads, device selection
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#performance-settings-performance)

### Alert Settings
- Webhooks, thresholds, cooldown
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#alert-settings-alerts)

### UI Settings
- Theme, auto-start, notifications
- **Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#ui-settings-ui)

---

## 🚀 Quick Examples

### Example 1: Increase Video Quality
```json
{
  "camera": { "width": 1280, "height": 720 },
  "streaming": { "quality": 90 }
}
```
**Documentation:** [CONFIG_QUICKREF.md](CONFIG_QUICKREF.md#increase-resolution-better-quality)

### Example 2: Reduce Lag
```json
{
  "camera": { "width": 320, "height": 240, "fps": 60 },
  "streaming": { "quality": 70 }
}
```
**Documentation:** [CONFIG_QUICKREF.md](CONFIG_QUICKREF.md#reduce-lag-lower-resolution)

### Example 3: Use Custom Model
```json
{
  "detection": { "model": "backend/models/my-custom.pt" }
}
```
**Documentation:** [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md#detectionmodel)

### Example 4: Auto-Save Detections
```json
{
  "capture": {
    "save_detections": true,
    "min_confidence_to_save": 0.7
  }
}
```
**Documentation:** [CONFIG_PRESETS.md](CONFIG_PRESETS.md#auto-save-everything)

---

## 📖 Reading Guide

### For Beginners
1. Read [CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md) (5 min)
2. Try changing a setting in `config.json`
3. Watch it update automatically!
4. Browse [CONFIG_PRESETS.md](CONFIG_PRESETS.md) for ideas

### For Power Users
1. Read [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for deep understanding
2. Browse [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) for all options
3. Customize settings based on your needs
4. Use [CONFIG_PRESETS.md](CONFIG_PRESETS.md) as starting points

### For Developers
1. Read [CONFIG_IMPLEMENTATION.md](CONFIG_IMPLEMENTATION.md)
2. Understand the callback system
3. Learn how to add new configuration options
4. See API documentation for programmatic access

---

## 🔍 Search Tips

### Find by Use Case
- **Performance:** Search for "FPS", "latency", "performance"
- **Quality:** Search for "resolution", "accuracy", "confidence"
- **Storage:** Search for "save", "capture", "logging"
- **Debugging:** Search for "debug", "log", "verbose"

### Find by Setting Name
All settings documented in [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) with:
- Description
- Type and default value
- Auto-restart behavior
- Valid values/ranges
- Examples

---

## 💡 Pro Tips

1. **Start with a preset** - Copy from [CONFIG_PRESETS.md](CONFIG_PRESETS.md)
2. **Edit config.json directly** - Fastest way to make changes
3. **Watch the logs** - See updates happen in real-time
4. **Backup before big changes** - Automatic backup created
5. **Change one thing at a time** - Easier to troubleshoot

---

## 🔗 Related Documentation

### Main Documentation
- [README.md](README.md) - Project overview
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation guide

### Configuration Documentation (You are here!)
- [CONFIG_INDEX.md](CONFIG_INDEX.md) - This file
- [CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md) - Quick start
- [CONFIG_QUICKREF.md](CONFIG_QUICKREF.md) - Quick reference
- [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) - All options
- [CONFIG_PRESETS.md](CONFIG_PRESETS.md) - Ready presets
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - Complete guide
- [CONFIG_IMPLEMENTATION.md](CONFIG_IMPLEMENTATION.md) - Technical docs

### Template Files
- [config.template.json](config.template.json) - Annotated template

---

## 📊 Documentation Statistics

| Document | Size | Purpose | Read Time |
|----------|------|---------|-----------|
| CONFIG_QUICKSTART.md | 3.5 KB | Quick start | 5 min |
| CONFIG_QUICKREF.md | 8.8 KB | Quick reference | 10 min |
| CONFIG_OPTIONS.md | 17.7 KB | Complete reference | 20 min |
| CONFIG_PRESETS.md | 10.1 KB | Ready presets | 15 min |
| CONFIG_GUIDE.md | 12.9 KB | In-depth guide | 20 min |
| CONFIG_IMPLEMENTATION.md | 11.9 KB | Technical docs | 15 min |
| **Total** | **64.9 KB** | Complete coverage | **85 min** |

---

## ✨ Summary

Your `config.json` is now the **center of everything**:

✅ **Single Source of Truth** - All settings in one place  
✅ **Auto-Reload** - Changes detected automatically  
✅ **Auto-Restart** - Components update on their own  
✅ **Real-time Sync** - All browsers notified instantly  
✅ **Well Documented** - 65 KB of documentation  
✅ **Easy to Use** - Just edit and save!

**Just edit config.json, save, and watch everything update automatically! 🚀**

---

**Have questions?** Check the documentation or let me know! 😊
