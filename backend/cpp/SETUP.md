# C++ Server Setup Guide

This guide walks you through setting up the C++ server on Raspberry Pi 5.

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS (64-bit recommended)
- Raspberry Pi Camera Module
- Internet connection for downloading dependencies

## Step 1: System Update

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

## Step 2: Install Build Tools

```bash
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl
```

## Step 3: Install OpenCV

```bash
# Install OpenCV from package manager (easiest)
sudo apt-get install -y libopencv-dev

# Verify installation
pkg-config --modversion opencv4
```

## Step 4: Install NCNN

NCNN is not available in standard repositories, so we need to build it:

```bash
# Install dependencies
sudo apt-get install -y \
    libvulkan-dev \
    vulkan-tools \
    libprotobuf-dev \
    protobuf-compiler

# Clone NCNN
cd ~
git clone --depth=1 https://github.com/Tencent/ncnn.git
cd ncnn

# Initialize submodules (REQUIRED!)
git submodule update --init

# Create build directory
mkdir -p build
cd build

# Configure (with Vulkan support and system-wide installation)
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DNCNN_VULKAN=ON \
      -DNCNN_BUILD_EXAMPLES=OFF \
      -DNCNN_BUILD_TOOLS=ON \
      ..

# Build (this may take 30-60 minutes)
make -j$(nproc)

# Install system-wide
sudo make install
sudo ldconfig

# Verify installation
ls /usr/local/include/ncnn/
ls /usr/local/lib/libncnn.a
```

## Step 5: Enable Camera

```bash
# Enable camera using raspi-config
sudo raspi-config
# Navigate to: Interface Options -> Legacy Camera -> Enable

# Reboot
sudo reboot
```

## Step 6: Test Camera

After reboot:

```bash
# Test with libcamera
libcamera-hello --timeout 5000

# Check V4L2 devices
v4l2-ctl --list-devices
```

## Step 7: Prepare Model Files

Convert your YOLOv8 model to NCNN format:

```bash
# On your development machine (with Python and Ultralytics)
python -c "from ultralytics import YOLO; YOLO('your-model.pt').export(format='onnx')"

# Install NCNN tools (if not already)
# Download from: https://github.com/Tencent/ncnn/releases

# Convert ONNX to NCNN
onnx2ncnn your-model.onnx model.param model.bin

# Optimize
ncnnoptimize model.param model.bin model.ncnn.param model.ncnn.bin 0

# Copy to Raspberry Pi
scp model.ncnn.param model.ncnn.bin pi@raspberrypi:~/tcdd-dev/backend/model/
```

## Step 8: Build C++ Server

```bash
cd ~/tcdd-dev/backend/cpp

# Make build script executable
chmod +x build.sh download_deps.sh

# Build
./build.sh
```

## Step 9: Configure

Edit `shared/config.json`:

```bash
cd ~/tcdd-dev
nano shared/config.json
```

Ensure these settings:

```json
{
  "cppServerPort": 5100,
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "detection": {
    "modelFormat": "ncnn",
    "modelPath": [
      "backend/model/model.ncnn.param",
      "backend/model/model.ncnn.bin"
    ],
    "confidenceThreshold": 0.5,
    "nmsThreshold": 0.5,
    "iouThreshold": 0.5,
    "inputSize": [640, 480]
  },
  "performance": {
    "enableGPU": false,
    "useVulkan": false
  },
  "logging": {
    "format": "csv",
    "path": "logs/",
    "metricsInterval": 1000
  }
}
```

## Step 10: Test Run

```bash
cd ~/tcdd-dev
./backend/cpp_server
```

Expected output:
```
╔════════════════════════════════════════════════╗
║   TCDD C++ Server - Traffic Sign Detection    ║
║   Real-time Object Detection on Raspberry Pi   ║
╚════════════════════════════════════════════════╝

✓ Configuration loaded from: /home/pi/tcdd-dev/shared/config.json
✓ Logger initialized: logs/performance_20250117_143022.csv
Initializing camera: 640x480 @ 30 FPS
  Actual resolution: 640x480 @ 30 FPS
✓ Camera opened successfully
Initializing NCNN detector...
  Param: backend/model/model.ncnn.param
  Bin: backend/model/model.ncnn.bin
  Input size: 640x480
  Confidence: 0.5
  NMS: 0.5
  IoU: 0.5
  Vulkan: disabled
✓ Detector initialized successfully
✓ HTTP server started on port 5100

✓ All systems initialized successfully
✓ Server running on port 5100
✓ Press Ctrl+C to stop

FPS: 28.5 | Inference: 45.2ms | Detections: 2 | CPU: 65% | RAM: 512MB
```

## Step 11: Test API

From another terminal or machine:

```bash
# Test health
curl http://raspberrypi:5100/health

# Test status
curl http://raspberrypi:5100/api/status

# Test detections
curl http://raspberrypi:5100/api/detections

# Test video feed (in browser)
http://raspberrypi:5100/video_feed
```

## Step 12: Update Node.js Proxy

Edit `backend/server.js` to proxy to the C++ server:

```javascript
// Find the proxy configuration
app.use('/video_feed', createProxyMiddleware({
    target: `http://localhost:${config.cppServerPort || 5100}`,
    // ...
}));
```

## Step 13: Create Systemd Service (Optional)

Create `/etc/systemd/system/tcdd-cpp.service`:

```ini
[Unit]
Description=TCDD C++ Detection Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tcdd-dev
ExecStart=/home/pi/tcdd-dev/backend/cpp_server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tcdd-cpp
sudo systemctl start tcdd-cpp
sudo systemctl status tcdd-cpp
```

## Troubleshooting

### Camera Not Detected

```bash
# Check camera
vcgencmd get_camera

# Check V4L2
v4l2-ctl --list-devices

# Check libcamera
libcamera-hello --list-cameras
```

### NCNN Build Fails

```bash
# Ensure dependencies
sudo apt-get install -y libvulkan-dev vulkan-tools

# Try without Vulkan
cmake -DCMAKE_BUILD_TYPE=Release -DNCNN_VULKAN=OFF ..
```

### Low Performance

1. Enable Vulkan in config: `"useVulkan": true`
2. Reduce resolution: `640x480` → `320x240`
3. Lower FPS: `30` → `15`
4. Increase detection interval: `"detectionInterval": 2`

### Memory Issues

```bash
# Increase swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Performance Tuning

### For Best Speed
```json
{
  "camera": {"width": 320, "height": 240, "fps": 15},
  "detection": {"inputSize": [320, 240]},
  "performance": {"useVulkan": true}
}
```

### For Best Quality
```json
{
  "camera": {"width": 1920, "height": 1080, "fps": 15},
  "detection": {"inputSize": [640, 640]},
  "performance": {"useVulkan": true}
}
```

### Balanced
```json
{
  "camera": {"width": 640, "height": 480, "fps": 30},
  "detection": {"inputSize": [640, 480]},
  "performance": {"useVulkan": false}
}
```

## Next Steps

- Test with real traffic sign images
- Tune confidence thresholds
- Analyze performance logs
- Integrate with frontend dashboard
- Set up auto-start on boot

## Resources

- [NCNN Documentation](https://github.com/Tencent/ncnn/wiki)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Raspberry Pi Camera Guide](https://www.raspberrypi.com/documentation/accessories/camera.html)
