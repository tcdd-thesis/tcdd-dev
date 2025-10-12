# Model Directory

Place your trained YOLOv8 model file here.

## Expected Files

- `best.pt` - Your custom trained YOLOv8 model (recommended)
- `labels.txt` - Class labels (one per line)

## Using Your Trained Model

If you trained a model using the scripts in the parent `tcdd-ml-train` directory:

1. Copy your trained model to this directory:
   ```bash
   cp ../../runs/detect/train/weights/best.pt ./best.pt
   ```

2. Update `labels.txt` with your class names:
   ```
   stop
   yield
   speed_limit_30
   speed_limit_50
   no_entry
   # ... add your classes
   ```

## Fallback Behavior

If `best.pt` is not found, the system will use the pretrained YOLOv8n model (`yolov8n.pt`) which can detect common objects but may not be optimized for traffic signs.

## Model Format

- Supported: PyTorch (.pt), ONNX (.onnx), TensorFlow Lite (.tflite)
- Recommended: PyTorch (.pt) for best performance on Raspberry Pi 5

## Testing Your Model

Test your model before deploying:

```bash
cd backend/python
python3 -c "
from ultralytics import YOLO
model = YOLO('model/best.pt')
results = model('test_image.jpg')
print('Model loaded successfully!')
print('Classes:', model.names)
"
```
