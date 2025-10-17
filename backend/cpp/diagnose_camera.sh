#!/bin/bash

# Camera diagnostic script
# Helps identify camera issues on Raspberry Pi

echo "╔════════════════════════════════════════════════╗"
echo "║   Raspberry Pi Camera Diagnostic Tool          ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠ Warning: This doesn't appear to be a Raspberry Pi"
    echo ""
fi

echo "═══ Camera Hardware Detection ═══"

# Check for camera devices
if ls /dev/video* > /dev/null 2>&1; then
    echo "✓ Video devices found:"
    for device in /dev/video*; do
        echo "  - $device"
        if command -v v4l2-ctl > /dev/null; then
            v4l2-ctl --device=$device --info 2>/dev/null | grep -E "(Card type|Driver name)" | sed 's/^/    /'
        fi
    done
else
    echo "✗ No /dev/video* devices found"
fi

echo ""

# Check libcamera
echo "═══ libcamera ═══"
if command -v libcamera-hello > /dev/null; then
    echo "✓ libcamera-hello is installed"
    echo ""
    echo "Testing camera with libcamera-hello..."
    if timeout 3 libcamera-hello --timeout 1 > /dev/null 2>&1; then
        echo "✓ Camera works with libcamera"
    else
        echo "✗ Camera test with libcamera failed"
    fi
else
    echo "✗ libcamera-hello not found"
    echo "  Install with: sudo apt-get install libcamera-apps"
fi

echo ""

# Check v4l2
echo "═══ V4L2 ═══"
if command -v v4l2-ctl > /dev/null; then
    echo "✓ v4l2-ctl is installed"
    if ls /dev/video0 > /dev/null 2>&1; then
        echo ""
        echo "Supported formats for /dev/video0:"
        v4l2-ctl --device=/dev/video0 --list-formats-ext 2>/dev/null | head -20
    fi
else
    echo "✗ v4l2-ctl not found"
    echo "  Install with: sudo apt-get install v4l-utils"
fi

echo ""

# Check GStreamer
echo "═══ GStreamer ═══"
if command -v gst-launch-1.0 > /dev/null; then
    echo "✓ GStreamer is installed"
    
    # Check for libcamerasrc plugin
    if gst-inspect-1.0 libcamerasrc > /dev/null 2>&1; then
        echo "✓ libcamerasrc plugin available"
        echo ""
        echo "Testing camera with GStreamer..."
        if timeout 3 gst-launch-1.0 libcamerasrc ! videoconvert ! fakesink > /dev/null 2>&1; then
            echo "✓ Camera works with GStreamer + libcamerasrc"
        else
            echo "✗ GStreamer test failed"
        fi
    else
        echo "✗ libcamerasrc plugin not found"
        echo "  Install with: sudo apt-get install gstreamer1.0-libcamera"
    fi
else
    echo "✗ GStreamer not found"
    echo "  Install with: sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base"
fi

echo ""

# Check OpenCV
echo "═══ OpenCV ═══"
if command -v pkg-config > /dev/null && pkg-config --exists opencv4; then
    VERSION=$(pkg-config --modversion opencv4)
    echo "✓ OpenCV installed: version $VERSION"
    
    # Check GStreamer support in OpenCV
    if pkg-config --libs opencv4 | grep -q gstreamer; then
        echo "✓ OpenCV compiled with GStreamer support"
    else
        echo "⚠ OpenCV may not have GStreamer support"
    fi
else
    echo "✗ OpenCV not found or pkg-config missing"
fi

echo ""

# Check camera configuration
echo "═══ Camera Configuration ═══"

if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_FILE="/boot/config.txt"
else
    CONFIG_FILE=""
fi

if [ -n "$CONFIG_FILE" ]; then
    echo "Checking $CONFIG_FILE:"
    
    if grep -q "^camera_auto_detect=1" "$CONFIG_FILE" 2>/dev/null; then
        echo "  ✓ camera_auto_detect=1"
    else
        echo "  ⚠ camera_auto_detect not enabled"
        echo "    Add to $CONFIG_FILE: camera_auto_detect=1"
    fi
    
    if grep -q "^dtoverlay=imx708" "$CONFIG_FILE" 2>/dev/null; then
        echo "  ✓ Camera Module 3 overlay detected (imx708)"
    fi
else
    echo "⚠ Could not find config.txt"
fi

echo ""

# Recommendations
echo "═══ Recommendations ═══"

ISSUES=0

if ! ls /dev/video* > /dev/null 2>&1; then
    echo "✗ No camera devices detected"
    echo "  1. Check camera cable connection"
    echo "  2. Enable camera: sudo raspi-config -> Interface Options -> Camera"
    echo "  3. Reboot: sudo reboot"
    ISSUES=$((ISSUES + 1))
fi

if ! command -v libcamera-hello > /dev/null; then
    echo "⚠ Install libcamera: sudo apt-get install libcamera-apps"
    ISSUES=$((ISSUES + 1))
fi

if ! gst-inspect-1.0 libcamerasrc > /dev/null 2>&1; then
    echo "⚠ Install GStreamer libcamera plugin: sudo apt-get install gstreamer1.0-libcamera"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "✓ Camera setup looks good!"
    echo ""
    echo "If C++ server still fails, try:"
    echo "  1. Use a test video file: ./cpp_server --file /path/to/video.mp4"
    echo "  2. Check permissions: sudo usermod -a -G video $USER"
    echo "  3. Test with verbose: ./cpp_server --verbose"
fi

echo ""
