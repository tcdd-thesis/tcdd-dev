# Complete Configuration Reference

## 📋 All Available Configuration Options

This document describes every configuration option available in `config.json`.

---

## 🌐 Server Settings

### `port`
- **Type:** Integer
- **Default:** `5000`
- **Description:** Port number for the web server
- **Auto-restart:** ❌ Requires manual server restart
- **Example:**
  ```json
  "port": 8080
  ```

### `debug`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable debug mode (verbose logging, auto-reload)
- **Auto-restart:** ❌ Requires manual server restart
- **Example:**
  ```json
  "debug": true
  ```

### `host`
- **Type:** String
- **Default:** `"0.0.0.0"`
- **Description:** Host IP address to bind to (`0.0.0.0` = all interfaces, `127.0.0.1` = localhost only)
- **Auto-restart:** ❌ Requires manual server restart
- **Example:**
  ```json
  "host": "127.0.0.1"  // Localhost only
  "host": "0.0.0.0"    // Accessible from network
  ```

---

## 📷 Camera Settings (`camera`)

### `camera.width`
- **Type:** Integer
- **Default:** `640`
- **Description:** Camera resolution width in pixels
- **Auto-restart:** ✅ Camera restarts automatically
- **Common values:**
  - `320` - Low res, fast
  - `640` - Standard (default)
  - `1280` - HD 720p
  - `1920` - Full HD 1080p
- **Example:**
  ```json
  "camera": { "width": 1280 }
  ```

### `camera.height`
- **Type:** Integer
- **Default:** `480`
- **Description:** Camera resolution height in pixels
- **Auto-restart:** ✅ Camera restarts automatically
- **Common values:**
  - `240` - Low res, fast
  - `480` - Standard (default)
  - `720` - HD
  - `1080` - Full HD
- **Example:**
  ```json
  "camera": { "height": 720 }
  ```

### `camera.fps`
- **Type:** Integer
- **Default:** `30`
- **Description:** Target frames per second
- **Auto-restart:** ✅ Camera restarts automatically
- **Range:** `1-60`
- **Note:** Higher FPS requires more CPU/GPU
- **Example:**
  ```json
  "camera": { "fps": 15 }  // Lower FPS for better performance
  ```

### `camera.rotation`
- **Type:** Integer
- **Default:** `0`
- **Description:** Rotate camera image (degrees)
- **Auto-restart:** ✅ Camera restarts automatically
- **Valid values:** `0`, `90`, `180`, `270`
- **Example:**
  ```json
  "camera": { "rotation": 180 }  // Upside-down camera
  ```

### `camera.flip_horizontal`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Mirror image horizontally
- **Auto-restart:** ✅ Camera restarts automatically
- **Example:**
  ```json
  "camera": { "flip_horizontal": true }
  ```

### `camera.flip_vertical`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Flip image vertically
- **Auto-restart:** ✅ Camera restarts automatically
- **Example:**
  ```json
  "camera": { "flip_vertical": true }
  ```

### `camera.brightness`
- **Type:** Float
- **Default:** `0.0`
- **Description:** Brightness adjustment
- **Auto-restart:** ✅ Camera restarts automatically
- **Range:** `-1.0` to `1.0`
- **Example:**
  ```json
  "camera": { "brightness": 0.2 }  // Slightly brighter
  ```

### `camera.contrast`
- **Type:** Float
- **Default:** `1.0`
- **Description:** Contrast multiplier
- **Auto-restart:** ✅ Camera restarts automatically
- **Range:** `0.0` to `3.0`
- **Example:**
  ```json
  "camera": { "contrast": 1.5 }  // Higher contrast
  ```

### `camera.saturation`
- **Type:** Float
- **Default:** `1.0`
- **Description:** Color saturation multiplier
- **Auto-restart:** ✅ Camera restarts automatically
- **Range:** `0.0` to `3.0` (`0.0` = grayscale)
- **Example:**
  ```json
  "camera": { "saturation": 0.8 }  // Less saturated
  ```

### `camera.auto_exposure`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable automatic exposure control
- **Auto-restart:** ✅ Camera restarts automatically
- **Example:**
  ```json
  "camera": { "auto_exposure": false }
  ```

### `camera.use_mock`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Force use of mock camera (for testing without hardware)
- **Auto-restart:** ✅ Camera restarts automatically
- **Example:**
  ```json
  "camera": { "use_mock": true }
  ```

---

## 🔍 Detection Settings (`detection`)

### `detection.model`
- **Type:** String
- **Default:** `"backend/models/yolov8n.pt"`
- **Description:** Path to YOLO model file
- **Auto-restart:** ✅ Detector reloads automatically
- **Model sizes:**
  - `yolov8n.pt` - Nano (fastest, least accurate)
  - `yolov8s.pt` - Small (balanced)
  - `yolov8m.pt` - Medium (more accurate)
  - `yolov8l.pt` - Large (most accurate, slowest)
- **Example:**
  ```json
  "detection": { "model": "backend/models/custom-signs.pt" }
  ```

### `detection.confidence`
- **Type:** Float
- **Default:** `0.5`
- **Description:** Minimum confidence threshold for detections
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `0.0` to `1.0`
- **Usage:**
  - `0.3` - Catch everything (more false positives)
  - `0.5` - Balanced (default)
  - `0.7` - High precision (fewer false positives)
- **Example:**
  ```json
  "detection": { "confidence": 0.7 }
  ```

### `detection.iou_threshold`
- **Type:** Float
- **Default:** `0.45`
- **Description:** IoU (Intersection over Union) threshold for Non-Maximum Suppression
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `0.0` to `1.0`
- **Note:** Lower values = fewer overlapping boxes
- **Example:**
  ```json
  "detection": { "iou_threshold": 0.5 }
  ```

### `detection.max_detections`
- **Type:** Integer
- **Default:** `100`
- **Description:** Maximum number of detections per frame
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `1` to `1000`
- **Example:**
  ```json
  "detection": { "max_detections": 50 }
  ```

### `detection.classes`
- **Type:** Array of Integers
- **Default:** `[]` (all classes)
- **Description:** Filter detections to specific class IDs (empty = all classes)
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "detection": { "classes": [0, 1, 2] }  // Only detect classes 0, 1, 2
  ```

### `detection.show_labels`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Show class labels on bounding boxes
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "detection": { "show_labels": false }
  ```

### `detection.show_confidence`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Show confidence scores on bounding boxes
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "detection": { "show_confidence": false }
  ```

### `detection.bbox_thickness`
- **Type:** Integer
- **Default:** `2`
- **Description:** Bounding box line thickness in pixels
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `1` to `10`
- **Example:**
  ```json
  "detection": { "bbox_thickness": 3 }
  ```

### `detection.font_scale`
- **Type:** Float
- **Default:** `0.5`
- **Description:** Font size for labels
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `0.3` to `2.0`
- **Example:**
  ```json
  "detection": { "font_scale": 0.8 }
  ```

---

## 📡 Streaming Settings (`streaming`)

### `streaming.enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable WebSocket video streaming
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "streaming": { "enabled": false }
  ```

### `streaming.quality`
- **Type:** Integer
- **Default:** `85`
- **Description:** JPEG compression quality (higher = better quality, more bandwidth)
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `10` to `100`
- **Example:**
  ```json
  "streaming": { "quality": 70 }  // Lower quality for slower networks
  ```

### `streaming.max_fps`
- **Type:** Integer
- **Default:** `30`
- **Description:** Maximum streaming FPS (independent of camera FPS)
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `1` to `60`
- **Example:**
  ```json
  "streaming": { "max_fps": 15 }
  ```

### `streaming.buffer_size`
- **Type:** Integer
- **Default:** `2`
- **Description:** Number of frames to buffer for streaming
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `1` to `10`
- **Example:**
  ```json
  "streaming": { "buffer_size": 5 }
  ```

---

## 💾 Capture Settings (`capture`)

### `capture.save_detections`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Automatically save frames with detections
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "capture": { "save_detections": true }
  ```

### `capture.save_path`
- **Type:** String
- **Default:** `"data/captures"`
- **Description:** Directory to save captured images
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "capture": { "save_path": "data/detections" }
  ```

### `capture.save_format`
- **Type:** String
- **Default:** `"jpg"`
- **Description:** Image format for saved files
- **Auto-restart:** ✅ Takes effect immediately
- **Valid values:** `"jpg"`, `"png"`, `"bmp"`
- **Example:**
  ```json
  "capture": { "save_format": "png" }
  ```

### `capture.save_timestamp`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Include timestamp in saved filenames
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "capture": { "save_timestamp": false }
  ```

### `capture.min_confidence_to_save`
- **Type:** Float
- **Default:** `0.7`
- **Description:** Minimum detection confidence to trigger auto-save
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `0.0` to `1.0`
- **Example:**
  ```json
  "capture": { "min_confidence_to_save": 0.9 }
  ```

---

## 📝 Logging Settings (`logging`)

### `logging.level`
- **Type:** String
- **Default:** `"INFO"`
- **Description:** Logging verbosity level
- **Auto-restart:** ✅ Takes effect immediately
- **Valid values:**
  - `"DEBUG"` - Everything (verbose)
  - `"INFO"` - Normal operation
  - `"WARNING"` - Warnings and errors
  - `"ERROR"` - Errors only
- **Example:**
  ```json
  "logging": { "level": "DEBUG" }
  ```

### `logging.file`
- **Type:** String
- **Default:** `"data/logs/app.log"`
- **Description:** Path to log file
- **Auto-restart:** ❌ Requires manual restart
- **Example:**
  ```json
  "logging": { "file": "data/logs/system.log" }
  ```

### `logging.max_size_mb`
- **Type:** Integer
- **Default:** `10`
- **Description:** Maximum log file size in megabytes before rotation
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `1` to `1000`
- **Example:**
  ```json
  "logging": { "max_size_mb": 50 }
  ```

### `logging.backup_count`
- **Type:** Integer
- **Default:** `5`
- **Description:** Number of backup log files to keep
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `0` to `100`
- **Example:**
  ```json
  "logging": { "backup_count": 10 }
  ```

### `logging.console_output`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Also print logs to console/terminal
- **Auto-restart:** ❌ Requires manual restart
- **Example:**
  ```json
  "logging": { "console_output": false }
  ```

### `logging.log_detections`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Log every detection to file (can create large logs!)
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "logging": { "log_detections": true }
  ```

---

## ⚡ Performance Settings (`performance`)

### `performance.enable_gpu`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use GPU for inference (requires CUDA-enabled GPU and PyTorch with CUDA)
- **Auto-restart:** ✅ Detector reloads automatically
- **Example:**
  ```json
  "performance": { "enable_gpu": true }
  ```

### `performance.num_threads`
- **Type:** Integer
- **Default:** `4`
- **Description:** Number of CPU threads for inference
- **Auto-restart:** ✅ Detector reloads automatically
- **Range:** `1` to `16`
- **Example:**
  ```json
  "performance": { "num_threads": 8 }
  ```

### `performance.inference_device`
- **Type:** String
- **Default:** `"cpu"`
- **Description:** Device to use for inference
- **Auto-restart:** ✅ Detector reloads automatically
- **Valid values:**
  - `"cpu"` - CPU only
  - `"cuda"` - NVIDIA GPU
  - `"cuda:0"` - Specific GPU
- **Example:**
  ```json
  "performance": { "inference_device": "cuda:0" }
  ```

---

## 🚨 Alert Settings (`alerts`)

### `alerts.enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable alert system
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "alerts": { "enabled": true }
  ```

### `alerts.detection_threshold`
- **Type:** Integer
- **Default:** `10`
- **Description:** Number of detections to trigger alert
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "alerts": { "detection_threshold": 5 }
  ```

### `alerts.cooldown_seconds`
- **Type:** Integer
- **Default:** `60`
- **Description:** Minimum seconds between alerts
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "alerts": { "cooldown_seconds": 300 }  // 5 minutes
  ```

### `alerts.webhook_url`
- **Type:** String
- **Default:** `""`
- **Description:** Webhook URL to send alerts to (e.g., Slack, Discord)
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "alerts": { "webhook_url": "https://hooks.slack.com/services/..." }
  ```

---

## 🎨 UI Settings (`ui`)

### `ui.theme`
- **Type:** String
- **Default:** `"dark"`
- **Description:** UI color theme
- **Auto-restart:** ✅ Takes effect on page refresh
- **Valid values:** `"dark"`, `"light"`
- **Example:**
  ```json
  "ui": { "theme": "light" }
  ```

### `ui.show_fps`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Display FPS counter in UI
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "ui": { "show_fps": false }
  ```

### `ui.show_stats`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Display detection statistics in UI
- **Auto-restart:** ✅ Takes effect immediately
- **Example:**
  ```json
  "ui": { "show_stats": false }
  ```

### `ui.auto_start_camera`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Automatically start camera when page loads
- **Auto-restart:** ✅ Takes effect on page refresh
- **Example:**
  ```json
  "ui": { "auto_start_camera": true }
  ```

### `ui.notification_duration`
- **Type:** Integer
- **Default:** `3000`
- **Description:** Toast notification duration in milliseconds
- **Auto-restart:** ✅ Takes effect immediately
- **Range:** `1000` to `10000`
- **Example:**
  ```json
  "ui": { "notification_duration": 5000 }  // 5 seconds
  ```

---

## 📊 Configuration Summary Table

| Category | Auto-Restart | Requires Server Restart |
|----------|--------------|------------------------|
| Server (`port`, `host`, `debug`) | ❌ | ✅ Yes |
| Camera | ✅ Yes (~2s) | ❌ |
| Detection | ✅ Yes (~1s) | ❌ |
| Streaming | ✅ Immediate | ❌ |
| Capture | ✅ Immediate | ❌ |
| Logging (level) | ✅ Immediate | ❌ |
| Logging (file path) | ❌ | ✅ Yes |
| Performance | ✅ Yes (~1s) | ❌ |
| Alerts | ✅ Immediate | ❌ |
| UI | ✅ Immediate/Refresh | ❌ |

---

## 🎯 Common Configuration Scenarios

### High Performance (RPi 5)
```json
{
  "camera": { "width": 1280, "height": 720, "fps": 30 },
  "detection": { "model": "backend/models/yolov8n.pt", "confidence": 0.6 },
  "streaming": { "quality": 85, "max_fps": 30 }
}
```

### Low Latency
```json
{
  "camera": { "width": 320, "height": 240, "fps": 60 },
  "detection": { "model": "backend/models/yolov8n.pt" },
  "streaming": { "quality": 70, "max_fps": 60 }
}
```

### High Accuracy
```json
{
  "camera": { "width": 1920, "height": 1080, "fps": 15 },
  "detection": { 
    "model": "backend/models/yolov8m.pt",
    "confidence": 0.8,
    "iou_threshold": 0.5
  }
}
```

### Save All Detections
```json
{
  "capture": {
    "save_detections": true,
    "save_path": "data/detections",
    "min_confidence_to_save": 0.5
  },
  "logging": { "log_detections": true }
}
```

### Debug Mode
```json
{
  "debug": true,
  "logging": { "level": "DEBUG", "log_detections": true },
  "ui": { "show_fps": true, "show_stats": true }
}
```

### Production Mode
```json
{
  "debug": false,
  "logging": { "level": "WARNING", "max_size_mb": 50 },
  "camera": { "width": 1280, "height": 720 },
  "detection": { "confidence": 0.7 }
}
```

---

## 💡 Tips

1. **Start with defaults** - The default configuration works well for most cases
2. **Change one thing at a time** - Easier to troubleshoot
3. **Monitor logs** - Watch `data/logs/app.log` after changes
4. **Backup before changes** - System auto-backups to `config.json.backup`
5. **Test on development** - Use mock camera on Windows for testing

---

## 🔗 Related Documentation

- [CONFIG_QUICKSTART.md](CONFIG_QUICKSTART.md) - Quick start guide
- [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - Complete configuration guide
- [CONFIG_QUICKREF.md](CONFIG_QUICKREF.md) - Quick reference
- [README.md](README.md) - Main documentation
