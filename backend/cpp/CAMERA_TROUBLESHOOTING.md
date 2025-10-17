# Camera Troubleshooting Guide

## Problem: "Failed to read from camera" Error

If you see continuous `[CAMERA] Error: Failed to read from camera` messages, the camera is not working properly with OpenCV.

## Quick Diagnosis

Run the camera diagnostic script:

```bash
cd backend/cpp
chmod +x diagnose_camera.sh
./diagnose_camera.sh
```

This will check:
- Camera hardware detection
- libcamera availability
- V4L2 devices
- GStreamer support
- OpenCV configuration

## Common Causes & Solutions

### 1. Camera Not Enabled

**Check:**
```bash
ls /dev/video*
```

**If no devices found:**
```bash
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable
sudo reboot
```

### 2. Wrong Backend (Raspberry Pi Camera Module V3)

The Pi Camera Module V3 uses libcamera, not V4L2. The C++ server now tries multiple backends automatically:

1. **GStreamer** (best for libcamera)
2. **V4L2** (legacy cameras)
3. **ANY** (OpenCV default)

**Install GStreamer support:**
```bash
sudo apt-get install gstreamer1.0-libcamera \
                     gstreamer1.0-tools \
                     gstreamer1.0-plugins-base \
                     gstreamer1.0-plugins-good
```

### 3. OpenCV Not Compiled with GStreamer

**Check if OpenCV has GStreamer support:**
```bash
pkg-config --libs opencv4 | grep gstreamer
```

**If no output**, OpenCV doesn't have GStreamer support. You have two options:

**Option A: Rebuild OpenCV with GStreamer (advanced)**
```bash
# This takes 1-2 hours on Raspberry Pi 5
cd ~
git clone https://github.com/opencv/opencv.git
cd opencv
mkdir build && cd build
cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D WITH_GSTREAMER=ON \
      -D BUILD_EXAMPLES=OFF \
      ..
make -j4
sudo make install
```

**Option B: Use a test video file instead**
```bash
./cpp_server --file /path/to/video.mp4
```

### 4. Permissions Issue

Add your user to the `video` group:
```bash
sudo usermod -a -G video $USER
```

Then log out and log back in (or reboot).

### 5. Camera Cable/Hardware Issue

**Test with libcamera directly:**
```bash
libcamera-hello --timeout 5000
```

If this fails:
- Check camera cable connection
- Try reseating the cable
- Test with `vcgencmd get_camera` (legacy)

## Testing Each Backend

### Test with GStreamer
```bash
gst-launch-1.0 libcamerasrc ! videoconvert ! autovideosink
```

### Test with V4L2
```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext
ffplay /dev/video0
```

### Test with OpenCV (Python quick test)
```python
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print(f"Success: {ret}, Frame shape: {frame.shape if ret else 'N/A'}")
cap.release()
```

## Updated Camera Code

The camera initialization now tries multiple backends automatically and tests frame capture for each one:

```cpp
// Tries in order:
1. GStreamer with libcamerasrc pipeline (best for Pi Camera Module V3)
2. V4L2 backend (legacy cameras, USB cameras)
3. ANY backend (OpenCV default)
```

For each backend, it:
- Opens the camera
- Attempts to read a test frame
- Only proceeds if frame capture succeeds

## Workaround: Use Video File

While debugging camera issues, use a test video file:

```bash
# Download a test video
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 -O test.mp4

# Run with video file
./cpp_server --file test.mp4 --verbose
```

## Still Not Working?

1. **Check system logs:**
   ```bash
   dmesg | grep -i camera
   journalctl -xe | grep -i camera
   ```

2. **Verify camera is detected:**
   ```bash
   vcgencmd get_camera  # Legacy
   libcamera-hello --list-cameras  # Modern
   ```

3. **Check config.txt:**
   ```bash
   cat /boot/firmware/config.txt | grep camera
   ```
   
   Should have:
   ```
   camera_auto_detect=1
   ```

4. **Try different camera index:**
   Modify code to try `/dev/video1`, `/dev/video2`, etc.

5. **File an issue** with the output of:
   ```bash
   ./diagnose_camera.sh
   ./cpp_server --verbose 2>&1 | head -100
   ```

## Next Steps

After fixing camera issues, rebuild and test:

```bash
cd backend/cpp
./build.sh
cd build
./cpp_server --verbose
```

Look for:
```
✓ Camera opened successfully
[CAMERA] Captured frame #1 (640x480)
```

If you see this, the camera is working! 🎉
