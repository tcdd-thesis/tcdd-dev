# Verbose Logging Implementation Summary

## Overview

The C++ backend has been enhanced with comprehensive verbose logging to track all operations throughout the system. **Verbose logging is controlled by the `--verbose` command-line flag** and is disabled by default for clean production output.

This makes debugging and troubleshooting significantly easier by providing real-time visibility into:

- HTTP requests and responses
- Client connections and disconnections
- API endpoint calls
- Data updates (frames, detections, status)
- Camera operations
- Object detection pipeline
- Main loop execution

## Key Design Decision: Optional Verbose Logging

**By default**, the server runs with minimal output showing only:
- Startup and initialization messages
- Real-time performance metrics
- Critical errors

**With `--verbose` flag**, detailed operational logging is enabled:
```bash
./tcdd_server --verbose
```

## What Was Changed

### 1. Global Verbose Flag System

Created a centralized verbose logging control:

**New files**:
- `logging_flags.h` - Header declaring global `Logging::verbose` flag
- `logging_flags.cpp` - Implementation of global flag (default: `false`)

**Integration**:
- `main.cpp` - Parses `--verbose` flag and sets global state
- `http_server.h/cpp` - Static `verboseLogging` flag
- All modules check the flag before logging

### 2. HTTP Server (`http_server.cpp`)

#### Client Connection Logging
- **Added**: Client IP and port tracking for all connections
- **Added**: Request line logging for every HTTP request
- **Format**: `[HTTP] 192.168.1.100:52314 -> GET /video_feed HTTP/1.1`

#### Endpoint-Specific Logging

**`/video_feed` (MJPEG Stream)**:
- Logs when stream starts
- Counts frames sent (every 100 frames)
- Logs client disconnections with frame count
- Warns when empty frames are encountered

**`/api/detections`**:
- Logs when endpoint is called
- Shows detection count
- Displays response preview (first 100 chars)

**`/api/status`**:
- Logs when endpoint is called
- Shows if status object is empty or populated
- Displays full status JSON response
- **Warns** if status is empty (helps debug null response issue)

**`/health`**:
- Logs health check requests
- Shows response JSON

**404 Not Found**:
- Logs unknown endpoints and client IP

#### Data Update Logging

**`updateFrame()`**:
- Logs every 100 frames
- Shows frame dimensions

**`updateDetections()`**:
- Logs every 100 updates OR when detections found
- Shows object count

**`updateStatus()`**:
- Logs every 100 updates
- Confirms status is being updated

### 2. Main Loop (`main.cpp`)

#### Command-Line Argument Parsing
Added `--verbose` flag support:
```cpp
./tcdd_server --verbose
./tcdd_server --verbose --vulkan --file video.mp4
```

#### Startup Banner
Conditional verbose banner that only shows when `--verbose` is used:
```
════════════════════════════════════════════════
Verbose logging enabled:
  [HTTP]     - HTTP requests and responses
  [API]      - API endpoint calls
  [SERVER]   - Server data updates
  [CAMERA]   - Camera frame capture
  [DETECTOR] - Object detection operations
════════════════════════════════════════════════
```

#### Frame Processing
All verbose logs wrapped in `if (verboseLogging)` checks.

### 3. Detector (`detector.cpp`)

#### Detection Pipeline
All verbose logging wrapped in `if (Logging::verbose)` checks:
- Logs empty frame or uninitialized warnings
- Tracks detection runs (every 100 frames or when objects detected)
- Shows number of detections found
- Reports inference time
- Warns if inference extraction fails

### 4. Camera (`camera.cpp`)

#### Capture Operations
All verbose logging wrapped in `if (Logging::verbose)` checks:
- Logs frame captures (every 100 frames)
- Shows frame dimensions
- Reports video file looping
- Warns on capture failures
- Errors on empty frames

### 5. Documentation

#### New Files Created

**`VERBOSE_LOGGING.md`** (Comprehensive logging guide):
- Explanation of all log categories
- Example log messages
- Common debugging scenarios
- Log filtering techniques
- Expected startup sequence
- Troubleshooting tips

**`troubleshoot.sh`** (Diagnostic script):
- Checks system dependencies (OpenCV, NCNN)
- Verifies camera devices
- Validates config and model files
- Tests network ports
- Checks file permissions
- Provides actionable error messages

#### Updated Files

**`README.md`**:
- Added Quick Start section with troubleshooting
- Added verbose logging feature
- Added troubleshooting section with common issues
- Added documentation index

**`SETUP.md`**:
- Fixed NCNN installation to include `-DCMAKE_INSTALL_PREFIX=/usr/local`
- Added verification step to check `/usr/local/lib/libncnn.a`

## Log Categories

| Tag | Purpose | Frequency |
|-----|---------|-----------|
| `[HTTP]` | HTTP requests, connections, responses | Every request |
| `[API]` | API endpoint handler calls | Every call |
| `[SERVER]` | Data updates (frames, detections, status) | Every 100 updates or when relevant |
| `[CAMERA]` | Frame capture, video looping, errors | Every 100 frames or on errors |
| `[DETECTOR]` | Inference runs, timing, results | Every 100 frames or when detections found |
| `[MAIN]` | Main loop iterations, dropped frames | Every 100 frames or on issues |

## Benefits

### 1. Easy Troubleshooting
You can now quickly identify issues:

```bash
# Check if HTTP requests are reaching the server
./tcdd_server | grep "\[HTTP\]"

# See if camera is capturing frames
./tcdd_server | grep "\[CAMERA\]"

# Monitor detection performance
./tcdd_server | grep "\[DETECTOR\]"

# Find all errors
./tcdd_server | grep -E "Error|Warning"
```

### 2. Real-time Monitoring
The logs show exactly what's happening at every stage:

```
[CAMERA] Captured frame #1 (640x480)
[MAIN] Processing frame #1 (640x480)
[DETECTOR] Frame #1: 2 detections in 45.2ms
[SERVER] Updated 1 frames (640x480)
[SERVER] Detection update #1: 2 objects
[HTTP] 192.168.1.100:52314 -> GET /api/status HTTP/1.1
[API] handleGetStatus called - Status: OK
[HTTP] Status response: {"fps":29.5,"detections_count":2,...}
```

### 3. Diagnosing Specific Issues

**Issue: /video_feed loading forever**

Look for:
```
[HTTP] Starting MJPEG stream for 192.168.1.100
[HTTP] Warning: Empty frame, waiting...
```
→ Camera not capturing frames

**Issue: /api/status returns null**

Look for:
```
[API] handleGetStatus called - Status: EMPTY
[API] WARNING: currentStatus is empty
```
→ Status not being updated in main loop

### 4. Performance Tracking
Logs show frame counts, timing, and throughput:
```
[HTTP] Streamed 100 frames to 192.168.1.100
[DETECTOR] Frame #100: 0 detections in 43.1ms
```

## Usage Examples

### Normal Operation (No Verbose Logging)
```bash
./tcdd_server

# Output:
# ✓ All systems initialized successfully
# ✓ Server running on port 5100
# FPS: 29.5 | Inference: 42.8ms | Detections: 2 | CPU: 45% | RAM: 512MB
```

### Debug Mode (With Verbose Logging)
```bash
./tcdd_server --verbose

# Output includes all operational details:
# [HTTP] 192.168.1.100:52314 -> GET /video_feed HTTP/1.1
# [CAMERA] Captured frame #1 (640x480)
# [DETECTOR] Frame #1: 2 detections in 45.2ms
# ...
```

### Save Verbose Logs to File
```bash
./tcdd_server --verbose 2>&1 | tee logs/server_$(date +%Y%m%d_%H%M%S).log
```

### Filter Specific Log Categories
```bash
# Only HTTP activity
./tcdd_server --verbose | grep "\[HTTP\]"

# Only errors and warnings
./tcdd_server --verbose | grep -E "Error|Warning"
```

### Run Diagnostics Before Starting
```bash
cd backend/cpp
chmod +x troubleshoot.sh
./troubleshoot.sh
```

## Testing the Implementation

After rebuilding on Raspberry Pi, you should see logs like:

```
╔════════════════════════════════════════════════╗
║   TCDD C++ Server - Traffic Sign Detection     ║
╚════════════════════════════════════════════════╝

✓ Loaded configuration from: shared/config.json
✓ Logger initialized: logs/
Initializing camera: 640x480 @ 30 FPS
✓ Camera opened successfully
...
✓ All systems initialized successfully
✓ Server running on port 5100

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
[DETECTOR] Frame #1: 0 detections in 45.2ms
[SERVER] Updated 1 frames (640x480)
...
```

Then when you access endpoints:

```bash
curl http://localhost:5100/health
```

You should see:
```
[HTTP] 127.0.0.1:54123 -> GET /health HTTP/1.1
[API] handleHealth called
[HTTP] Health response: {"status":"ok","server":"cpp","port":5100}
```

## Next Steps

1. **Rebuild on Raspberry Pi**:
   ```bash
   cd ~/tcdd-dev/backend/cpp
   ./build.sh
   ```

2. **Run with logging**:
   ```bash
   cd build
   ./tcdd_server 2>&1 | tee ../logs/server.log
   ```

3. **Test endpoints and observe logs**:
   ```bash
   # In another terminal
   curl http://localhost:5100/health
   curl http://localhost:5100/api/status
   ```

4. **Debug issues**:
   - Use grep to filter specific log categories
   - Look for errors and warnings
   - Check if data is flowing through the system
   - Verify status is not empty

## Files Modified

- `backend/cpp/logging_flags.h`: **NEW** - Global verbose flag declaration
- `backend/cpp/logging_flags.cpp`: **NEW** - Global verbose flag implementation
- `backend/cpp/http_server.h`: Added static `setVerbose()` method
- `backend/cpp/http_server.cpp`: All logging wrapped in `verboseLogging` checks
- `backend/cpp/main.cpp`: Added `--verbose` flag parsing and global flag setup
- `backend/cpp/detector.cpp`: All logging wrapped in `Logging::verbose` checks
- `backend/cpp/camera.cpp`: All logging wrapped in `Logging::verbose` checks
- `backend/cpp/CMakeLists.txt`: Added `logging_flags.cpp` to build
- `backend/cpp/SETUP.md`: Fixed NCNN installation instructions
- `backend/cpp/README.md`: Added `--verbose` flag documentation
- `backend/cpp/QUICKREF.md`: Added `--verbose` usage examples
- `backend/cpp/VERBOSE_LOGGING.md`: Updated with `--verbose` flag info
- `backend/cpp/LOGGING_IMPLEMENTATION.md`: This file - updated summary

## Summary

You now have:

✅ **Optional verbose logging** controlled by `--verbose` flag  
✅ **Clean output by default** for production use  
✅ **Detailed logging on demand** for troubleshooting  
✅ **Real-time visibility** into all operations when needed  
✅ **Easy troubleshooting** with filtered logs  
✅ **Diagnostic script** to check system health  
✅ **Complete documentation** for using the logging system  
✅ **Fixed NCNN setup** instructions with correct CMAKE_INSTALL_PREFIX  

### Quick Commands

```bash
# Normal mode (clean output)
./tcdd_server

# Debug mode (verbose output)
./tcdd_server --verbose

# Debug with log file
./tcdd_server --verbose 2>&1 | tee server.log

# Check system health
./troubleshoot.sh
```

This should make it much easier to identify and fix issues while keeping production output clean!
