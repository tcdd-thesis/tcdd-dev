# Model Directory

This directory contains the NCNN model files for traffic sign detection.

## Required Files

- `model.ncnn.param` - NCNN parameter file
- `model.ncnn.bin` - NCNN binary/weight file
- `labels.txt` - Class names (one per line)

## Model Conversion

Convert your YOLOv8 model to NCNN format:

### Step 1: Export to ONNX

```bash
# Using Ultralytics
python -c "from ultralytics import YOLO; model = YOLO('path/to/your-model.pt'); model.export(format='onnx')"
```

### Step 2: Convert ONNX to NCNN

```bash
# Install NCNN tools
# https://github.com/Tencent/ncnn

# Convert
onnx2ncnn your-model.onnx model.param model.bin

# Optimize (optional but recommended)
ncnnoptimize model.param model.bin model.ncnn.param model.ncnn.bin 0
```

### Step 3: Place Files

```bash
cp model.ncnn.param backend/model/
cp model.ncnn.bin backend/model/
```

## Class Names

Create a `labels.txt` file with your class names:

```
stop_sign
yield_sign
speed_limit_30
speed_limit_50
...
```

Each line represents one class (index matches model output).

## Model Configuration

Update `shared/config.json`:

```json
{
  "detection": {
    "modelFormat": "ncnn",
    "modelPath": [
      "backend/model/model.ncnn.param",
      "backend/model/model.ncnn.bin"
    ],
    "inputSize": [640, 480],
    "confidenceThreshold": 0.5
  }
}
```

## Notes

- Model files are ignored by git (too large)
- Keep originals backed up separately
- Test model compatibility before deployment
- Ensure input/output layer names match code expectations (default: "in0"/"out0")
