# Verbose Logging - Flag-Controlled Implementation

## Summary

The verbose logging system has been updated to be **optional and controlled by the `--verbose` command-line flag**. This provides:

- **Clean output by default** for production use
- **Detailed logging on demand** for debugging and troubleshooting
- **No performance impact** when verbose logging is disabled

## Usage

```bash
# Normal mode - clean output (DEFAULT)
./tcdd_server

# Debug mode - verbose output
./tcdd_server --verbose

# Combined with other flags
./tcdd_server --verbose --vulkan --file video.mp4
```

## What You See

### Without --verbose (Default)
```
╔════════════════════════════════════════════════╗
║   TCDD C++ Server - Traffic Sign Detection     ║
╚════════════════════════════════════════════════╝

✓ All systems initialized successfully
✓ Server running on port 5100
✓ Press Ctrl+C to stop

FPS: 29.5 | Inference: 42.8ms | Detections: 2 | CPU: 45% | RAM: 512MB
```

### With --verbose
```
╔════════════════════════════════════════════════╗
║   TCDD C++ Server - Traffic Sign Detection     ║
╚════════════════════════════════════════════════╝

✓ All systems initialized successfully
✓ Server running on port 5100
✓ Press Ctrl+C to stop

════════════════════════════════════════════════
Verbose logging enabled:
  [HTTP]     - HTTP requests and responses
  [API]      - API endpoint calls
  [SERVER]   - Server data updates
  [CAMERA]   - Camera frame capture
  [DETECTOR] - Object detection operations
════════════════════════════════════════════════

[CAMERA] Captured frame #1 (640x480)
[MAIN] Processing frame #1 (640x480)
[DETECTOR] Frame #1: 2 detections in 45.2ms
[SERVER] Updated 1 frames (640x480)
[HTTP] 192.168.1.100:52314 -> GET /video_feed HTTP/1.1
[HTTP] Starting MJPEG stream for 192.168.1.100
...
```

## Implementation Details

### New Files
- `logging_flags.h` - Global verbose flag declaration
- `logging_flags.cpp` - Global verbose flag implementation

### Modified Files
- `http_server.h/cpp` - Checks `verboseLogging` static flag
- `main.cpp` - Parses `--verbose` flag, sets global flags
- `detector.cpp` - Checks `Logging::verbose` before logging
- `camera.cpp` - Checks `Logging::verbose` before logging
- `CMakeLists.txt` - Added `logging_flags.cpp` to build

### Log Categories (Only with --verbose)
- `[HTTP]` - HTTP requests, responses, client info
- `[API]` - API endpoint handler calls
- `[SERVER]` - Frame/detection/status updates
- `[CAMERA]` - Frame capture operations
- `[DETECTOR]` - Inference runs and timing
- `[MAIN]` - Main loop operations

## Troubleshooting Workflow

1. **Normal operation**: Run without flags
   ```bash
   ./tcdd_server
   ```

2. **Issue detected**: Enable verbose logging
   ```bash
   ./tcdd_server --verbose
   ```

3. **Analyze logs**: Filter by category
   ```bash
   ./tcdd_server --verbose | grep "\[HTTP\]"
   ./tcdd_server --verbose | grep "Error"
   ```

4. **Save logs**: Redirect to file
   ```bash
   ./tcdd_server --verbose 2>&1 | tee debug.log
   ```

## Benefits

✅ **Clean production output** - No log spam in normal operation  
✅ **Detailed debugging** - Full visibility when needed  
✅ **Zero overhead** - No performance cost when disabled  
✅ **Easy troubleshooting** - Turn on/off without rebuilding  
✅ **Flexible filtering** - Use grep to focus on specific issues  

## Next Steps on Raspberry Pi

```bash
# 1. Complete NCNN installation (if not done)
cd ~/ncnn/build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make -j4
sudo make install
sudo ldconfig

# 2. Rebuild C++ server
cd ~/tcdd-dev/backend/cpp
./build.sh

# 3. Test normal mode
cd build
./tcdd_server

# 4. Test verbose mode (for debugging)
./tcdd_server --verbose

# 5. Debug specific issues
./tcdd_server --verbose | grep "\[HTTP\]"   # HTTP issues
./tcdd_server --verbose | grep "\[CAMERA\]" # Camera issues
./tcdd_server --verbose | grep "Error"      # All errors
```

## Documentation

- **[README.md](README.md)** - Overview with `--verbose` examples
- **[QUICKREF.md](QUICKREF.md)** - Quick reference with flag usage
- **[VERBOSE_LOGGING.md](VERBOSE_LOGGING.md)** - Comprehensive logging guide
- **[LOGGING_IMPLEMENTATION.md](LOGGING_IMPLEMENTATION.md)** - Technical details
- **[troubleshoot.sh](troubleshoot.sh)** - System diagnostic script

---

**Perfect for**: Development, debugging, and troubleshooting while keeping production output clean and professional! 🎯
