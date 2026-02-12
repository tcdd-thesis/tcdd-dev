# Configuration Presets

Quick configuration presets for common use cases. Copy and paste into your `config.json`.

---

## 📋 Available Presets

1. [Default - Balanced](#default-balanced)
2. [High Performance (RPi 5)](#high-performance-rpi-5)
3. [Low Latency](#low-latency)
4. [High Accuracy](#high-accuracy)
5. [Low Resource (RPi 3/4)](#low-resource-rpi-34)
6. [Development/Testing](#developmenttesting)
7. [Production](#production)
8. [Auto-Save Everything](#auto-save-everything)
9. [Debug Mode](#debug-mode)
10. [Kiosk Mode](#kiosk-mode)

---

## Default - Balanced

Standard configuration, good for most use cases.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "detection": {
    "model": "backend/models/yolov8n.pt",
    "confidence": 0.5
  },
  "streaming": {
    "quality": 85,
    "max_fps": 30
  },
  "logging": {
    "level": "INFO"
  }
}
```

**Use when:** General purpose, starting out

---

## High Performance (RPi 5)

Maximize quality and FPS on Raspberry Pi 5.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 30
  },
  "detection": {
    "model": "backend/models/yolov8s.pt",
    "confidence": 0.6,
    "iou_threshold": 0.5
  },
  "streaming": {
    "quality": 90,
    "max_fps": 30
  },
  "performance": {
    "num_threads": 8
  },
  "logging": {
    "level": "INFO"
  }
}
```

**Use when:** Raspberry Pi 5, want best quality  
**FPS:** ~25-30 FPS  
**Resolution:** 720p HD

---

## Low Latency

Minimize lag, maximum responsiveness.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 320,
    "height": 240,
    "fps": 60
  },
  "detection": {
    "model": "backend/models/yolov8n.pt",
    "confidence": 0.5,
    "max_detections": 50
  },
  "streaming": {
    "quality": 70,
    "max_fps": 60,
    "buffer_size": 1
  },
  "performance": {
    "num_threads": 4
  },
  "logging": {
    "level": "WARNING"
  }
}
```

**Use when:** Speed is critical, quality less important  
**FPS:** 50-60 FPS  
**Latency:** ~50-100ms

---

## High Accuracy

Best detection accuracy, quality over speed.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 1920,
    "height": 1080,
    "fps": 15
  },
  "detection": {
    "model": "backend/models/yolov8m.pt",
    "confidence": 0.8,
    "iou_threshold": 0.5,
    "bbox_thickness": 3,
    "font_scale": 0.8
  },
  "streaming": {
    "quality": 95,
    "max_fps": 15
  },
  "performance": {
    "num_threads": 8
  },
  "capture": {
    "save_detections": true,
    "min_confidence_to_save": 0.9
  },
  "logging": {
    "level": "INFO"
  }
}
```

**Use when:** Need high accuracy, research/analysis  
**FPS:** ~10-15 FPS  
**Resolution:** 1080p Full HD  
**Model:** Medium (more accurate)

---

## Low Resource (RPi 3/4)

Optimized for older Raspberry Pi models.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 320,
    "height": 240,
    "fps": 15
  },
  "detection": {
    "model": "backend/models/yolov8n.pt",
    "confidence": 0.6,
    "max_detections": 30
  },
  "streaming": {
    "quality": 60,
    "max_fps": 15,
    "buffer_size": 1
  },
  "performance": {
    "num_threads": 2
  },
  "logging": {
    "level": "WARNING",
    "max_size_mb": 5
  }
}
```

**Use when:** Raspberry Pi 3 or 4  
**FPS:** ~10-15 FPS  
**Memory:** Low usage

---

## Development/Testing

Testing on Windows/Mac without camera hardware.

```json
{
  "port": 5000,
  "debug": true,
  "host": "127.0.0.1",
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30,
    "use_mock": true
  },
  "detection": {
    "model": "backend/models/yolov8n.pt",
    "confidence": 0.3,
    "show_labels": true,
    "show_confidence": true
  },
  "streaming": {
    "quality": 85,
    "max_fps": 30
  },
  "logging": {
    "level": "DEBUG",
    "console_output": true,
    "log_detections": true
  },
  "ui": {
    "show_fps": true,
    "show_stats": true
  }
}
```

**Use when:** Developing on Windows/Mac  
**Features:** Mock camera, debug logs, localhost only

---

## Production

Stable, efficient production configuration.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 25,
    "auto_exposure": true
  },
  "detection": {
    "model": "backend/models/yolov8s.pt",
    "confidence": 0.7,
    "iou_threshold": 0.5
  },
  "streaming": {
    "quality": 85,
    "max_fps": 25
  },
  "logging": {
    "level": "WARNING",
    "max_size_mb": 50,
    "backup_count": 10,
    "log_detections": false
  },
  "performance": {
    "num_threads": 6
  },
  "alerts": {
    "enabled": true,
    "detection_threshold": 10,
    "cooldown_seconds": 300
  }
}
```

**Use when:** Deployed in production  
**Features:** Stable, efficient, alerting enabled

---

## Auto-Save Everything

Save all detections for analysis.

```json
{
  "port": 5000,
  "debug": false,
  "host": "0.0.0.0",
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 30
  },
  "detection": {
    "model": "backend/models/yolov8s.pt",
    "confidence": 0.6
  },
  "streaming": {
    "quality": 85,
    "max_fps": 30
  },
  "capture": {
    "save_detections": true,
    "save_path": "data/detections",
    "save_format": "jpg",
    "save_timestamp": true,
    "min_confidence_to_save": 0.5
  },
  "logging": {
    "level": "INFO",
    "log_detections": true,
    "max_size_mb": 100,
    "backup_count": 20
  }
}
```

**Use when:** Research, data collection  
**Features:** Auto-save frames, log all detections  
**Note:** Requires lots of disk space!

---

## Debug Mode

Maximum verbosity for troubleshooting.

```json
{
  "port": 5000,
  "debug": true,
  "host": "0.0.0.0",
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "detection": {
    "model": "backend/models/yolov8n.pt",
    "confidence": 0.3,
    "show_labels": true,
    "show_confidence": true,
    "bbox_thickness": 3
  },
  "streaming": {
    "quality": 85,
    "max_fps": 30
  },
  "logging": {
    "level": "DEBUG",
    "console_output": true,
    "log_detections": true,
    "max_size_mb": 50
  },
  "ui": {
    "show_fps": true,
    "show_stats": true,
    "notification_duration": 5000
  }
}
```

**Use when:** Debugging issues  
**Features:** Verbose logging, all stats visible

---

## Kiosk Mode

Touchscreen/kiosk display setup.

```json
{
  "port": 5000,
  "debug": false,
  "host": "127.0.0.1",
  "camera": {
    "width": 1280,
    "height": 720,
    "fps": 30,
    "rotation": 0
  },
  "detection": {
    "model": "backend/models/yolov8s.pt",
    "confidence": 0.7,
    "show_labels": true,
    "show_confidence": false,
    "bbox_thickness": 4,
    "font_scale": 1.0
  },
  "streaming": {
    "quality": 90,
    "max_fps": 30
  },
  "logging": {
    "level": "WARNING"
  },
  "ui": {
    "theme": "dark",
    "show_fps": false,
    "show_stats": true,
    "auto_start_camera": true,
    "notification_duration": 2000
  }
}
```

**Use when:** Touchscreen display, kiosk mode  
**Features:** Auto-start, large text, clean UI

---

## 📊 Preset Comparison

| Preset | Resolution | FPS | Model | CPU Load | Latency | Accuracy |
|--------|-----------|-----|-------|----------|---------|----------|
| Default | 640x480 | 30 | Nano | Medium | Low | Medium |
| High Perf | 1280x720 | 30 | Small | High | Low | High |
| Low Latency | 320x240 | 60 | Nano | Medium | Very Low | Low |
| High Accuracy | 1920x1080 | 15 | Medium | Very High | Medium | Very High |
| Low Resource | 320x240 | 15 | Nano | Low | Medium | Low |
| Dev/Testing | 640x480 | 30 | Nano | Low | Low | Medium |
| Production | 1280x720 | 25 | Small | High | Low | High |
| Auto-Save | 1280x720 | 30 | Small | High | Low | High |
| Debug | 640x480 | 30 | Nano | Medium | Low | Medium |
| Kiosk | 1280x720 | 30 | Small | High | Low | High |

---

## 🎯 How to Use Presets

### Method 1: Replace Entire Config
```bash
# Backup current config
cp config.json config.json.backup

# Copy preset (example: High Performance)
# Copy the JSON above and paste into config.json

# Save and watch it auto-update!
```

### Method 2: Merge Specific Settings
```json
// Start with your current config.json
// Copy only the sections you want from the preset
{
  "camera": {
    "width": 1280,    // From High Performance preset
    "height": 720
  },
  // ... keep your other settings
}
```

### Method 3: Via API
```powershell
# Update to High Performance preset via API
curl -X PUT http://localhost:5000/api/config `
  -H "Content-Type: application/json" `
  -d @high-performance-preset.json
```

---

## 💡 Customization Tips

### Mix and Match
```json
{
  // High quality camera (from High Perf)
  "camera": { "width": 1280, "height": 720, "fps": 30 },
  
  // But use fast model (from Low Latency)
  "detection": { "model": "backend/models/yolov8n.pt" },
  
  // And save detections (from Auto-Save)
  "capture": { "save_detections": true }
}
```

### Fine-Tune for Your Hardware
```json
{
  // Start with preset
  "camera": { "width": 1280, "height": 720, "fps": 30 },
  
  // Then adjust based on your FPS
  // If FPS < 20, reduce resolution or FPS
  // If FPS > 40, increase quality
}
```

---

## 🔗 Related Documentation

- [CONFIG_OPTIONS.md](CONFIG_OPTIONS.md) - All available options
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - Complete guide
- [CONFIG_QUICKREF.md](CONFIG_QUICKREF.md) - Quick reference
