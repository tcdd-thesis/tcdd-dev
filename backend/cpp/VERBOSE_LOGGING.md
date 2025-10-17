# Verbose Logging Guide

The C++ server includes comprehensive verbose logging to help track all operations and troubleshoot issues. **Verbose logging is disabled by default** and can be enabled with the `--verbose` flag.

## Enabling Verbose Logging

```bash
# Run with verbose logging
./tcdd_server --verbose

# Or combine with other flags
./tcdd_server --verbose --file video.mp4
./tcdd_server --verbose --vulkan
```

By default (without `--verbose`), you'll only see:
- Startup messages
- Initialization status
- Real-time performance metrics (FPS, inference time, etc.)
- Critical errors

With `--verbose`, you'll additionally see:
- HTTP request details
- API endpoint calls
- Frame capture operations
- Detection pipeline events
- Data update notifications

## Log Categories

All log messages are prefixed with a category tag for easy filtering:

### `[HTTP]` - HTTP Server Operations
- **Client connections**: Shows client IP, port, and requested endpoint
- **Request routing**: Displays which endpoint is being accessed
- **MJPEG streaming**: Tracks video feed connections and frame counts
- **Response data**: Shows API responses (truncated for readability)
- **Disconnections**: Logs when clients disconnect

**Example:**
```
[HTTP] 192.168.1.100:52314 -> GET /video_feed HTTP/1.1
[HTTP] Starting MJPEG stream for 192.168.1.100
[HTTP] Streamed 100 frames to 192.168.1.100
[HTTP] Client 192.168.1.100 disconnected after 234 frames
```

### `[API]` - API Endpoint Handlers
- **Endpoint calls**: Logs when API handlers are invoked
- **Data state**: Shows if data is available or empty
- **Response content**: Displays JSON responses

**Example:**
```
[API] handleGetStatus called - Status: OK
[API] Status response: {"fps":29.5,"detections_count":2,...}
[API] handleGetDetections called - 3 detections
```

### `[SERVER]` - Server Data Updates
- **Frame updates**: Tracks frame buffer updates (every 100 frames)
- **Detection updates**: Logs when new detections are received
- **Status updates**: Tracks status object updates

**Example:**
```
[SERVER] Updated 100 frames (640x480)
[SERVER] Detection update #42: 2 objects
[SERVER] Status update #100
```

### `[CAMERA]` - Camera Operations
- **Frame capture**: Logs successful frame captures (every 100 frames)
- **Video looping**: Shows when video files loop back to start
- **Errors**: Reports capture failures, empty frames, or camera issues

**Example:**
```
[CAMERA] Captured frame #1 (640x480)
[CAMERA] Video file ended, looping back to start
[CAMERA] Error: Failed to read from camera
```

### `[DETECTOR]` - Object Detection
- **Detection runs**: Logs inference operations (every 100 frames or when objects detected)
- **Performance**: Shows inference time per frame
- **Warnings**: Reports initialization issues or inference errors

**Example:**
```
[DETECTOR] Frame #1: 3 detections in 45.2ms
[DETECTOR] Frame #101: 0 detections in 42.8ms
[DETECTOR] Warning: Inference extraction failed with code -1
```

### `[MAIN]` - Main Loop Operations
- **Frame processing**: Tracks main loop iterations
- **Frame drops**: Reports when frames fail to capture

**Example:**
```
[MAIN] Processing frame #1 (640x480)
[MAIN] Processing frame #101 (640x480)
```

## Common Scenarios

### Debugging /video_feed Issues

When `/video_feed` is loading indefinitely, look for these patterns:

1. **No HTTP requests logged**: Server not receiving requests
   ```
   # Should see:
   [HTTP] 192.168.1.100:52314 -> GET /video_feed HTTP/1.1
   ```

2. **Stream starts but no frames sent**: Camera not capturing
   ```
   [HTTP] Starting MJPEG stream for 192.168.1.100
   [HTTP] Warning: Empty frame, waiting...
   ```

3. **Frames captured but not sent**: Check camera logs
   ```
   [CAMERA] Error: Failed to read from camera
   ```

### Debugging /api/status Returning null

When `/api/status` returns null or empty, check:

1. **Status never initialized**: No status updates in logs
   ```
   # Should see:
   [SERVER] Status update #1
   ```

2. **Status object is empty**:
   ```
   [API] handleGetStatus called - Status: EMPTY
   [API] WARNING: currentStatus is empty, returning empty JSON object
   ```

3. **Main loop not running**: No frame processing logs
   ```
   # Should see:
   [MAIN] Processing frame #1 (640x480)
   ```

### Debugging Detection Issues

When detections aren't working:

1. **Detector not initialized**: Check startup logs
   ```
   ✓ Detector initialized successfully
   ✓ Loaded 80 class names
   ```

2. **Inference failing**:
   ```
   [DETECTOR] Warning: Inference extraction failed with code -1
   ```

3. **Detections never sent to server**:
   ```
   # Should see when objects detected:
   [SERVER] Detection update #42: 2 objects
   ```

## Performance Monitoring

The main loop prints real-time metrics:
```
FPS: 29.5 | Inference: 42.8ms | Detections: 2 | CPU: 45% | RAM: 512MB
```

Every 100 frames, you'll see update summaries:
```
[SERVER] Updated 100 frames (640x480)
[CAMERA] Captured frame #100 (640x480)
[DETECTOR] Frame #100: 0 detections in 43.1ms
```

## Filtering Logs

To filter specific log categories:

```bash
# Only HTTP requests
./tcdd_server | grep "\[HTTP\]"

# Only errors and warnings
./tcdd_server | grep -E "(Error|Warning)"

# Only API calls
./tcdd_server | grep "\[API\]"

# Save all logs to file
./tcdd_server 2>&1 | tee server.log
```

## Expected Startup Sequence

A successful startup **without --verbose** should show:

```
╔════════════════════════════════════════════════╗
║   TCDD C++ Server - Traffic Sign Detection     ║
║   Real-time Object Detection on Raspberry Pi   ║
╚════════════════════════════════════════════════╝

✓ Loaded configuration from: shared/config.json
✓ Logger initialized: logs/
Initializing camera: 640x480 @ 30 FPS
✓ Camera opened successfully
  Actual resolution: 640x480 @ 30 FPS
Initializing NCNN detector...
  Param: backend/model/model.ncnn.param
  Bin: backend/model/model.ncnn.bin
  Input size: 640x640
  Confidence: 0.500000
  NMS: 0.500000
  IoU: 0.500000
  Vulkan: disabled
✓ Detector initialized successfully
✓ Loaded 80 class names
Initializing HTTP server on port 5100
✓ HTTP server started on port 5100
✓ Server listening on port 5100

✓ All systems initialized successfully
✓ Server running on port 5100
✓ Press Ctrl+C to stop

FPS: 29.5 | Inference: 42.8ms | Detections: 2 | CPU: 45% | RAM: 512MB
```

With **--verbose**, you'll also see:

```
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
[DETECTOR] Frame #1: 0 detections in 45.2ms
[SERVER] Updated 1 frames (640x480)
[SERVER] Detection update #1: 0 objects
[SERVER] Status update #1
```

## Troubleshooting Common Issues

### No logs appearing
- Ensure stdout is not buffered: run with `unbuffer` or redirect to `tee`
- Check if program is actually running: `ps aux | grep tcdd_server`

### Too much output
- Reduce frequency of periodic logs by editing the modulo checks in code
- Filter output using grep
- Disable specific log categories by commenting out std::cout lines

### Logs show everything working but endpoint fails
- Check firewall: `sudo ufw status`
- Verify port is listening: `netstat -tlnp | grep 5100`
- Test with curl: `curl http://localhost:5100/health`

## Log File Location

CSV metrics logs are still written to the configured logging path (default: `logs/`):
```
logs/
  metrics_2025-10-17_14-30-45.csv
```

Console logs can be saved:
```bash
./tcdd_server 2>&1 | tee logs/console_$(date +%Y%m%d_%H%M%S).log
```
