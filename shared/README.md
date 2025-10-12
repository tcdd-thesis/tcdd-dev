# Shared Configuration

This directory contains configuration files shared between backend and frontend.

## config.json

Main configuration file with settings for:

- **Port Configuration**: Backend, Python server, and frontend ports
- **Camera Settings**: Resolution, FPS for optimal Pi performance
- **Detection Parameters**: Confidence threshold, polling interval
- **Display Options**: Fullscreen mode, theme, Pi-specific optimizations

## Environment Variables

For production deployments, override these settings using environment variables:

```bash
# Backend
PORT=5000
PYTHON_SERVER=http://localhost:5001

# Frontend
REACT_APP_API_URL=http://localhost:5000

# Camera
CAMERA_WIDTH=640
CAMERA_HEIGHT=480
CAMERA_FPS=30

# Detection
CONFIDENCE_THRESHOLD=0.5
```

## Performance Tuning for Raspberry Pi

### Low-end Pi (2GB RAM)
```json
{
  "camera": { "width": 320, "height": 240, "fps": 15 },
  "detection": { "confidenceThreshold": 0.6 }
}
```

### High-end Pi (8GB RAM)
```json
{
  "camera": { "width": 1280, "height": 720, "fps": 30 },
  "detection": { "confidenceThreshold": 0.4 }
}
```

## Network Configuration

For access from other devices, update the frontend API URL:

```bash
# Local network access
REACT_APP_API_URL=http://192.168.1.100:5000

# mDNS hostname
REACT_APP_API_URL=http://raspberrypi.local:5000
```

