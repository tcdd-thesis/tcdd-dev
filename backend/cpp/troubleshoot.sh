#!/bin/bash

# Troubleshooting script for C++ server
# This script performs basic diagnostics and reports common issues

echo "╔════════════════════════════════════════════════╗"
echo "║   TCDD C++ Server Troubleshooting Script       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Function to print test result
check_result() {
    if [ $1 -eq 0 ]; then
        echo "✓ $2"
    else
        echo "✗ $2"
        ERRORS=$((ERRORS + 1))
    fi
}

warn_result() {
    echo "⚠ $1"
    WARNINGS=$((WARNINGS + 1))
}

echo "═══ System Dependencies ═══"

# Check OpenCV
if pkg-config --exists opencv4; then
    VERSION=$(pkg-config --modversion opencv4)
    check_result 0 "OpenCV installed (version $VERSION)"
else
    check_result 1 "OpenCV not found"
fi

# Check NCNN headers
if [ -d "/usr/local/include/ncnn" ]; then
    check_result 0 "NCNN headers found in /usr/local/include/ncnn"
elif [ -d "$HOME/ncnn/build/install/include/ncnn" ]; then
    warn_result "NCNN headers found in local build, not system-wide"
else
    check_result 1 "NCNN headers not found"
fi

# Check NCNN library
if [ -f "/usr/local/lib/libncnn.a" ]; then
    check_result 0 "NCNN library found in /usr/local/lib"
elif [ -f "$HOME/ncnn/build/install/lib/libncnn.a" ]; then
    warn_result "NCNN library found in local build, not system-wide"
else
    check_result 1 "NCNN library not found"
fi

echo ""
echo "═══ Camera ═══"

# Check camera devices
if ls /dev/video* > /dev/null 2>&1; then
    DEVICES=$(ls /dev/video* | wc -l)
    check_result 0 "Found $DEVICES video device(s)"
    ls /dev/video* | while read device; do
        echo "    - $device"
    done
else
    check_result 1 "No video devices found"
fi

# Check if libcamera is working
if command -v libcamera-hello > /dev/null; then
    check_result 0 "libcamera-hello available"
else
    warn_result "libcamera-hello not found"
fi

echo ""
echo "═══ Project Files ═══"

# Check config file
if [ -f "shared/config.json" ]; then
    check_result 0 "Config file exists (shared/config.json)"
    
    # Validate JSON
    if command -v python3 > /dev/null; then
        python3 -m json.tool shared/config.json > /dev/null 2>&1
        check_result $? "Config file is valid JSON"
    fi
else
    check_result 1 "Config file not found (shared/config.json)"
fi

# Check model files
if [ -f "backend/model/model.ncnn.param" ]; then
    check_result 0 "Model param file exists"
else
    warn_result "Model param file not found (backend/model/model.ncnn.param)"
fi

if [ -f "backend/model/model.ncnn.bin" ]; then
    check_result 0 "Model bin file exists"
else
    warn_result "Model bin file not found (backend/model/model.ncnn.bin)"
fi

if [ -f "backend/model/labels.txt" ]; then
    LABELS=$(wc -l < backend/model/labels.txt)
    check_result 0 "Labels file exists ($LABELS classes)"
else
    warn_result "Labels file not found (backend/model/labels.txt)"
fi

# Check if executable exists
if [ -f "backend/cpp/build/tcdd_server" ]; then
    check_result 0 "Server executable built"
else
    check_result 1 "Server executable not found (run ./build.sh)"
fi

echo ""
echo "═══ Network ═══"

# Check if port 5100 is available
if command -v netstat > /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":5100"; then
        warn_result "Port 5100 is already in use"
        netstat -tlnp 2>/dev/null | grep ":5100"
    else
        check_result 0 "Port 5100 is available"
    fi
else
    warn_result "netstat not available, cannot check port"
fi

echo ""
echo "═══ Permissions ═══"

# Check logs directory
if [ -d "logs" ]; then
    if [ -w "logs" ]; then
        check_result 0 "Logs directory is writable"
    else
        check_result 1 "Logs directory exists but is not writable"
    fi
else
    warn_result "Logs directory does not exist (will be created automatically)"
fi

echo ""
echo "═══ Summary ═══"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✓ All checks passed! Ready to run."
elif [ $ERRORS -eq 0 ]; then
    echo "⚠ $WARNINGS warning(s) found. Server may still work."
else
    echo "✗ $ERRORS error(s) and $WARNINGS warning(s) found."
    echo ""
    echo "Common fixes:"
    echo "  1. Install NCNN with: cd ~/ncnn/build && cmake -DCMAKE_INSTALL_PREFIX=/usr/local .. && make -j4 && sudo make install"
    echo "  2. Install OpenCV with: sudo apt-get install libopencv-dev"
    echo "  3. Build server with: cd backend/cpp && ./build.sh"
    echo "  4. Enable camera with: sudo raspi-config (Interface Options -> Camera)"
fi

echo ""
echo "Next steps:"
echo "  - Run server: cd backend/cpp/build && ./tcdd_server"
echo "  - Test health: curl http://localhost:5100/health"
echo "  - View logs: tail -f logs/*.csv"
echo ""
