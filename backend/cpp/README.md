# C++ Server Implementation

## Overview

This directory contains the C++ implementation of the TCDD traffic sign detection server. It replaces the Python `camera_server.py` with a high-performance C++ implementation using NCNN for inference.

## Features

- **NCNN Inference**: Optimized YOLOv8 inference using NCNN
- **OpenCV Camera**: Raspberry Pi camera capture via V4L2/libcamera
- **HTTP API**: Compatible endpoints with the Python version
- **MJPEG Streaming**: Real-time video feed
- **CSV Logging**: Performance metrics logging
- **Vulkan Support**: Optional GPU acceleration
- **Multi-threaded**: Concurrent capture, inference, and serving
- **Verbose Logging**: Comprehensive request/response tracking for troubleshooting

## Quick Start

```bash
# 1. Install dependencies and build (first time only)
cd backend/cpp
chmod +x troubleshoot.sh build.sh
./troubleshoot.sh  # Check if everything is ready
./build.sh         # Build the server

# 2. Run the server
cd build
./tcdd_server

# 3. Run with verbose logging (for debugging)
./tcdd_server --verbose

# 4. Test endpoints
curl http://localhost:5100/health
curl http://localhost:5100/api/status
```

See [SETUP.md](SETUP.md) for detailed installation instructions.

## Troubleshooting

If you encounter issues:

```bash
# Run the troubleshooting script
cd backend/cpp
./troubleshoot.sh

# Run with verbose logging to see detailed operations
./build/tcdd_server --verbose 2>&1 | tee server.log

# Filter specific issues
./build/tcdd_server --verbose | grep "\[HTTP\]"   # HTTP requests only
./build/tcdd_server --verbose | grep "Error"      # Errors only
```

**Note**: Verbose logging is disabled by default. Use the `--verbose` flag to enable detailed logging for troubleshooting.

See [VERBOSE_LOGGING.md](VERBOSE_LOGGING.md) for detailed logging documentation.

## Dependencies

### Required
- **CMake** >= 3.10
- **OpenCV** >= 4.0 (with V4L2 support)
- **NCNN** (latest version)
- **C++17 compiler** (GCC 8+, Clang 7+)

### Optional
- **Vulkan** (for GPU acceleration)

## Installation

### On Raspberry Pi

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y cmake build-essential libopencv-dev

# Install NCNN (if not already installed)
# See: https://github.com/Tencent/ncnn

# Build the project
cd backend/cpp
chmod +x build.sh
./build.sh
```

## Project Structure

```
backend/cpp/
├── CMakeLists.txt          # Build configuration
├── build.sh                # Build script for Raspberry Pi
├── main.cpp                # Main application entry point
├── config_loader.h/cpp     # Configuration management
├── logger.h/cpp            # CSV logging
├── camera.h/cpp            # Camera capture
├── detector.h/cpp          # NCNN inference
├── http_server.h/cpp       # HTTP API server
└── third_party/
    └── json.hpp            # nlohmann/json (single header)
```

## Configuration

The C++ server **requires** a valid configuration file to run. It reads from `shared/config.json` by default. If the config file is not found or cannot be loaded, the program will terminate with an error message.

**Flexible Configuration System:**
- ✅ Add new config keys without rebuilding C++
- ✅ Change config structure dynamically  
- ✅ Just edit `config.json` and restart the server
- ✅ No code changes needed for new config parameters

See [CONFIG_USAGE.md](CONFIG_USAGE.md) for detailed usage guide.

Key settings:

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
    "modelPath": ["backend/model/model.ncnn.param", "backend/model/model.ncnn.bin"],
    "labelsPath": "backend/model/labels.txt",
    "confidenceThreshold": 0.5,
    "nmsThreshold": 0.5,
    "iouThreshold": 0.5,
    "inputSize": [640, 480]
  },
  "performance": {
    "useVulkan": false
  },
  "logging": {
    "format": "csv",
    "path": "logs/",
    "metricsInterval": 1000
  }
}
```

## Usage

### Basic Usage

```bash
cd backend
./cpp_server
```

### With Verbose Logging (for debugging)

```bash
./cpp_server --verbose
```

### With Video File (for testing)

```bash
./cpp_server --file path/to/video.mp4
```

### Without ML Detection (for troubleshooting)

```bash
./cpp_server --no-ml
```

This disables model loading and inference, showing only the camera feed. Useful for:
- Testing camera feed without ML overhead
- Isolating camera vs detection issues
- Debugging false positive problems

### With Vulkan Acceleration

```bash
./cpp_server --vulkan
```

### Custom Config

```bash
./cpp_server --config path/to/config.json
```

### Combined Flags

```bash
./cpp_server --verbose --vulkan --file video.mp4
./cpp_server --verbose --no-ml  # Test camera feed only
```

## API Endpoints

The C++ server provides the same API as the Python version:

### GET `/video_feed`
Returns MJPEG stream of the camera feed with detections drawn.

### GET `/api/detections`
Returns JSON array of current detections:
```json
{
  "success": true,
  "count": 2,
  "detections": [
    {
      "class": "stop_sign",
      "confidence": 0.95,
      "bbox": [100, 150, 200, 200]
    }
  ]
}
```

### GET `/api/status`
Returns current system status:
```json
{
  "fps": 28.5,
  "inference_time_ms": 45.2,
  "detections_count": 2,
  "total_detections": 150,
  "cpu_usage_percent": 65.3,
  "ram_usage_mb": 512.4,
  "camera_width": 640,
  "camera_height": 480,
  "running": true
}
```

### GET `/health`
Health check endpoint:
```json
{
  "status": "ok",
  "server": "cpp",
  "port": 5100
}
```

## Performance Logging

Performance metrics are logged to CSV files in the `logs/` directory. Each session creates a new file:

```
logs/performance_20250117_143022.csv
```

### Logged Metrics

- `timestamp`: ISO 8601 timestamp
- `fps`: Frames per second
- `inference_time_ms`: Model inference time
- `detections_count`: Current frame detections
- `cpu_usage_percent`: CPU utilization
- `ram_usage_mb`: RAM usage in MB
- `camera_frame_time_ms`: Frame capture time
- `jpeg_encode_time_ms`: JPEG encoding time
- `total_detections`: Cumulative detection count
- `dropped_frames`: Number of dropped frames
- `queue_size`: Processing queue size

## Model Conversion

### Convert YOLOv8 to NCNN

```bash
# 1. Export to ONNX
python -m ultralytics export model=path/to/model.pt format=onnx

# 2. Convert ONNX to NCNN
onnx2ncnn model.onnx model.param model.bin

# 3. Optimize (optional)
ncnnoptimize model.param model.bin optimized.param optimized.bin 0

# 4. Place in backend/model/
cp optimized.param backend/model/model.ncnn.param
cp optimized.bin backend/model/model.ncnn.bin
```

## Integration with Node.js Backend

Update `backend/server.js` to proxy to the C++ server:

```javascript
// Change pythonServerPort to cppServerPort
const config = ConfigLoader.loadConfig();
const proxyTarget = `http://localhost:${config.cppServerPort || 5100}`;
```

## Troubleshooting

### Quick Diagnostics

Run the troubleshooting script to check your setup:

```bash
cd backend/cpp
chmod +x troubleshoot.sh
./troubleshoot.sh
```

This will check:
- System dependencies (OpenCV, NCNN)
- Camera devices
- Config and model files
- Network ports
- File permissions

### Common Issues

#### Camera Not Found
- Ensure Raspberry Pi camera is enabled: `sudo raspi-config`
- Check camera connection: `libcamera-hello`
- Try V4L2 devices: `v4l2-ctl --list-devices`
- Check verbose logs: `./tcdd_server | grep "\[CAMERA\]"`

#### NCNN Model Loading Fails
- Verify model files exist and paths are correct
- Check param/bin file compatibility
- Ensure input/output layer names match (default: "in0", "out0")
- Check initialization logs at startup

#### /video_feed Loading Forever
Enable verbose logging to diagnose:
```bash
./tcdd_server | grep -E "\[HTTP\]|\[CAMERA\]"
```

Look for:
- HTTP connection established
- MJPEG stream started
- Frames being sent
- Empty frame warnings

See [VERBOSE_LOGGING.md](VERBOSE_LOGGING.md) for detailed diagnostics.

#### /api/status Returns null
Check if status is being updated:
```bash
./tcdd_server | grep -E "\[API\]|\[SERVER\]"
```

Should see:
- `[SERVER] Status update` messages
- `[API] handleGetStatus called - Status: OK`

If status is EMPTY, main loop may not be running.

#### Low FPS
- Enable Vulkan if available
- Reduce input resolution
- Increase `detectionInterval`
- Lower JPEG quality

### Build Errors
- Ensure all dependencies are installed
- Check CMake version: `cmake --version`
- Verify OpenCV installation: `pkg-config --modversion opencv4`
- Check NCNN installation: `ls /usr/local/include/ncnn`

## Development

### Adding New Features

1. **Custom Preprocessing**: Modify `detector.cpp::preprocess()`
2. **New Endpoints**: Add handlers in `http_server.cpp`
3. **Additional Metrics**: Extend `Logger::Metrics` struct
4. **Configuration**: Add getters in `config_loader.h/cpp`

### Code Style

- Use C++17 features
- Follow RAII principles
- Thread-safe operations with mutexes
- Prefer smart pointers over raw pointers

## Performance Benchmarks

Target performance on Raspberry Pi 5:

- **FPS**: 25-30 FPS (640x480)
- **Inference Time**: 30-50ms (NCNN CPU)
- **Inference Time**: 15-25ms (NCNN Vulkan)
- **Latency**: <100ms end-to-end

## Documentation

- **[README.md](README.md)**: This file - overview and quick start
- **[SETUP.md](SETUP.md)**: Detailed installation and setup guide
- **[QUICKREF.md](QUICKREF.md)**: Quick reference for common commands
- **[CONFIG_USAGE.md](CONFIG_USAGE.md)**: Configuration system guide
- **[VERBOSE_LOGGING.md](VERBOSE_LOGGING.md)**: Logging and troubleshooting guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**: Technical implementation details
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)**: Production deployment checklist
- **[REFACTOR_SUMMARY.md](REFACTOR_SUMMARY.md)**: Configuration refactoring notes

## License

Same as parent project.
