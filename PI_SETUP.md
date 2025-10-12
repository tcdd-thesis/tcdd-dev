# Raspberry Pi 5 Setup Guide

Quick reference for setting up the sign detection system on Raspberry Pi 5.

## Prerequisites

- Raspberry Pi 5 (4GB+ RAM recommended)
- Raspberry Pi OS 64-bit (Bookworm or later)
- Raspberry Pi Camera Module 3 or USB webcam
- Internet connection

## Quick Setup

### 1. System update

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install system dependencies

```bash
sudo apt install -y \
  git \
  build-essential \
  python3-dev \
  python3-pip \
  python3-venv \
  libcap-dev \
  libatlas-base-dev \
  libopenblas-dev \
  ffmpeg \
  libcamera-dev \
  libcamera-apps
```

### 3. Clone repository

```bash
cd ~
git clone https://github.com/tcdd-thesis/tcdd-dev.git
cd tcdd-dev
```

### 4. Create Python virtual environment

```bash
cd backend/python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 5. Install Python packages

**Important:** Use `--no-cache-dir --upgrade` to avoid piwheels hash mismatches:

```bash
pip install --no-cache-dir --upgrade -r requirements.txt
pip install picamera2
```

### 6. Test camera

```bash
libcamera-hello
```

### 7. Create systemd services

**Camera service:**

```bash
sudo tee /etc/systemd/system/sign-detection-camera.service > /dev/null <<EOF
[Unit]
Description=Sign Detection Camera Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/tcdd-dev/backend/python
ExecStart=$HOME/tcdd-dev/backend/python/venv/bin/python camera_server.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

**Backend service:**

```bash
sudo tee /etc/systemd/system/sign-detection-backend.service > /dev/null <<EOF
[Unit]
Description=Sign Detection Backend Server
After=network.target sign-detection-camera.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/tcdd-dev/backend
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

### 8. Enable and start services

```bash
sudo systemctl daemon-reload
sudo systemctl enable sign-detection-camera
sudo systemctl enable sign-detection-backend
sudo systemctl start sign-detection-camera
sudo systemctl start sign-detection-backend
```

### 9. Check status

```bash
sudo systemctl status sign-detection-camera
sudo systemctl status sign-detection-backend
```

### 10. View logs

```bash
# Follow camera server logs
sudo journalctl -u sign-detection-camera -f

# Follow backend logs
sudo journalctl -u sign-detection-backend -f
```

## Access Dashboard

From the Pi:
```
http://localhost:5000
```

From another device on the same network:
```
http://raspberrypi.local:5000
```

Or use the Pi's IP address:
```
http://192.168.1.XXX:5000
```

## Common Issues

### Hash mismatch errors during pip install

```bash
# Use --no-cache-dir --upgrade flag
pip install --no-cache-dir --upgrade -r requirements.txt
```

### Camera not detected

```bash
# Check camera connection
libcamera-hello

# Add user to video group
sudo usermod -a -G video $USER
# Log out and back in
```

### Service fails to start

```bash
# Check logs
sudo journalctl -u sign-detection-camera -n 50 --no-pager

# Test manually
cd ~/tcdd-dev/backend/python
source venv/bin/activate
python camera_server.py
```

### Port already in use

```bash
sudo lsof -ti:5000 | xargs -r kill -9
sudo lsof -ti:5001 | xargs -r kill -9
```

## Performance Tuning

Edit `backend/python/camera_server.py`:

```python
# Lower resolution for better performance
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
CAMERA_FPS = 15

# Adjust confidence threshold
CONFIDENCE_THRESHOLD = 0.5
```

Restart service:
```bash
sudo systemctl restart sign-detection-camera
```

## Auto-start on Boot

Services are already configured to start on boot with `systemctl enable`. To disable:

```bash
sudo systemctl disable sign-detection-camera
sudo systemctl disable sign-detection-backend
```

## Uninstall

```bash
sudo systemctl stop sign-detection-camera sign-detection-backend
sudo systemctl disable sign-detection-camera sign-detection-backend
sudo rm /etc/systemd/system/sign-detection-*.service
sudo systemctl daemon-reload
cd ~ && rm -rf tcdd-dev
```
