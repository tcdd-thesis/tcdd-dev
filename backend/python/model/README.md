# Model Directory

This directory contains your trained YOLOv8 model for traffic sign detection.

## Required Files

- **`best.pt`** - Your custom trained YOLOv8 model (required for production)

**Note:** YOLOv8 models embed class names directly in the `.pt` file. The camera server uses `model.names` from the model file automatically. A `labels.txt` file is provided for documentation purposes only but is not used by the code.

## Quick Start: Add Your Trained Model

### Option 1: From Local Training

If you trained a model locally or on your development machine:

```bash
# On your development machine or Pi
cd /path/to/tcdd-dev/backend/python/model

# Copy your trained weights
cp /path/to/training/runs/detect/train/weights/best.pt ./best.pt
```

### Option 2: Download from Remote Training

If you trained on Google Colab, Kaggle, or another remote environment:

```bash
# Download from your training environment
scp user@remote:/path/to/best.pt ./best.pt

# Or use wget/curl if hosted
wget https://your-storage-url/best.pt -O best.pt
```

### Option 3: Transfer to Raspberry Pi

From your Windows/Mac/Linux machine to Pi:

**Windows (PowerShell):**
```powershell
scp C:\path\to\best.pt pi@raspberrypi.local:/home/pi/tcdd-dev/backend/python/model/best.pt
```

**Linux/Mac:**
```bash
scp /path/to/best.pt pi@raspberrypi.local:~/tcdd-dev/backend/python/model/best.pt
```

## Verify Your Model

Before deploying, verify that your model loads correctly and check its embedded class names:

```bash
cd /path/to/tcdd-dev/backend/python
source venv/bin/activate  # if using venv (Linux/Mac)
# or: .venv\Scripts\activate  # if using venv (Windows)

# Use the show_model_classes script
python scripts/show_model_classes.py model/best.pt
```

Expected output:
```
Loading model from: model/best.pt
✓ Model loaded successfully!

Model Classes (15 total):
  [0] Green Light
  [1] Red Light
  [2] Speed Limit 10
  ...
```

These embedded class names are automatically used by the camera server at runtime.

## Restart Services After Model Update

After updating your model or labels, restart the camera service:

```bash
# If using systemd (on Pi)
sudo systemctl restart sign-detection-camera
sudo journalctl -u sign-detection-camera -f

# If running manually
cd /path/to/tcdd-dev/backend/python
source venv/bin/activate
python camera_server.py
```

## Model Formats

### Supported Formats

| Format | File Extension | Performance | Recommended For |
|--------|---------------|-------------|-----------------|
| PyTorch | `.pt` | Best | Development, Pi 5 |
| ONNX | `.onnx` | Good | Edge devices |
| TensorFlow Lite | `.tflite` | Fast | Older Pi models |

### Convert Model (Optional)

For better performance on resource-constrained devices:

**Export to ONNX:**
```bash
cd /path/to/tcdd-dev/backend/python
source venv/bin/activate

python3 << EOF
from ultralytics import YOLO
model = YOLO('model/best.pt')
model.export(format='onnx')
EOF
```

**Export to TFLite:**
```bash
python3 << EOF
from ultralytics import YOLO
model = YOLO('model/best.pt')
model.export(format='tflite')
EOF
```

Update `camera_server.py` to use the exported model:
```python
# Change from:
model = YOLO('model/best.pt')

# To:
model = YOLO('model/best.onnx')  # or best.tflite
```

## Fallback Behavior

If `best.pt` is not found, the system will attempt to use a pretrained YOLOv8 model:

1. Tries `yolov8n.pt` (YOLOv8 nano)
2. Falls back to OpenCV detection (if available)
3. Returns an error if no model is available

**Note:** Pretrained models detect common objects (person, car, etc.) but are **not optimized for traffic signs**. Always use a custom trained model for production.

## Model Performance Tips

### For Raspberry Pi 5

- **Resolution:** 640x480 or 320x240 for best FPS
- **Model size:** YOLOv8n or YOLOv8s (nano/small)
- **FPS target:** 15-30 FPS
- **Confidence threshold:** 0.5-0.7

Edit `camera_server.py`:
```python
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CONFIDENCE_THRESHOLD = 0.5
```

### Memory Usage

| Model | Parameters | Size | RAM Usage | Pi 5 FPS (640x480) |
|-------|-----------|------|-----------|-------------------|
| YOLOv8n | 3.2M | ~6 MB | ~200 MB | 25-30 |
| YOLOv8s | 11.2M | ~22 MB | ~400 MB | 15-20 |
| YOLOv8m | 25.9M | ~50 MB | ~800 MB | 8-12 |

## Troubleshooting

### Model Won't Load

```bash
# Check if file exists
ls -lh /path/to/tcdd-dev/backend/python/model/best.pt

# Check file size (should be > 1MB)
du -h model/best.pt

# Verify it's a valid PyTorch file
file model/best.pt
# Should output: "model/best.pt: data"
```

### Wrong Number of Classes

If you see errors like `RuntimeError: expected 80 classes, got 15`:

1. Verify you're using the correct model file for this project
2. Check that you're not mixing models from different training runs
3. Use the verification script to confirm class count:
   ```bash
   python scripts/show_model_classes.py model/best.pt
   ```

### Low Detection Accuracy

- Verify model classes using `python scripts/show_model_classes.py model/best.pt`
- Check camera focus and lighting
- Adjust confidence threshold in `shared/config.json`
- Consider retraining with more data
- Try different image augmentation during training

### Service Won't Start After Model Update

```bash
# Check logs
sudo journalctl -u sign-detection-camera -n 50 --no-pager

# Test manually
cd /path/to/tcdd-dev/backend/python
source venv/bin/activate
python camera_server.py

# Common fixes:
# 1. Check file permissions
chmod 644 model/best.pt

# 2. Verify model path in shared/config.json
cat ../../shared/config.json | grep modelPath

# 3. Ensure venv has ultralytics installed
pip list | grep ultralytics

# 4. Verify model classes
python scripts/show_model_classes.py model/best.pt
```

## Model Versioning (Recommended)

Keep track of model versions for easy rollback:

```bash
cd /path/to/tcdd-dev/backend/python/model

# Backup current model
cp best.pt best_v1.pt

# Add new model
cp /path/to/new_training/best.pt best.pt

# If new model has issues, rollback:
cp best_v1.pt best.pt
sudo systemctl restart sign-detection-camera
```

## Training Resources

For training your own traffic sign detection model:

- **Dataset preparation:** Roboflow, CVAT, LabelImg
- **Training platforms:** Google Colab, Kaggle, local GPU
- **YOLOv8 docs:** https://docs.ultralytics.com/
- **Transfer learning:** Start with YOLOv8n pretrained weights

## Support

If you encounter issues:

1. Check [PI_SETUP.md](../../../PI_SETUP.md) for common fixes
2. Review logs: `sudo journalctl -u sign-detection-camera -f`
3. Test model manually with the verification script above
4. Ensure camera is working: `libcamera-hello`

```
