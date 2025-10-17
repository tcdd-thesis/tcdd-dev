#!/bin/bash

# Build script for C++ server on Raspberry Pi
# Run this script from the backend/cpp directory

set -e

echo "============================================"
echo "TCDD C++ Server Build Script"
echo "============================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠ Warning: Not running on Raspberry Pi"
    echo "  This script is optimized for Raspberry Pi 5"
    echo ""
fi

# Create build directory
echo "Creating build directory..."
mkdir -p build

# Download nlohmann/json if not present
if [ ! -f "../third_party/json.hpp" ]; then
    echo "Downloading nlohmann/json..."
    chmod +x ./download_deps.sh
    (./download_deps.sh)
fi

cd build

# Check for dependencies
echo ""
echo "Checking dependencies..."

# Check for CMake
if ! command -v cmake &> /dev/null; then
    echo "✗ CMake not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y cmake
fi

# Check for OpenCV
if ! pkg-config --exists opencv4; then
    echo "✗ OpenCV not found. Installing..."
    sudo apt-get install -y libopencv-dev
fi

# Check for NCNN
if [ ! -d "/usr/local/include/ncnn" ]; then
    echo "✗ NCNN not found."
    echo "  Please install NCNN from: https://github.com/Tencent/ncnn"
    echo "  Or run: sudo apt-get install libncnn-dev (if available)"
    exit 1
fi

echo "✓ All dependencies found"
echo ""

# Configure with CMake
echo "Configuring project..."
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-march=armv8-a+crc+simd -mtune=cortex-a76"

echo ""
echo "Building project..."
make -j$(nproc)

echo ""
echo "============================================"
echo "✓ Build completed successfully!"
echo "============================================"
echo ""
echo "Executable location: backend/cpp_server"
echo ""
echo "To run the server:"
echo "  cd ../.. "
echo "  ./backend/cpp_server"
echo ""
echo "To run with Vulkan:"
echo "  ./backend/cpp_server -v"
echo ""
