# Standalone Model Inference Tool

This tool is a desktop GUI for benchmarking model inference performance.

It supports:

- Model formats: `.pt`, `.pth`, `.onnx`, `.hef`
- Input types: single image, dataset folder, camera stream
- Platforms: Windows and Raspberry Pi
- RPi reuse path: uses existing `backend/detector.py` implementation for `.pt/.pth/.hef`

## File

- `backend/model_inference_tool.py`

## Install

Use your current environment or create one, then install:

```bash
pip install -r backend/inference_tool.requirements.txt
```

Notes:

- For HEF models on Raspberry Pi, ensure your Hailo runtime is installed and available.
- For Raspberry Pi camera module, install `picamera2` and camera stack dependencies.
- YOLO report mode requires `pyyaml` (for `data.yaml`) and `matplotlib` (for plot generation).

## Run

From repository root:

```bash
python backend/model_inference_tool.py
```

## GUI Workflow

1. Select a model (`.pt`, `.pth`, `.onnx`, `.hef`)
2. Optionally set confidence/IOU and labels path
3. Click **Load Model**
4. Choose mode:
   - Single Image: select one image and run N iterations
   - Dataset: select a folder (recursive scan for images)
   - Camera Stream: choose camera index (`0`, `1`, etc.) or `rpi_camera`
5. Click **Start**
6. Watch live logs, preview, and statistics

## YOLO Dataset Evaluation Mode

If the selected dataset folder contains `data.yaml` (or `dataset.yaml`), dataset mode automatically switches to YOLO evaluation report generation.

Expected layout:

- Dataset root with `data.yaml`
- Split folders/files referenced by `train`, `val`/`valid`, `test`
- YOLO labels in matching `labels/.../*.txt` paths

Available split selector in GUI:

- `train`, `val`, `test`, `all`

Generated report artifacts are saved under `data/logs/inference_reports/<timestamp>/`:

- `metrics_summary.json`
- `pr_curve.png`
- `f1_conf_curve.png`
- `p_conf_curve.png`
- `r_conf_curve.png`
- `confusion_matrix.png`

Report metrics include:

- Precision, Recall, F1 (best confidence threshold)
- mAP@0.50 (`map50`)
- mAP@0.50:0.95 (`map50_95`)
- Per-class AP@0.50
- Confusion matrix (row-normalized)
- Inference latency/FPS statistics

## Metrics

The app reports:

- Average latency (ms)
- Min/Max latency
- Percentiles: p50, p90, p95, p99
- Std deviation
- Effective FPS
- Average detections per frame (for detector backends)

## Backend Selection Rules

- `.pt` / `.pth`: existing detector backend (`ultralytics` path)
- `.hef`: existing detector backend (`hef` + Hailo path)
- `.onnx`: ONNX Runtime backend

## Camera Support

- Windows: OpenCV camera capture (webcam/USB)
- Raspberry Pi:
  - `rpi_camera` source uses `picamera2`
  - Numeric indices use OpenCV camera capture

## Current Limitations

- ONNX backend is generic performance-focused inference. It does not parse detections for drawing boxes unless model-specific post-processing is added.
- HEF models require Hailo runtime and accelerator.
