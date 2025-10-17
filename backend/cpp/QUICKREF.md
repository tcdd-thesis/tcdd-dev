# C++ Server Quick Reference

## Build & Run

```bash
# First time setup
cd backend/cpp
chmod +x build.sh download_deps.sh
./build.sh

# Run server (normal mode)
cd ../..
./backend/cpp_server

# Run with verbose logging (for debugging)
./backend/cpp_server --verbose

# With options
./backend/cpp_server --vulkan           # Enable Vulkan
./backend/cpp_server --file video.mp4   # Use video file
./backend/cpp_server --verbose --vulkan # Combine flags
./backend/cpp_server --help             # Show help
```

## File Locations

```
backend/
├── cpp_server              ← Executable (after build)
├── cpp/                    ← Source code
│   ├── build/              ← Build artifacts
│   └── third_party/        ← Dependencies
└── model/                  ← Model files
    ├── model.ncnn.param
    ├── model.ncnn.bin
    └── labels.txt

shared/
└── config.json             ← Configuration

logs/
└── performance_*.csv       ← Performance logs (per session)
```

## Configuration

**Important:** The server requires a valid `shared/config.json` file to run. It will not start without it.

Edit `shared/config.json`:

```json
{
  "cppServerPort": 5100,
  "camera": {"width": 640, "height": 480, "fps": 30},
  "detection": {
    "modelPath": ["backend/model/model.ncnn.param", "backend/model/model.ncnn.bin"],
    "confidenceThreshold": 0.5,
    "inputSize": [640, 480]
  },
  "performance": {"useVulkan": false},
  "logging": {"path": "logs/", "metricsInterval": 1000}
}
```

## API Endpoints

| Endpoint | Response |
|----------|----------|
| `http://localhost:5100/video_feed` | MJPEG stream |
| `http://localhost:5100/api/status` | System status JSON |
| `http://localhost:5100/api/detections` | Detections JSON |
| `http://localhost:5100/health` | Health check JSON |

## Test Commands

```bash
# Health check
curl http://localhost:5100/health

# Get status
curl http://localhost:5100/api/status | jq

# Get detections
curl http://localhost:5100/api/detections | jq

# View stream (browser)
xdg-open http://localhost:5100/video_feed
```

## Model Conversion

```bash
# 1. Export ONNX
python -c "from ultralytics import YOLO; YOLO('model.pt').export(format='onnx')"

# 2. Convert to NCNN
onnx2ncnn model.onnx temp.param temp.bin

# 3. Optimize
ncnnoptimize temp.param temp.bin model.ncnn.param model.ncnn.bin 0

# 4. Copy to project
cp model.ncnn.* backend/model/
```

## Performance Tuning

### Fast (low quality)
```json
{"camera": {"width": 320, "height": 240, "fps": 15}}
```

### Balanced (recommended)
```json
{"camera": {"width": 640, "height": 480, "fps": 30}}
```

### Quality (slow)
```json
{"camera": {"width": 1280, "height": 720, "fps": 15}}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Camera not found | `sudo raspi-config` → Enable camera |
| NCNN not found | Install from source (see SETUP.md) |
| Low FPS | Enable Vulkan or reduce resolution |
| Build errors | Check dependencies: `pkg-config --modversion opencv4` |
| Port in use | Change `cppServerPort` in config |

## Systemd Service

Create `/etc/systemd/system/tcdd-cpp.service`:
```ini
[Unit]
Description=TCDD C++ Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tcdd-dev
ExecStart=/home/pi/tcdd-dev/backend/cpp_server
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable tcdd-cpp
sudo systemctl start tcdd-cpp
sudo systemctl status tcdd-cpp
```

## Logs

View performance logs:
```bash
# Latest log
ls -lt logs/ | head -n 1

# View log
cat logs/performance_YYYYMMDD_HHMMSS.csv

# Tail log
tail -f logs/performance_YYYYMMDD_HHMMSS.csv

# Analyze with Python
python -c "import pandas as pd; df=pd.read_csv('logs/performance_*.csv'); print(df.describe())"
```

## Common Tasks

### Restart Server
```bash
sudo systemctl restart tcdd-cpp
```

### View Logs
```bash
journalctl -u tcdd-cpp -f
```

### Check Camera
```bash
libcamera-hello --list-cameras
v4l2-ctl --list-devices
```

### Monitor Performance
```bash
htop
```

### Check Vulkan
```bash
vulkaninfo | grep deviceName
```

## Development

### Rebuild
```bash
cd backend/cpp/build
make -j$(nproc)
```

### Clean Build
```bash
cd backend/cpp
rm -rf build
./build.sh
```

### Debug Build
```bash
cd backend/cpp/build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)
```

## Key Files

- **main.cpp** - Entry point
- **detector.cpp** - Inference logic
- **http_server.cpp** - API endpoints
- **logger.cpp** - Metrics logging
- **config_loader.cpp** - Config parsing

## Environment Variables

None currently used. All config in `shared/config.json`.

## Dependencies

- **OpenCV** >= 4.0
- **NCNN** (latest)
- **CMake** >= 3.10
- **C++17** compiler

## Port Usage

- **5000** - Node.js backend
- **5100** - C++ server (configurable)
- **3000** - React frontend

## Performance Targets

On Raspberry Pi 5:
- **FPS**: 25-30 (CPU), 35-45 (Vulkan)
- **Inference**: 30-50ms (CPU), 15-25ms (Vulkan)
- **Latency**: <100ms

## Resources

- Full setup: `backend/cpp/SETUP.md`
- Usage guide: `backend/cpp/README.md`
- Implementation details: `backend/cpp/IMPLEMENTATION_SUMMARY.md`
