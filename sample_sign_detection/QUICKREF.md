# Sign Detection System - Quick Reference

## 🚀 Quick Commands

### On Raspberry Pi

```bash
# Check system status
sudo systemctl status sign-detection-camera
sudo systemctl status sign-detection-backend

# Start services
sudo systemctl start sign-detection-camera sign-detection-backend

# Stop services
sudo systemctl stop sign-detection-camera sign-detection-backend

# Restart services
sudo systemctl restart sign-detection-camera sign-detection-backend

# View real-time logs
sudo journalctl -u sign-detection-camera -f
sudo journalctl -u sign-detection-backend -f

# Test camera
libcamera-hello --timeout 5000

# Test setup
cd backend/python
python3 scripts/test_setup.py
```

### Development (Local Machine)

```bash
# Start all services (Linux/Mac)
./start-dev.sh

# Start all services (Windows PowerShell)
.\start-dev.ps1

# Or start manually:
# Terminal 1:
cd backend/python && python3 camera_server.py

# Terminal 2:
cd backend && npm start

# Terminal 3:
cd frontend && npm start
```

## 🔧 Troubleshooting

### Camera Issues
```bash
# Check camera connection
vcgencmd get_camera

# Test with libcamera
libcamera-hello

# Check permissions
groups | grep video
sudo usermod -a -G video $USER
```

### Port Conflicts
```bash
# Find process using port
sudo lsof -i :5000
sudo lsof -i :5001

# Kill process
sudo kill -9 <PID>
```

### Model Not Loading
```bash
# Check model exists
ls -lh backend/python/model/best.pt

# Test model loading
cd backend/python
python3 -c "from ultralytics import YOLO; m=YOLO('model/best.pt'); print('OK')"
```

### Performance Too Slow
1. Lower camera resolution in config
2. Reduce FPS to 15
3. Increase confidence threshold
4. Use ONNX model format

## 📊 System Architecture

```
Browser → React (port 3000)
           ↓
        Node.js Backend (port 5000)
           ↓ (proxy)
        Python Flask (port 5001)
           ↓
        Camera → YOLOv8 → MJPEG Stream
```

## 🌐 Access URLs

- **Dashboard**: http://localhost:5000
- **Video Feed**: http://localhost:5000/video_feed
- **API Status**: http://localhost:5000/api/python/status
- **Detections**: http://localhost:5000/api/python/detections

## 📝 File Locations

- **Model**: `backend/python/model/best.pt`
- **Labels**: `backend/python/model/labels.txt`
- **Config**: `shared/config.json`
- **Logs**: `sudo journalctl -u sign-detection-*`
- **Services**: `/etc/systemd/system/sign-detection-*.service`

## 🔑 Important Notes

1. **Model File**: Must add your trained `best.pt` model
2. **Labels**: Update labels.txt with your classes
3. **Permissions**: User must be in `video` group
4. **Network**: For remote access, update REACT_APP_API_URL
5. **Autostart**: Enable services with `systemctl enable`
