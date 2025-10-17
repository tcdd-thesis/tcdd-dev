# --no-ml Flag Implementation

## Overview
Added `--no-ml` command-line flag to disable ML object detection for troubleshooting purposes.

## Purpose
Allows running the camera feed without loading or executing the NCNN model, useful for:
- Isolating camera vs detection issues
- Testing camera feed performance without ML overhead
- Debugging false positive detection problems

## Usage
```bash
./tcdd --no-ml
```

## Implementation Details

### Command-line Parsing (main.cpp)
- Added `bool disableML = false;` variable
- Added `--no-ml` flag parsing in argument loop
- Updated `printUsage()` to document the flag

### Detector Initialization
- Wrapped detector initialization in `if (mlEnabled)` check
- Shows warning message when ML is disabled: "⚠ ML Detection DISABLED (--no-ml flag set)"
- Skips loading model files and class names when flag is set

### Main Processing Loop
- Detection calls wrapped in `if (mlEnabled)` check
- When disabled:
  - No `detector.detect()` call
  - Empty detections array
  - Zero inference time in metrics
  - No detection drawing on frames
- When enabled:
  - Normal detection pipeline runs

### Metrics Impact
When `--no-ml` is active:
- `inference_time_ms` = 0.0
- `detections_count` = 0
- `total_detections` = 0

## Testing
To test camera feed without ML detection:
```bash
cd backend/cpp
./build.sh
./tcdd --no-ml
```

Access the feed at: `http://<raspberry-pi-ip>:8080/mjpeg`

## Related Files
- `main.cpp` - Flag parsing and conditional ML execution
- `detector.cpp` - Detection implementation (unchanged)
- `README.md` - User documentation
- `QUICKREF.md` - Quick reference guide

## Next Steps for Debugging
1. Run with `--no-ml` to verify camera feed is clean
2. If feed is clean, issue is in model/detection logic
3. If feed still has issues, problem is in camera/preprocessing
4. Investigate confidence/NMS thresholds in config.json if model issue
