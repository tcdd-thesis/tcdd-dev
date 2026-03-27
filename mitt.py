#!/usr/bin/env python3
"""
Model Inference Testing Tool (MITT)
Standalone model inference GUI tool for performance testing.

Supported model formats:
- PyTorch/Ultralytics (.pt, .pth) via existing Detector backend
- HEF (.hef) via existing Detector + Hailo path
- ONNX (.onnx) via onnxruntime

Input modes:
- Single image
- Video file
- Dataset folder (recursive image scan)
- Camera stream (Windows webcams/USB, Raspberry Pi camera module)
"""

from __future__ import annotations

import os
import time
import queue
import json
import threading
import platform
import urllib.request
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

try:
    from PIL import Image, ImageTk
except ImportError as exc:
    raise RuntimeError("Pillow is required for preview rendering. Install pillow.") from exc

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_TKDND = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    HAS_TKDND = False

# Reuse the existing RPi-ready detector implementation
try:
    from backend.detector import Detector, HAS_HAILO, HAS_YOLO
except ImportError:
    Detector = None
    HAS_HAILO = False
    HAS_YOLO = False

try:
    import onnxruntime as ort
except ImportError:
    ort = None

try:
    import yaml
except ImportError:
    yaml = None

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

try:
    import psutil
except ImportError:
    psutil = None

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".avi", ".mp4", ".mkv", ".mov", ".wmv", ".m4v", ".webm", ".flv", ".mpeg", ".mpg"}
MODEL_EXTENSIONS = {".pt", ".pth", ".onnx", ".hef"}


class DictConfig:
    """Tiny dot-notation config adapter for Detector compatibility."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node


@dataclass
class InferenceResult:
    latency_ms: float
    detections: int
    output_summary: str
    annotated_frame: Optional[np.ndarray]
    predictions: Optional[List[Dict[str, Any]]] = None


class BaseBackend:
    name = "base"

    def infer(self, frame_bgr: np.ndarray) -> InferenceResult:
        raise NotImplementedError

    def get_model_info(self) -> Dict[str, Any]:
        return {"backend": self.name}

    def close(self) -> None:
        return None


class DetectorBackend(BaseBackend):
    """Wrap the existing Detector class for .pt/.pth and .hef models."""

    name = "detector"

    def __init__(
        self,
        model_path: str,
        confidence: float,
        iou: float,
        labels_path: str,
        use_hailo_for_hef: bool,
        device: str,
    ):
        if Detector is None:
            raise RuntimeError("Unable to import Detector from backend/detector.py")

        suffix = Path(model_path).suffix.lower()
        if suffix == ".hef":
            if not use_hailo_for_hef:
                raise RuntimeError("HEF model selected but Hailo option is disabled.")
            if not HAS_HAILO:
                raise RuntimeError("hailo_platform is not available in this environment.")
            engine = "hef"
            detection_device = "hailo"
        else:
            if not HAS_YOLO:
                raise RuntimeError("ultralytics is not available in this environment.")
            engine = "ultralytics"
            detection_device = device

        config_dict: Dict[str, Any] = {
            "detection": {
                "engine": engine,
                "device": detection_device,
                "model_files": [model_path],
                "labels": labels_path,
                "confidence": confidence,
                "iou_threshold": iou,
            }
        }
        self.model_path = model_path
        self._detector = Detector(DictConfig(config_dict))

        if not self._detector.is_loaded():
            raise RuntimeError("Detector backend did not load the model successfully.")

    def infer(self, frame_bgr: np.ndarray) -> InferenceResult:
        start = time.perf_counter()
        detections = self._detector.detect(frame_bgr)
        latency_ms = (time.perf_counter() - start) * 1000.0

        count = len(detections) if isinstance(detections, list) else 0
        annotated = self._detector.draw_detections(frame_bgr, detections) if count else frame_bgr.copy()
        summary = f"detections={count}"

        return InferenceResult(
            latency_ms=latency_ms,
            detections=count,
            output_summary=summary,
            annotated_frame=annotated,
            predictions=detections if isinstance(detections, list) else [],
        )

    def get_model_info(self) -> Dict[str, Any]:
        info = self._detector.get_info()
        info["backend"] = self.name
        return info

    def close(self) -> None:
        if hasattr(self._detector, "_cleanup_hailo"):
            try:
                self._detector._cleanup_hailo()
            except Exception:
                pass


class OnnxBackend(BaseBackend):
    """Generic ONNX Runtime backend for performance testing."""

    name = "onnxruntime"

    _DTYPE_MAP = {
        "tensor(float)": np.float32,
        "tensor(float16)": np.float16,
        "tensor(double)": np.float64,
        "tensor(int64)": np.int64,
        "tensor(int32)": np.int32,
        "tensor(uint8)": np.uint8,
        "tensor(int8)": np.int8,
    }

    def __init__(
        self,
        model_path: str,
        prefer_gpu: bool,
        confidence: float,
        iou: float,
        labels_path: str,
    ):
        if ort is None:
            raise RuntimeError("onnxruntime is not installed in this environment.")

        requested = ["CPUExecutionProvider"]
        if prefer_gpu:
            requested = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        available = set(ort.get_available_providers())
        providers = [p for p in requested if p in available]
        if not providers:
            providers = ["CPUExecutionProvider"]

        self.model_path = model_path
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_meta = self.session.get_inputs()[0]
        self.input_name = self.input_meta.name
        self.input_shape = list(self.input_meta.shape)
        self.input_type = self.input_meta.type
        self.channels_last = self._is_channels_last(self.input_shape)
        self.height, self.width = self._resolve_hw(self.input_shape)
        self.confidence = confidence
        self.iou_threshold = iou
        self.labels_path = labels_path
        self.class_names = self._load_labels(labels_path)
        self.input_frame_color_space = "BGR"

    @staticmethod
    def _load_labels(labels_path: str) -> List[str]:
        if not labels_path or not os.path.exists(labels_path):
            return []
        names: List[str] = []
        with open(labels_path, "r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if text:
                    names.append(text)
        return names

    @staticmethod
    def _resolve_dim(raw: Any, fallback: int) -> int:
        if isinstance(raw, int) and raw > 0:
            return raw
        return fallback

    def _is_channels_last(self, shape: Sequence[Any]) -> bool:
        if len(shape) != 4:
            return False
        if shape[-1] in (1, 3):
            return True
        if shape[1] in (1, 3):
            return False
        return False

    def _resolve_hw(self, shape: Sequence[Any]) -> Tuple[int, int]:
        if len(shape) == 4:
            if shape[1] in (1, 3):  # NCHW
                return self._resolve_dim(shape[2], 640), self._resolve_dim(shape[3], 640)
            if shape[-1] in (1, 3):  # NHWC
                return self._resolve_dim(shape[1], 640), self._resolve_dim(shape[2], 640)
        return 640, 640

    def _preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        input_dtype = self._DTYPE_MAP.get(self.input_type, np.float32)
        resized = cv2.resize(frame_bgr, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        if str(self.input_frame_color_space).upper() == "RGB":
            rgb = resized
        else:
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        if input_dtype == np.uint8:
            arr = rgb
        else:
            arr = rgb.astype(np.float32) / 255.0

        if len(self.input_shape) == 4 and not self.channels_last:
            arr = np.transpose(arr, (2, 0, 1))

        if len(self.input_shape) == 4:
            arr = np.expand_dims(arr, axis=0)

        return arr.astype(input_dtype, copy=False)

    @staticmethod
    def _summarize_outputs(outputs: Sequence[Any]) -> str:
        parts: List[str] = []
        for idx, out in enumerate(outputs):
            if isinstance(out, np.ndarray):
                parts.append(f"out{idx}: shape={tuple(out.shape)} dtype={out.dtype}")
            else:
                parts.append(f"out{idx}: type={type(out).__name__}")
            if idx >= 2:
                break
        return " | ".join(parts)

    def _class_name(self, cls_id: int) -> str:
        if 0 <= cls_id < len(self.class_names):
            return self.class_names[cls_id]
        return f"class_{cls_id}"

    @staticmethod
    def _box_iou_xyxy(box_a: Sequence[float], box_b: Sequence[float]) -> float:
        inter_x1 = max(float(box_a[0]), float(box_b[0]))
        inter_y1 = max(float(box_a[1]), float(box_b[1]))
        inter_x2 = min(float(box_a[2]), float(box_b[2]))
        inter_y2 = min(float(box_a[3]), float(box_b[3]))

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0.0, float(box_a[2]) - float(box_a[0])) * max(0.0, float(box_a[3]) - float(box_a[1]))
        area_b = max(0.0, float(box_b[2]) - float(box_b[0])) * max(0.0, float(box_b[3]) - float(box_b[1]))

        union = area_a + area_b - inter_area
        if union <= 0.0:
            return 0.0
        return inter_area / union

    def _input_to_frame_box(
        self,
        box_xyxy: Sequence[float],
        frame_w: int,
        frame_h: int,
    ) -> List[int]:
        x1, y1, x2, y2 = [float(v) for v in box_xyxy]
        if max(abs(x1), abs(y1), abs(x2), abs(y2)) <= 2.5:
            x1 *= self.width
            y1 *= self.height
            x2 *= self.width
            y2 *= self.height

        sx = frame_w / max(float(self.width), 1.0)
        sy = frame_h / max(float(self.height), 1.0)
        x1 *= sx
        x2 *= sx
        y1 *= sy
        y2 *= sy

        x1 = max(0.0, min(frame_w - 1.0, x1))
        x2 = max(0.0, min(frame_w - 1.0, x2))
        y1 = max(0.0, min(frame_h - 1.0, y1))
        y2 = max(0.0, min(frame_h - 1.0, y2))

        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        return [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))]

    def _decode_xyxy_rows(
        self,
        rows: np.ndarray,
        frame_w: int,
        frame_h: int,
    ) -> List[Dict[str, Any]]:
        if rows.ndim != 2 or rows.shape[1] < 6:
            return []

        decoded: List[Dict[str, Any]] = []
        for row in rows:
            vals = np.asarray(row, dtype=np.float32)
            conf = float(vals[4])
            if conf < self.confidence:
                continue

            cls_id = int(round(float(vals[5])))
            x1, y1, x2, y2 = [float(v) for v in vals[:4]]

            # Some exports may still output xywh in first four slots.
            if x2 <= x1 or y2 <= y1:
                cx, cy, bw, bh = x1, y1, x2, y2
                if max(abs(cx), abs(cy), abs(bw), abs(bh)) <= 2.5:
                    cx *= self.width
                    cy *= self.height
                    bw *= self.width
                    bh *= self.height
                x1 = cx - bw / 2.0
                y1 = cy - bh / 2.0
                x2 = cx + bw / 2.0
                y2 = cy + bh / 2.0

            box = self._input_to_frame_box([x1, y1, x2, y2], frame_w, frame_h)
            if box[2] <= box[0] or box[3] <= box[1]:
                continue

            decoded.append(
                {
                    "cls": cls_id,
                    "class_name": self._class_name(cls_id),
                    "confidence": conf,
                    "bbox": box,
                }
            )

        return decoded

    def _decode_dense_yolo(
        self,
        rows: np.ndarray,
        frame_w: int,
        frame_h: int,
    ) -> List[Dict[str, Any]]:
        if rows.ndim != 2 or rows.shape[1] < 6:
            return []

        attrs = rows.shape[1]
        labels_count = len(self.class_names)

        modes: List[bool] = []
        if labels_count > 0:
            if attrs == labels_count + 4:
                modes = [False]
            elif attrs == labels_count + 5:
                modes = [True]

        if not modes:
            if attrs == 84:
                modes = [False]
            elif attrs == 85:
                modes = [True]
            elif attrs > 6:
                # Unknown head layout: try both hypotheses and choose best.
                modes = [False, True]

        candidates_per_mode: List[List[Dict[str, Any]]] = []
        for has_objectness in modes:
            cls_start = 5 if has_objectness else 4
            if attrs <= cls_start:
                continue

            mode_preds: List[Dict[str, Any]] = []
            for row in rows:
                vals = np.asarray(row, dtype=np.float32)
                cx, cy, bw, bh = [float(v) for v in vals[:4]]
                cls_scores = vals[cls_start:]
                if cls_scores.size == 0:
                    continue

                cls_rel_idx = int(np.argmax(cls_scores))
                cls_score = float(cls_scores[cls_rel_idx])
                if has_objectness:
                    conf = float(vals[4]) * cls_score
                else:
                    conf = cls_score

                if conf < self.confidence:
                    continue

                if max(abs(cx), abs(cy), abs(bw), abs(bh)) <= 2.5:
                    cx *= self.width
                    cy *= self.height
                    bw *= self.width
                    bh *= self.height

                x1 = cx - bw / 2.0
                y1 = cy - bh / 2.0
                x2 = cx + bw / 2.0
                y2 = cy + bh / 2.0
                box = self._input_to_frame_box([x1, y1, x2, y2], frame_w, frame_h)
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue

                cls_id = cls_rel_idx
                mode_preds.append(
                    {
                        "cls": cls_id,
                        "class_name": self._class_name(cls_id),
                        "confidence": conf,
                        "bbox": box,
                    }
                )

            candidates_per_mode.append(mode_preds)

        if not candidates_per_mode:
            return []

        # Prefer mode with more valid detections; tie-break by mean confidence.
        candidates_per_mode.sort(
            key=lambda dets: (len(dets), float(np.mean([d["confidence"] for d in dets])) if dets else 0.0),
            reverse=True,
        )
        return candidates_per_mode[0]

    def _decode_output_array(
        self,
        output: np.ndarray,
        frame_w: int,
        frame_h: int,
    ) -> List[Dict[str, Any]]:
        arr = np.asarray(output)
        if not np.issubdtype(arr.dtype, np.number) or arr.size == 0:
            return []

        # Drop batch dimensions when batch=1.
        while arr.ndim > 2 and arr.shape[0] == 1:
            arr = arr[0]

        # Candidate layout A: direct Nx6/Nx7 rows after NMS.
        direct_rows: Optional[np.ndarray] = None
        if arr.ndim == 2 and arr.shape[1] >= 6:
            direct_rows = arr

        # Candidate layout B: dense YOLO head (N x attrs). Handle transposed case.
        dense_rows: Optional[np.ndarray] = None
        if arr.ndim == 2:
            if arr.shape[1] >= 6:
                dense_rows = arr
            elif arr.shape[0] >= 6:
                dense_rows = arr.T

        direct = self._decode_xyxy_rows(direct_rows, frame_w, frame_h) if direct_rows is not None else []
        dense = self._decode_dense_yolo(dense_rows, frame_w, frame_h) if dense_rows is not None else []

        if len(dense) > len(direct):
            return dense
        return direct

    def _nms(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not detections:
            return []

        by_class: Dict[int, List[Dict[str, Any]]] = {}
        for det in detections:
            cls_id = int(det.get("cls", -1))
            by_class.setdefault(cls_id, []).append(det)

        kept: List[Dict[str, Any]] = []
        for cls_dets in by_class.values():
            ordered = sorted(cls_dets, key=lambda item: float(item["confidence"]), reverse=True)
            selected: List[Dict[str, Any]] = []
            for cand in ordered:
                overlap = False
                for prev in selected:
                    iou = self._box_iou_xyxy(cand["bbox"], prev["bbox"])
                    if iou > self.iou_threshold:
                        overlap = True
                        break
                if not overlap:
                    selected.append(cand)
            kept.extend(selected)

        return kept

    def _draw_detections(self, frame_bgr: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        if not detections:
            return frame_bgr.copy()

        annotated = frame_bgr.copy()
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
            conf = float(det["confidence"])
            label = f"{det['class_name']} {conf:.2f}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 220, 0), 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(
                annotated,
                (x1, max(0, y1 - th - 6)),
                (x1 + tw + 6, y1),
                (0, 220, 0),
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x1 + 3, max(10, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        return annotated

    def _parse_predictions(
        self,
        outputs: Sequence[Any],
        frame_w: int,
        frame_h: int,
    ) -> List[Dict[str, Any]]:
        all_candidates: List[List[Dict[str, Any]]] = []
        for out in outputs:
            if isinstance(out, np.ndarray):
                parsed = self._decode_output_array(out, frame_w, frame_h)
                if parsed:
                    all_candidates.append(parsed)

        if not all_candidates:
            return []

        # Choose output branch with most usable detections and apply NMS.
        all_candidates.sort(key=len, reverse=True)
        return self._nms(all_candidates[0])

    def infer(self, frame_bgr: np.ndarray) -> InferenceResult:
        frame_h, frame_w = frame_bgr.shape[:2]
        model_input = self._preprocess(frame_bgr)
        start = time.perf_counter()
        outputs = self.session.run(None, {self.input_name: model_input})
        latency_ms = (time.perf_counter() - start) * 1000.0

        predictions = self._parse_predictions(outputs, frame_w=frame_w, frame_h=frame_h)
        annotated = self._draw_detections(frame_bgr, predictions)
        summary = f"detections={len(predictions)} | {self._summarize_outputs(outputs)}"

        return InferenceResult(
            latency_ms=latency_ms,
            detections=len(predictions),
            output_summary=summary,
            annotated_frame=annotated,
            predictions=predictions,
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "backend": self.name,
            "model": self.model_path,
            "providers": self.session.get_providers(),
            "input_name": self.input_name,
            "input_shape": self.input_shape,
            "input_type": self.input_type,
            "layout": "NHWC" if self.channels_last else "NCHW",
            "resolved_hw": [self.height, self.width],
            "classes": self.class_names,
            "confidence": self.confidence,
            "iou_threshold": self.iou_threshold,
        }


class OpenCVCapture:
    def __init__(self, index: int, width: int, height: int, fps: int):
        api = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_V4L2
        self.cap = cv2.VideoCapture(index, api)
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open camera index {index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        for _ in range(4):
            self.cap.read()

    def read(self) -> Optional[np.ndarray]:
        ok, frame = self.cap.read()
        if not ok:
            return None
        return frame

    def release(self) -> None:
        self.cap.release()


class PiCamera2Capture:
    def __init__(self, width: int, height: int, fps: int):
        if Picamera2 is None:
            raise RuntimeError("picamera2 is not installed.")

        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": (width, height), "format": "RGB888"},
            buffer_count=4,
        )
        self.camera.configure(config)

        frame_duration_us = int(1_000_000 / max(fps, 1))
        self.camera.set_controls(
            {
                "AwbEnable": True,
                "AwbMode": 0,
                "FrameDurationLimits": (frame_duration_us, frame_duration_us),
            }
        )
        self.camera.start()
        time.sleep(1.0)

    def read(self) -> Optional[np.ndarray]:
        rgb = self.camera.capture_array()
        if rgb is None:
            return None
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def release(self) -> None:
        try:
            self.camera.stop()
        finally:
            self.camera.close()


def compute_stats(samples_ms: Sequence[float]) -> Dict[str, float]:
    if not samples_ms:
        return {}

    arr = np.asarray(samples_ms, dtype=np.float64)
    mean_ms = float(arr.mean())
    fps = (1000.0 / mean_ms) if mean_ms > 0 else 0.0

    return {
        "count": float(arr.size),
        "avg_ms": mean_ms,
        "min_ms": float(arr.min()),
        "max_ms": float(arr.max()),
        "std_ms": float(arr.std()),
        "p50_ms": float(np.percentile(arr, 50)),
        "p90_ms": float(np.percentile(arr, 90)),
        "p95_ms": float(np.percentile(arr, 95)),
        "p99_ms": float(np.percentile(arr, 99)),
        "fps": fps,
    }


def discover_images(folder: str) -> List[str]:
    root = Path(folder)
    files: List[str] = []
    for ext in IMAGE_EXTENSIONS:
        files.extend(str(p) for p in root.rglob(f"*{ext}"))
        files.extend(str(p) for p in root.rglob(f"*{ext.upper()}"))
    files.sort()
    return files


def normalize_class_name(name: str) -> str:
    return "".join(ch for ch in name.lower().strip() if ch.isalnum())


def parse_yolo_names(raw_names: Any) -> List[str]:
    if isinstance(raw_names, list):
        return [str(item) for item in raw_names]
    if isinstance(raw_names, dict):
        parsed: Dict[int, str] = {}
        for key, value in raw_names.items():
            try:
                parsed[int(key)] = str(value)
            except Exception:
                continue
        if parsed:
            return [parsed[idx] for idx in sorted(parsed.keys())]
    return []


def resolve_dataset_entry(root: Path, entry: Any) -> List[str]:
    if entry is None:
        return []

    if isinstance(entry, (list, tuple)):
        out: List[str] = []
        for item in entry:
            out.extend(resolve_dataset_entry(root, item))
        return out

    if not isinstance(entry, str):
        return []

    target = Path(entry)
    if not target.is_absolute():
        target = root / target

    if target.is_dir():
        return discover_images(str(target))

    if target.is_file():
        if target.suffix.lower() == ".txt":
            files: List[str] = []
            with target.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    image_path = Path(line)
                    if not image_path.is_absolute():
                        image_path = target.parent / image_path
                    files.append(str(image_path))
            return files
        if target.suffix.lower() in IMAGE_EXTENSIONS:
            return [str(target)]

    return []


def load_yolo_dataset_layout(dataset_root: str, split: str) -> Dict[str, Any]:
    root = Path(dataset_root)
    yaml_path: Optional[Path] = None
    for name in ("data.yaml", "dataset.yaml"):
        candidate = root / name
        if candidate.exists():
            yaml_path = candidate
            break

    if yaml_path is None:
        return {"is_yolo": False, "images": discover_images(dataset_root), "names": [], "yaml_path": None}

    if yaml is None:
        raise RuntimeError("PyYAML is required for YOLO dataset parsing. Install pyyaml.")

    with yaml_path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}

    names = parse_yolo_names(parsed.get("names", []))
    split_map: Dict[str, Any] = {
        "train": parsed.get("train"),
        "val": parsed.get("val", parsed.get("valid")),
        "test": parsed.get("test"),
    }

    selected = split.lower().strip()
    if selected == "valid":
        selected = "val"

    available_images: Dict[str, List[str]] = {}
    for key, source in split_map.items():
        files = resolve_dataset_entry(root, source)
        if files:
            available_images[key] = sorted(set(files))

    images: List[str] = []
    if selected == "all":
        seen: Dict[str, None] = {}
        for key in ("train", "val", "test"):
            for file_path in available_images.get(key, []):
                seen[file_path] = None
        images = list(seen.keys())
    else:
        images = available_images.get(selected, [])

    if not images:
        images = discover_images(dataset_root)

    return {
        "is_yolo": True,
        "images": sorted(set(images)),
        "names": names,
        "yaml_path": str(yaml_path),
        "available_splits": sorted(list(available_images.keys())),
    }


def image_path_to_label_path(image_path: str) -> str:
    img = Path(image_path)
    parts = list(img.parts)
    for idx, token in enumerate(parts):
        if token.lower() == "images":
            replaced = parts.copy()
            replaced[idx] = "labels"
            return str(Path(*replaced).with_suffix(".txt"))
    return str(img.with_suffix(".txt"))


def parse_yolo_label_file(label_path: str, image_w: int, image_h: int, class_count: int) -> List[Dict[str, Any]]:
    if not os.path.exists(label_path):
        return []

    gts: List[Dict[str, Any]] = []
    with open(label_path, "r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            parts = raw.split()
            if len(parts) < 5:
                continue
            try:
                cls_id = int(float(parts[0]))
                xc = float(parts[1])
                yc = float(parts[2])
                bw = float(parts[3])
                bh = float(parts[4])
            except ValueError:
                continue

            if cls_id < 0 or (class_count > 0 and cls_id >= class_count):
                continue

            x1 = max(0.0, (xc - bw / 2.0) * image_w)
            y1 = max(0.0, (yc - bh / 2.0) * image_h)
            x2 = min(float(image_w - 1), (xc + bw / 2.0) * image_w)
            y2 = min(float(image_h - 1), (yc + bh / 2.0) * image_h)

            if x2 <= x1 or y2 <= y1:
                continue

            gts.append({"cls": cls_id, "bbox": [x1, y1, x2, y2]})

    return gts


def clip_box(box: Sequence[float], image_w: int, image_h: int) -> List[float]:
    x1 = float(max(0.0, min(image_w - 1, box[0])))
    y1 = float(max(0.0, min(image_h - 1, box[1])))
    x2 = float(max(0.0, min(image_w - 1, box[2])))
    y2 = float(max(0.0, min(image_h - 1, box[3])))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return [x1, y1, x2, y2]


def box_iou(box_a: Sequence[float], box_b: Sequence[float]) -> float:
    inter_x1 = max(float(box_a[0]), float(box_b[0]))
    inter_y1 = max(float(box_a[1]), float(box_b[1]))
    inter_x2 = min(float(box_a[2]), float(box_b[2]))
    inter_y2 = min(float(box_a[3]), float(box_b[3]))

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, float(box_a[2]) - float(box_a[0])) * max(0.0, float(box_a[3]) - float(box_a[1]))
    area_b = max(0.0, float(box_b[2]) - float(box_b[0])) * max(0.0, float(box_b[3]) - float(box_b[1]))

    union = area_a + area_b - inter_area
    if union <= 0.0:
        return 0.0
    return inter_area / union


def greedy_match(iou_matrix: np.ndarray, min_iou: float) -> List[Tuple[int, int, float]]:
    if iou_matrix.size == 0:
        return []

    pred_count, gt_count = iou_matrix.shape
    candidates: List[Tuple[float, int, int]] = []
    for pred_idx in range(pred_count):
        for gt_idx in range(gt_count):
            score = float(iou_matrix[pred_idx, gt_idx])
            if score >= min_iou:
                candidates.append((score, pred_idx, gt_idx))

    candidates.sort(key=lambda item: item[0], reverse=True)
    used_preds: Dict[int, None] = {}
    used_gts: Dict[int, None] = {}
    matches: List[Tuple[int, int, float]] = []
    for score, pred_idx, gt_idx in candidates:
        if pred_idx in used_preds or gt_idx in used_gts:
            continue
        used_preds[pred_idx] = None
        used_gts[gt_idx] = None
        matches.append((pred_idx, gt_idx, score))
    return matches


def compute_ap(recall: np.ndarray, precision: np.ndarray) -> float:
    if recall.size == 0 or precision.size == 0:
        return 0.0

    mrec = np.concatenate(([0.0], recall, [1.0]))
    mpre = np.concatenate(([1.0], precision, [0.0]))
    for idx in range(mpre.size - 1, 0, -1):
        mpre[idx - 1] = max(mpre[idx - 1], mpre[idx])

    x = np.linspace(0.0, 1.0, 101)
    y = np.interp(x, mrec, mpre)
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def class_ap_for_iou(records: Sequence[Dict[str, Any]], cls_id: int, iou_thr: float) -> Tuple[float, int]:
    gt_by_image: Dict[int, List[Sequence[float]]] = {}
    predictions: List[Tuple[int, float, Sequence[float]]] = []
    gt_total = 0

    for image_idx, rec in enumerate(records):
        gts = [g["bbox"] for g in rec["gt"] if int(g["cls"]) == cls_id]
        if gts:
            gt_by_image[image_idx] = gts
            gt_total += len(gts)

        for pred in rec["pred"]:
            if int(pred["cls"]) != cls_id:
                continue
            predictions.append((image_idx, float(pred["conf"]), pred["bbox"]))

    if gt_total == 0:
        return float("nan"), 0

    predictions.sort(key=lambda item: item[1], reverse=True)
    matched: Dict[int, Dict[int, None]] = {}
    tp: List[int] = []
    fp: List[int] = []

    for image_idx, _, pred_box in predictions:
        gt_boxes = gt_by_image.get(image_idx, [])
        if image_idx not in matched:
            matched[image_idx] = {}

        best_iou = 0.0
        best_idx = -1
        for gt_idx, gt_box in enumerate(gt_boxes):
            if gt_idx in matched[image_idx]:
                continue
            iou = box_iou(pred_box, gt_box)
            if iou > best_iou:
                best_iou = iou
                best_idx = gt_idx

        if best_idx >= 0 and best_iou >= iou_thr:
            matched[image_idx][best_idx] = None
            tp.append(1)
            fp.append(0)
        else:
            tp.append(0)
            fp.append(1)

    if not tp:
        return 0.0, gt_total

    tp_cum = np.cumsum(np.asarray(tp, dtype=np.float64))
    fp_cum = np.cumsum(np.asarray(fp, dtype=np.float64))
    recall = tp_cum / max(float(gt_total), 1e-9)
    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1e-9)
    return compute_ap(recall, precision), gt_total


def evaluate_confidence_at(records: Sequence[Dict[str, Any]], conf_thr: float, class_count: int, iou_thr: float) -> Tuple[int, int, int]:
    tp_total = 0
    fp_total = 0
    fn_total = 0

    for rec in records:
        for cls_id in range(class_count):
            preds = [p for p in rec["pred"] if int(p["cls"]) == cls_id and float(p["conf"]) >= conf_thr]
            gts = [g for g in rec["gt"] if int(g["cls"]) == cls_id]

            if not preds and not gts:
                continue
            if preds and not gts:
                fp_total += len(preds)
                continue
            if gts and not preds:
                fn_total += len(gts)
                continue

            iou_matrix = np.zeros((len(preds), len(gts)), dtype=np.float64)
            for pred_idx, pred in enumerate(preds):
                for gt_idx, gt in enumerate(gts):
                    iou_matrix[pred_idx, gt_idx] = box_iou(pred["bbox"], gt["bbox"])

            matches = greedy_match(iou_matrix, iou_thr)
            match_count = len(matches)
            tp_total += match_count
            fp_total += len(preds) - match_count
            fn_total += len(gts) - match_count

    return tp_total, fp_total, fn_total


def compute_confusion_matrix(records: Sequence[Dict[str, Any]], class_count: int, conf_thr: float, iou_thr: float) -> np.ndarray:
    matrix = np.zeros((class_count + 1, class_count + 1), dtype=np.int64)
    bg_idx = class_count

    for rec in records:
        preds = [p for p in rec["pred"] if float(p["conf"]) >= conf_thr]
        gts = rec["gt"]

        if preds and gts:
            iou_matrix = np.zeros((len(preds), len(gts)), dtype=np.float64)
            for pred_idx, pred in enumerate(preds):
                for gt_idx, gt in enumerate(gts):
                    iou_matrix[pred_idx, gt_idx] = box_iou(pred["bbox"], gt["bbox"])
            matches = greedy_match(iou_matrix, iou_thr)
        else:
            matches = []

        used_pred: Dict[int, None] = {}
        used_gt: Dict[int, None] = {}
        for pred_idx, gt_idx, _ in matches:
            used_pred[pred_idx] = None
            used_gt[gt_idx] = None
            gt_cls = int(gts[gt_idx]["cls"])
            pred_cls = int(preds[pred_idx]["cls"])
            matrix[gt_cls, pred_cls] += 1

        for gt_idx, gt in enumerate(gts):
            if gt_idx in used_gt:
                continue
            matrix[int(gt["cls"]), bg_idx] += 1

        for pred_idx, pred in enumerate(preds):
            if pred_idx in used_pred:
                continue
            matrix[bg_idx, int(pred["cls"])] += 1

    return matrix


def save_yolo_eval_report(
    report_dir: str,
    class_names: Sequence[str],
    summary: Dict[str, Any],
    conf_thresholds: np.ndarray,
    precision_curve: np.ndarray,
    recall_curve: np.ndarray,
    f1_curve: np.ndarray,
    confusion_matrix: np.ndarray,
) -> Dict[str, str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required to generate evaluation plots.") from exc

    out_root = Path(report_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    files: Dict[str, str] = {}

    summary_path = out_root / "metrics_summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    files["summary_json"] = str(summary_path)

    def save_curve(x: np.ndarray, y: np.ndarray, title: str, x_label: str, y_label: str, filename: str) -> None:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(x, y, linewidth=2)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        out_path = out_root / filename
        fig.savefig(out_path, dpi=160)
        plt.close(fig)
        files[filename] = str(out_path)

    save_curve(recall_curve, precision_curve, "Precision-Recall Curve", "Recall", "Precision", "pr_curve.png")
    save_curve(conf_thresholds, f1_curve, "F1-Confidence Curve", "Confidence", "F1", "f1_conf_curve.png")
    save_curve(conf_thresholds, precision_curve, "Precision-Confidence Curve", "Confidence", "Precision", "p_conf_curve.png")
    save_curve(conf_thresholds, recall_curve, "Recall-Confidence Curve", "Confidence", "Recall", "r_conf_curve.png")

    cm = confusion_matrix.astype(np.float64)
    cm_row_sum = cm.sum(axis=1, keepdims=True)
    cm_norm = np.divide(cm, np.maximum(cm_row_sum, 1.0))

    labels = list(class_names) + ["background"]
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0.0, vmax=1.0)
    ax.set_title("Confusion Matrix (row-normalized)")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Ground Truth")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    cm_path = out_root / "confusion_matrix.png"
    fig.savefig(cm_path, dpi=180)
    plt.close(fig)
    files["confusion_matrix.png"] = str(cm_path)

    return files


class InferenceToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.screen_w = int(self.root.winfo_screenwidth())
        self.screen_h = int(self.root.winfo_screenheight())
        self.small_screen_mode = self.screen_w <= 900 or self.screen_h <= 600
        self.compact_pad = 2
        self.root.title("TCDD Standalone Inference Tool")
        if self.small_screen_mode:
            self.root.geometry(f"{self.screen_w}x{self.screen_h}")
        else:
            self.root.geometry("1400x900")

        self.backend: Optional[BaseBackend] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.ui_queue: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self.preview_image: Optional[ImageTk.PhotoImage] = None
        self.preview_image_popup: Optional[ImageTk.PhotoImage] = None
        self.log_window: Optional[tk.Toplevel] = None
        self.preview_window: Optional[tk.Toplevel] = None
        self.log_text_popup: Optional[ScrolledText] = None
        self.model_info_text_popup: Optional[ScrolledText] = None
        self.preview_label_popup: Optional[ttk.Label] = None

        self.model_path_var = tk.StringVar()
        self.model_format_var = tk.StringVar(value="Unknown")
        self.labels_path_var = tk.StringVar(value="backend/models/labels.txt")
        self.mode_var = tk.StringVar(value="image")
        self.image_path_var = tk.StringVar()
        self.video_path_var = tk.StringVar()
        self.dataset_path_var = tk.StringVar()
        self.dataset_split_var = tk.StringVar(value="val")
        self.camera_source_var = tk.StringVar(value="0")
        self.device_var = tk.StringVar(value="cpu")
        self.input_color_space_var = tk.StringVar(value="BGR")

        self.use_hailo_var = tk.BooleanVar(value=True)
        self.prefer_gpu_var = tk.BooleanVar(value=False)

        self.confidence_var = tk.StringVar(value="0.50")
        self.iou_var = tk.StringVar(value="0.45")
        self.warmup_var = tk.StringVar(value="5")
        self.iterations_var = tk.StringVar(value="50")

        self.cam_width_var = tk.StringVar(value="640")
        self.cam_height_var = tk.StringVar(value="480")
        self.cam_fps_var = tk.StringVar(value="30")

        self.status_var = tk.StringVar(value="Idle")
        self.stats_var = tk.StringVar(value="No benchmark yet")
        self.image_drop_enabled = True

        self._build_ui()
        self._setup_image_receiver()
        self._refresh_capability_hint()
        if self.small_screen_mode:
            self._log("Small screen mode enabled: model info/logs and preview open in separate windows.")
            self._ensure_small_screen_popouts(open_logs=True, open_preview=True)

        self.model_path_var.trace_add("write", self._on_model_path_changed)
        self.mode_var.trace_add("write", self._on_mode_changed)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(60, self._poll_ui_queue)
        self._apply_mode_controls()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=4 if self.small_screen_mode else 8)
        outer.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(outer)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.Frame(outer)
        if not self.small_screen_mode:
            right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        model_path_width = 72 if not self.small_screen_mode else 38
        labels_path_width = 50 if not self.small_screen_mode else 28
        image_path_width = 68 if not self.small_screen_mode else 34
        dataset_path_width = 52 if not self.small_screen_mode else 28

        model_frame = ttk.LabelFrame(left, text="Model")
        model_frame.pack(fill=tk.X, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        ttk.Label(model_frame, text="Path").grid(row=0, column=0, sticky="w", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Entry(model_frame, textvariable=self.model_path_var, width=model_path_width).grid(row=0, column=1, sticky="ew", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Button(model_frame, text="Browse", command=self._browse_model).grid(row=0, column=2, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        ttk.Label(model_frame, text="Format").grid(row=1, column=0, sticky="w", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Label(model_frame, textvariable=self.model_format_var).grid(row=1, column=1, sticky="w", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        ttk.Label(model_frame, text="Labels").grid(row=2, column=0, sticky="w", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Entry(model_frame, textvariable=self.labels_path_var, width=labels_path_width).grid(row=2, column=1, sticky="ew", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Button(model_frame, text="Browse", command=self._browse_labels).grid(row=2, column=2, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        controls_row = ttk.Frame(model_frame)
        controls_row.grid(row=3, column=0, columnspan=3, sticky="ew", padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        ttk.Checkbutton(controls_row, text="Use Hailo for HEF", variable=self.use_hailo_var).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(controls_row, text="Prefer GPU (ONNX)", variable=self.prefer_gpu_var).pack(side=tk.LEFT, padx=4)

        ttk.Label(controls_row, text="Device").pack(side=tk.LEFT, padx=(12, 2))
        ttk.Combobox(
            controls_row,
            textvariable=self.device_var,
            values=["cpu", "cuda"],
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)

        ttk.Label(controls_row, text="Input Color").pack(side=tk.LEFT, padx=(12, 2))
        ttk.Combobox(
            controls_row,
            textvariable=self.input_color_space_var,
            values=["BGR", "RGB"],
            width=6,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(controls_row, text="Load Model", command=self._load_model).pack(side=tk.RIGHT, padx=4)
        model_frame.columnconfigure(1, weight=1)

        input_frame = ttk.LabelFrame(left, text="Input")
        input_frame.pack(fill=tk.X, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        mode_row = ttk.Frame(input_frame)
        mode_row.pack(fill=tk.X, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Radiobutton(mode_row, text="Single Image", variable=self.mode_var, value="image").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(mode_row, text="Video", variable=self.mode_var, value="video").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(mode_row, text="Dataset", variable=self.mode_var, value="dataset").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(mode_row, text="Camera Stream", variable=self.mode_var, value="camera").pack(side=tk.LEFT, padx=4)

        self.image_row = ttk.Frame(input_frame)
        if not self.small_screen_mode:
            self.image_row.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(self.image_row, text="Image").pack(side=tk.LEFT)
        self.image_entry = ttk.Entry(self.image_row, textvariable=self.image_path_var, width=image_path_width)
        self.image_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.image_browse_btn = ttk.Button(self.image_row, text="Browse", command=self._browse_image)
        self.image_browse_btn.pack(side=tk.LEFT)

        self.video_row = ttk.Frame(input_frame)
        if not self.small_screen_mode:
            self.video_row.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(self.video_row, text="Video").pack(side=tk.LEFT)
        self.video_entry = ttk.Entry(self.video_row, textvariable=self.video_path_var, width=image_path_width)
        self.video_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.video_browse_btn = ttk.Button(self.video_row, text="Browse", command=self._browse_video)
        self.video_browse_btn.pack(side=tk.LEFT)

        self.image_receiver_row = ttk.Frame(input_frame)
        if not self.small_screen_mode:
            self.image_receiver_row.pack(fill=tk.X, padx=4, pady=(0, 4))
        drop_text = "Drop image or press Ctrl+V to paste" if self.small_screen_mode else "Drop an image here or press Ctrl+V to paste from clipboard"
        self.image_drop_label = tk.Label(
            self.image_receiver_row,
            text=drop_text,
            relief="groove",
            borderwidth=2,
            padx=6 if self.small_screen_mode else 8,
            pady=3 if self.small_screen_mode else 8,
            anchor="w",
            bg="#f5f7fa",
        )
        self.image_drop_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.image_paste_btn = ttk.Button(
            self.image_receiver_row,
            text="Paste",
            command=self._paste_image_from_clipboard,
        )
        self.image_paste_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.dataset_row = ttk.Frame(input_frame)
        if not self.small_screen_mode:
            self.dataset_row.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(self.dataset_row, text="Dataset").pack(side=tk.LEFT)
        self.dataset_entry = ttk.Entry(self.dataset_row, textvariable=self.dataset_path_var, width=dataset_path_width)
        self.dataset_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.dataset_browse_btn = ttk.Button(self.dataset_row, text="Browse", command=self._browse_dataset)
        self.dataset_browse_btn.pack(side=tk.LEFT)
        ttk.Label(self.dataset_row, text="Split").pack(side=tk.LEFT, padx=(10, 2))
        self.dataset_split_combo = ttk.Combobox(
            self.dataset_row,
            textvariable=self.dataset_split_var,
            values=["all", "train", "val", "test", "valid"],
            width=8,
            state="readonly",
        )
        self.dataset_split_combo.pack(side=tk.LEFT)

        self.camera_row = ttk.Frame(input_frame)
        if not self.small_screen_mode:
            self.camera_row.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(self.camera_row, text="Camera Source").pack(side=tk.LEFT)
        self.camera_source_combo = ttk.Combobox(
            self.camera_row,
            textvariable=self.camera_source_var,
            values=["0", "1", "2", "3", "4", "rpi_camera"],
            width=12,
            state="readonly",
        )
        self.camera_source_combo.pack(side=tk.LEFT, padx=6)

        ttk.Label(self.camera_row, text="Width").pack(side=tk.LEFT, padx=(12, 2))
        self.cam_width_entry = ttk.Entry(self.camera_row, textvariable=self.cam_width_var, width=6)
        self.cam_width_entry.pack(side=tk.LEFT)
        ttk.Label(self.camera_row, text="Height").pack(side=tk.LEFT, padx=(8, 2))
        self.cam_height_entry = ttk.Entry(self.camera_row, textvariable=self.cam_height_var, width=6)
        self.cam_height_entry.pack(side=tk.LEFT)
        ttk.Label(self.camera_row, text="FPS").pack(side=tk.LEFT, padx=(8, 2))
        self.cam_fps_entry = ttk.Entry(self.camera_row, textvariable=self.cam_fps_var, width=6)
        self.cam_fps_entry.pack(side=tk.LEFT)

        bench_frame = ttk.LabelFrame(left, text="Benchmark")
        bench_frame.pack(fill=tk.X, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)

        if self.small_screen_mode:
            ttk.Label(bench_frame, text="Conf").grid(row=0, column=0, padx=2, pady=2, sticky="w")
            ttk.Entry(bench_frame, textvariable=self.confidence_var, width=6).grid(row=0, column=1, padx=2, pady=2, sticky="w")

            ttk.Label(bench_frame, text="IOU").grid(row=0, column=2, padx=2, pady=2, sticky="w")
            ttk.Entry(bench_frame, textvariable=self.iou_var, width=6).grid(row=0, column=3, padx=2, pady=2, sticky="w")

            ttk.Label(bench_frame, text="Warm").grid(row=0, column=4, padx=2, pady=2, sticky="w")
            ttk.Entry(bench_frame, textvariable=self.warmup_var, width=5).grid(row=0, column=5, padx=2, pady=2, sticky="w")

            ttk.Label(bench_frame, text="Iter").grid(row=0, column=6, padx=2, pady=2, sticky="w")
            self.iterations_entry = ttk.Entry(bench_frame, textvariable=self.iterations_var, width=6)
            self.iterations_entry.grid(row=0, column=7, padx=2, pady=2, sticky="w")
        else:
            ttk.Label(bench_frame, text="Confidence").grid(row=0, column=0, padx=4, pady=4, sticky="w")
            ttk.Entry(bench_frame, textvariable=self.confidence_var, width=8).grid(row=0, column=1, padx=4, pady=4, sticky="w")

            ttk.Label(bench_frame, text="IOU").grid(row=0, column=2, padx=4, pady=4, sticky="w")
            ttk.Entry(bench_frame, textvariable=self.iou_var, width=8).grid(row=0, column=3, padx=4, pady=4, sticky="w")

            ttk.Label(bench_frame, text="Warmup").grid(row=0, column=4, padx=4, pady=4, sticky="w")
            ttk.Entry(bench_frame, textvariable=self.warmup_var, width=8).grid(row=0, column=5, padx=4, pady=4, sticky="w")

            ttk.Label(bench_frame, text="Iterations (image)").grid(row=0, column=6, padx=4, pady=4, sticky="w")
            self.iterations_entry = ttk.Entry(bench_frame, textvariable=self.iterations_var, width=8)
            self.iterations_entry.grid(row=0, column=7, padx=4, pady=4, sticky="w")

        action_row = ttk.Frame(left)
        action_row.pack(fill=tk.X, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 6)
        ttk.Button(action_row, text="Start", command=self._start).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_row, text="Stop", command=self._stop).pack(side=tk.LEFT, padx=4)
        ttk.Label(action_row, textvariable=self.status_var).pack(side=tk.RIGHT, padx=6)

        stats_frame = ttk.LabelFrame(left, text="Statistics")
        stats_frame.pack(fill=tk.X, padx=self.compact_pad if self.small_screen_mode else 4, pady=self.compact_pad if self.small_screen_mode else 4)
        ttk.Label(stats_frame, textvariable=self.stats_var, justify=tk.LEFT).pack(fill=tk.X, padx=6, pady=6)

        self.model_info_text = ScrolledText(left, height=7)
        if not self.small_screen_mode:
            self.model_info_text.pack(fill=tk.BOTH, padx=4, pady=4)
        self.model_info_text.insert(tk.END, "Model info will appear here.\n")
        self.model_info_text.configure(state=tk.DISABLED)

        logs_frame = ttk.LabelFrame(right, text="Logs")
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.log_text = ScrolledText(logs_frame, height=18)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        preview_frame = ttk.LabelFrame(right, text="Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _on_popup_log_close(self) -> None:
        if self.log_window is not None:
            self.log_window.destroy()
        self.log_window = None
        self.model_info_text_popup = None
        self.log_text_popup = None

    def _on_popup_preview_close(self) -> None:
        if self.preview_window is not None:
            self.preview_window.destroy()
        self.preview_window = None
        self.preview_label_popup = None
        self.preview_image_popup = None

    def _ensure_small_screen_popouts(self, *, open_logs: bool, open_preview: bool) -> None:
        if not self.small_screen_mode:
            return

        if open_logs and (self.log_window is None or not self.log_window.winfo_exists()):
            self.log_window = tk.Toplevel(self.root)
            self.log_window.title("MITT Model Info and Logs")
            self.log_window.geometry(f"{min(620, self.screen_w - 20)}x{min(460, self.screen_h - 40)}")
            self.log_window.protocol("WM_DELETE_WINDOW", self._on_popup_log_close)

            frame = ttk.Frame(self.log_window, padding=6)
            frame.pack(fill=tk.BOTH, expand=True)

            info_frame = ttk.LabelFrame(frame, text="Model Info")
            info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
            self.model_info_text_popup = ScrolledText(info_frame, height=8)
            self.model_info_text_popup.pack(fill=tk.BOTH, expand=True)
            model_existing = self.model_info_text.get("1.0", tk.END)
            if model_existing.strip():
                self.model_info_text_popup.insert(tk.END, model_existing)
                self.model_info_text_popup.see(tk.END)
            self.model_info_text_popup.configure(state=tk.DISABLED)

            logs_frame = ttk.LabelFrame(frame, text="Logs")
            logs_frame.pack(fill=tk.BOTH, expand=True)
            self.log_text_popup = ScrolledText(logs_frame, height=12)
            self.log_text_popup.pack(fill=tk.BOTH, expand=True)
            existing = self.log_text.get("1.0", tk.END)
            if existing.strip():
                self.log_text_popup.insert(tk.END, existing)
                self.log_text_popup.see(tk.END)

        if open_preview and (self.preview_window is None or not self.preview_window.winfo_exists()):
            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.title("MITT Preview")
            self.preview_window.geometry(f"{min(760, self.screen_w - 20)}x{min(520, self.screen_h - 40)}")
            self.preview_window.protocol("WM_DELETE_WINDOW", self._on_popup_preview_close)

            frame = ttk.Frame(self.preview_window, padding=6)
            frame.pack(fill=tk.BOTH, expand=True)
            self.preview_label_popup = ttk.Label(frame)
            self.preview_label_popup.pack(fill=tk.BOTH, expand=True)

    def _setup_image_receiver(self) -> None:
        self.root.bind_all("<Control-v>", self._on_paste_shortcut)
        self.root.bind_all("<Control-V>", self._on_paste_shortcut)

        if HAS_TKDND:
            try:
                self.image_drop_label.drop_target_register(DND_FILES)
                self.image_drop_label.dnd_bind("<<Drop>>", self._on_image_drop)
                self._log("Drag-drop enabled for Single Image input")
            except Exception as exc:
                self._log(f"Drag-drop setup failed: {exc}")
        else:
            self._log("Drag-drop extension not available (install tkinterdnd2 for file drop support)")

    def _set_drop_zone_visual_state(self, enabled: bool) -> None:
        self.image_drop_enabled = enabled
        if enabled:
            text = "Drop an image here or press Ctrl+V to paste from clipboard"
            bg = "#f5f7fa"
        else:
            text = "Drop/Paste is available only in Single Image mode"
            bg = "#e8eaed"
        self.image_drop_label.configure(text=text, bg=bg)

    def _refresh_capability_hint(self) -> None:
        hints = [
            f"OS={platform.system()} {platform.release()}",
            f"ultralytics={'yes' if HAS_YOLO else 'no'}",
            f"hailo_platform={'yes' if HAS_HAILO else 'no'}",
            f"onnxruntime={'yes' if ort else 'no'}",
            f"picamera2={'yes' if Picamera2 else 'no'}",
        ]
        self._log("Capabilities: " + " | ".join(hints))

    def _on_model_path_changed(self, *_: Any) -> None:
        suffix = Path(self.model_path_var.get().strip()).suffix.lower()
        if suffix in MODEL_EXTENSIONS:
            self.model_format_var.set(suffix[1:].upper())
        else:
            self.model_format_var.set("Unknown")

    def _set_single_image_path(self, image_path: str, source: str) -> None:
        self.image_path_var.set(image_path)
        self._log(f"Single image set from {source}: {image_path}")

    def _save_clipboard_image(self, image: Image.Image) -> str:
        out_dir = Path("data") / "captures" / "mitt_clipboard"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"clipboard_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        image.convert("RGB").save(out_path, format="PNG")
        return str(out_path)

    def _download_dropped_image_url(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read()

        encoded = np.frombuffer(payload, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError("Dropped URL did not return a decodable image")

        out_dir = Path("data") / "captures" / "mitt_drop"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"drop_url_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        if not cv2.imwrite(str(out_path), frame):
            raise RuntimeError("Failed to save downloaded image from URL")
        return str(out_path)

    def _paste_image_from_clipboard(self) -> None:
        if self.mode_var.get() != "image":
            return
        if ImageGrab is None:
            messagebox.showerror("Clipboard", "Clipboard image paste is not available in this environment.")
            return

        try:
            clip = ImageGrab.grabclipboard()
        except Exception as exc:
            messagebox.showerror("Clipboard", f"Unable to read clipboard: {exc}")
            return

        if clip is None:
            messagebox.showwarning("Clipboard", "Clipboard does not contain an image.")
            return

        if isinstance(clip, Image.Image):
            saved_path = self._save_clipboard_image(clip)
            self._set_single_image_path(saved_path, source="clipboard image")
            frame = cv2.imread(saved_path)
            if frame is not None:
                self._render_preview(frame)
            return

        if isinstance(clip, list):
            for item in clip:
                candidate = str(item)
                ext = Path(candidate).suffix.lower()
                if ext in IMAGE_EXTENSIONS and os.path.exists(candidate):
                    self._set_single_image_path(candidate, source="clipboard file")
                    frame = cv2.imread(candidate)
                    if frame is not None:
                        self._render_preview(frame)
                    return

        messagebox.showwarning("Clipboard", "Clipboard content is not a supported image.")

    def _on_paste_shortcut(self, _event: Any) -> str:
        if self.mode_var.get() != "image" or not self.image_drop_enabled:
            return ""
        self._paste_image_from_clipboard()
        return "break"

    def _extract_drop_paths(self, raw_data: str) -> List[str]:
        try:
            values = list(self.root.tk.splitlist(raw_data))
        except Exception:
            values = [raw_data]

        out: List[str] = []
        for value in values:
            cleaned = str(value).strip().strip("{}")
            if cleaned:
                out.append(cleaned)
        return out

    def _on_image_drop(self, event: Any) -> str:
        if self.mode_var.get() != "image" or not self.image_drop_enabled:
            return "break"

        paths = self._extract_drop_paths(getattr(event, "data", ""))
        for candidate in paths:
            ext = Path(candidate).suffix.lower()
            if ext in IMAGE_EXTENSIONS and os.path.exists(candidate):
                self._set_single_image_path(candidate, source="drag-drop")
                frame = cv2.imread(candidate)
                if frame is not None:
                    self._render_preview(frame)
                return "break"

            if candidate.startswith("http://") or candidate.startswith("https://"):
                try:
                    downloaded = self._download_dropped_image_url(candidate)
                except Exception as exc:
                    self._log(f"Dropped URL is not usable as image: {exc}")
                    continue

                self._set_single_image_path(downloaded, source="drag-drop URL")
                frame = cv2.imread(downloaded)
                if frame is not None:
                    self._render_preview(frame)
                return "break"

        messagebox.showwarning("Drop Image", "Dropped item is not a supported local image file or image URL.")
        return "break"

    def _set_control_state(self, widget: Any, enabled: bool, *, readonly_when_enabled: bool = False) -> None:
        if readonly_when_enabled:
            widget.configure(state="readonly" if enabled else "disabled")
            return
        widget.configure(state="normal" if enabled else "disabled")

    def _on_mode_changed(self, *_: Any) -> None:
        self._apply_mode_controls()

    def _set_small_screen_input_rows(self, *, is_image: bool, is_video: bool, is_dataset: bool, is_camera: bool) -> None:
        if not self.small_screen_mode:
            return

        for row in (self.image_row, self.image_receiver_row, self.video_row, self.dataset_row, self.camera_row):
            if row.winfo_manager():
                row.pack_forget()

        if is_image:
            self.image_row.pack(fill=tk.X, padx=self.compact_pad, pady=1)
            self.image_receiver_row.pack(fill=tk.X, padx=self.compact_pad, pady=(0, 2))
        elif is_video:
            self.video_row.pack(fill=tk.X, padx=self.compact_pad, pady=1)
        elif is_dataset:
            self.dataset_row.pack(fill=tk.X, padx=self.compact_pad, pady=1)
        elif is_camera:
            self.camera_row.pack(fill=tk.X, padx=self.compact_pad, pady=1)

    def _apply_mode_controls(self) -> None:
        mode = self.mode_var.get()
        is_image = mode == "image"
        is_video = mode == "video"
        is_dataset = mode == "dataset"
        is_camera = mode == "camera"

        self._set_small_screen_input_rows(is_image=is_image, is_video=is_video, is_dataset=is_dataset, is_camera=is_camera)

        # Single image controls
        self._set_control_state(self.image_entry, is_image)
        self._set_control_state(self.image_browse_btn, is_image)
        self._set_control_state(self.image_paste_btn, is_image)
        self._set_drop_zone_visual_state(is_image)

        # Video controls
        self._set_control_state(self.video_entry, is_video)
        self._set_control_state(self.video_browse_btn, is_video)

        # Dataset controls
        self._set_control_state(self.dataset_entry, is_dataset)
        self._set_control_state(self.dataset_browse_btn, is_dataset)
        self._set_control_state(self.dataset_split_combo, is_dataset, readonly_when_enabled=True)

        # Camera controls
        self._set_control_state(self.camera_source_combo, is_camera, readonly_when_enabled=True)
        self._set_control_state(self.cam_width_entry, is_camera)
        self._set_control_state(self.cam_height_entry, is_camera)
        self._set_control_state(self.cam_fps_entry, is_camera)

        # Iterations are only used in single-image mode
        self._set_control_state(self.iterations_entry, is_image)

    def _browse_model(self) -> None:
        path = filedialog.askopenfilename(
            title="Select model",
            filetypes=[("Model files", "*.pt *.pth *.onnx *.hef"), ("All files", "*.*")],
        )
        if path:
            self.model_path_var.set(path)

    def _browse_labels(self) -> None:
        path = filedialog.askopenfilename(
            title="Select labels file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.labels_path_var.set(path)

    def _browse_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")],
        )
        if path:
            self.image_path_var.set(path)

    def _browse_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Select video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv *.m4v *.webm *.flv *.mpeg *.mpg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.video_path_var.set(path)

    def _browse_dataset(self) -> None:
        path = filedialog.askdirectory(title="Select dataset folder")
        if path:
            self.dataset_path_var.set(path)

    def _parse_int(self, raw: str, default: int, minimum: int = 0) -> int:
        try:
            value = int(raw)
        except ValueError:
            return default
        return max(value, minimum)

    def _parse_float(self, raw: str, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        try:
            value = float(raw)
        except ValueError:
            return default
        return max(minimum, min(maximum, value))

    @staticmethod
    def _read_numeric_file(path: str) -> Optional[float]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = handle.read().strip()
        except Exception:
            return None

        if not raw:
            return None

        match = re.search(r"[-+]?\d*\.?\d+", raw)
        if not match:
            return None

        try:
            return float(match.group(0))
        except ValueError:
            return None

    def _read_linux_temp_c(self) -> Optional[float]:
        candidates = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/devices/virtual/thermal/thermal_zone0/temp",
        ]
        for path in candidates:
            value = self._read_numeric_file(path)
            if value is None:
                continue
            if value > 200.0:
                value /= 1000.0
            if -40.0 <= value <= 150.0:
                return value
        return None

    def _read_linux_power_w(self) -> Optional[float]:
        base = Path("/sys/class/power_supply")
        if not base.exists():
            return None

        for supply in base.iterdir():
            power_now = supply / "power_now"
            if power_now.exists():
                value = self._read_numeric_file(str(power_now))
                if value is not None:
                    # Usually microwatts on Linux sysfs.
                    if value > 10000.0:
                        return value / 1_000_000.0
                    return value

            voltage_now = supply / "voltage_now"
            current_now = supply / "current_now"
            if voltage_now.exists() and current_now.exists():
                voltage_uv = self._read_numeric_file(str(voltage_now))
                current_ua = self._read_numeric_file(str(current_now))
                if voltage_uv is None or current_ua is None:
                    continue
                return (voltage_uv * current_ua) / 1_000_000_000_000.0

        return None

    def _read_hailo_util_pct(self) -> Optional[float]:
        candidates = [
            "/sys/class/hailo_chardev/hailo0/device/utilization",
            "/sys/class/hailo_chardev/hailo0/device/hailo_utilization",
            "/sys/class/hailo_chardev/hailo0/device/npu_utilization",
            "/sys/class/hailo0/device/utilization",
        ]
        for path in candidates:
            value = self._read_numeric_file(path)
            if value is None:
                continue
            if 0.0 <= value <= 1.0:
                return value * 100.0
            if 0.0 <= value <= 100.0:
                return value
        return None

    def _sample_system_metrics(self) -> Dict[str, float]:
        metrics: Dict[str, float] = {}

        if psutil is not None:
            try:
                metrics["cpu_util_pct"] = float(psutil.cpu_percent(interval=None))
            except Exception:
                pass

        if os.name != "nt":
            temp_c = self._read_linux_temp_c()
            if temp_c is not None:
                metrics["temp_c"] = float(temp_c)

            power_w = self._read_linux_power_w()
            if power_w is not None:
                metrics["power_w"] = float(power_w)

            hailo_util_pct = self._read_hailo_util_pct()
            if hailo_util_pct is not None:
                metrics["hailo_util_pct"] = float(hailo_util_pct)

        return metrics

    @staticmethod
    def _aggregate_metrics(samples: Sequence[Dict[str, float]]) -> Dict[str, float]:
        grouped: Dict[str, List[float]] = {}
        for sample in samples:
            for key, value in sample.items():
                try:
                    numeric = float(value)
                except Exception:
                    continue
                if np.isnan(numeric) or np.isinf(numeric):
                    continue
                grouped.setdefault(key, []).append(numeric)

        out: Dict[str, float] = {}
        for key, vals in grouped.items():
            if vals:
                out[key] = float(np.mean(np.asarray(vals, dtype=np.float64)))
        return out

    def _selected_input_color_space(self) -> str:
        color = str(self.input_color_space_var.get() or "BGR").strip().upper()
        return "RGB" if color == "RGB" else "BGR"

    def _infer_with_color_space(self, frame_bgr: np.ndarray) -> Tuple[InferenceResult, float]:
        assert self.backend is not None

        color = self._selected_input_color_space()
        if color == "RGB":
            model_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        else:
            model_frame = frame_bgr

        if isinstance(self.backend, OnnxBackend):
            self.backend.input_frame_color_space = color

        start = time.perf_counter()
        result = self.backend.infer(model_frame)
        e2e_ms = (time.perf_counter() - start) * 1000.0

        if color == "RGB" and result.annotated_frame is not None:
            try:
                result.annotated_frame = cv2.cvtColor(result.annotated_frame, cv2.COLOR_RGB2BGR)
            except Exception:
                pass

        return result, e2e_ms

    def _load_model(self) -> bool:
        model_path = self.model_path_var.get().strip()
        if not model_path:
            messagebox.showerror("Model", "Please select a model file.")
            return False
        if not os.path.exists(model_path):
            messagebox.showerror("Model", f"Model file not found:\n{model_path}")
            return False

        suffix = Path(model_path).suffix.lower()
        if suffix not in MODEL_EXTENSIONS:
            messagebox.showerror("Model", "Unsupported model extension. Use .pt, .pth, .onnx, or .hef")
            return False

        confidence = self._parse_float(self.confidence_var.get(), 0.5)
        iou = self._parse_float(self.iou_var.get(), 0.45)
        labels_path = self.labels_path_var.get().strip() or "backend/models/labels.txt"
        device = self.device_var.get().strip() or "cpu"

        if self.backend is not None:
            self.backend.close()
            self.backend = None

        try:
            if suffix in {".pt", ".pth", ".hef"}:
                backend = DetectorBackend(
                    model_path=model_path,
                    confidence=confidence,
                    iou=iou,
                    labels_path=labels_path,
                    use_hailo_for_hef=self.use_hailo_var.get(),
                    device=device,
                )
            elif suffix == ".onnx":
                backend = OnnxBackend(
                    model_path=model_path,
                    prefer_gpu=self.prefer_gpu_var.get(),
                    confidence=confidence,
                    iou=iou,
                    labels_path=labels_path,
                )
            else:
                raise RuntimeError(f"Unsupported model format: {suffix}")

            self.backend = backend
            info = backend.get_model_info()
            self._set_model_info(info)
            self._log(f"Model loaded with backend={info.get('backend', 'unknown')}")
            self.status_var.set("Model loaded")
            return True

        except Exception as exc:
            self._log(f"Model load failed: {exc}")
            messagebox.showerror("Model Load Failed", str(exc))
            self.status_var.set("Load failed")
            return False

    def _set_model_info(self, info: Dict[str, Any]) -> None:
        lines = ["Model information:"]
        for key, value in info.items():
            lines.append(f"- {key}: {value}")

        self.model_info_text.configure(state=tk.NORMAL)
        self.model_info_text.delete("1.0", tk.END)
        self.model_info_text.insert(tk.END, "\n".join(lines) + "\n")
        self.model_info_text.configure(state=tk.DISABLED)

        if self.small_screen_mode and self.model_info_text_popup is not None:
            self.model_info_text_popup.configure(state=tk.NORMAL)
            self.model_info_text_popup.delete("1.0", tk.END)
            self.model_info_text_popup.insert(tk.END, "\n".join(lines) + "\n")
            self.model_info_text_popup.configure(state=tk.DISABLED)

    def _start(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Benchmark", "A run is already active.")
            return

        if self.small_screen_mode:
            self._ensure_small_screen_popouts(open_logs=True, open_preview=True)

        if self.backend is None and not self._load_model():
            return

        run_config = {
            "mode": self.mode_var.get(),
            "warmup": self._parse_int(self.warmup_var.get(), 5, minimum=0),
            "iterations": self._parse_int(self.iterations_var.get(), 50, minimum=1),
            "image_path": self.image_path_var.get().strip(),
            "video_path": self.video_path_var.get().strip(),
            "dataset_path": self.dataset_path_var.get().strip(),
            "dataset_split": self.dataset_split_var.get().strip(),
            "camera_source": self.camera_source_var.get().strip(),
            "cam_width": self._parse_int(self.cam_width_var.get(), 640, minimum=64),
            "cam_height": self._parse_int(self.cam_height_var.get(), 480, minimum=64),
            "cam_fps": self._parse_int(self.cam_fps_var.get(), 30, minimum=1),
        }

        self.stop_event.clear()
        self.status_var.set("Running")
        self.stats_var.set("Running...")

        self.worker_thread = threading.Thread(target=self._run_worker, args=(run_config,), daemon=True)
        self.worker_thread.start()

    def _stop(self) -> None:
        self.stop_event.set()
        self.status_var.set("Stopping...")

    def _run_worker(self, run_config: Dict[str, Any]) -> None:
        mode = run_config["mode"]
        self._enqueue_log(f"Starting run mode={mode}")

        try:
            if mode == "image":
                self._run_image(run_config)
            elif mode == "video":
                self._run_video(run_config)
            elif mode == "dataset":
                self._run_dataset(run_config)
            elif mode == "camera":
                self._run_camera(run_config)
            else:
                raise RuntimeError(f"Unknown mode: {mode}")
        except Exception as exc:
            self._enqueue_error(str(exc))
        finally:
            self._enqueue_status("Idle")

    def _run_image(self, cfg: Dict[str, Any]) -> None:
        assert self.backend is not None
        image_path = cfg["image_path"]

        if not image_path:
            raise RuntimeError("No image selected.")
        if not os.path.exists(image_path):
            raise RuntimeError(f"Image file not found: {image_path}")

        frame = cv2.imread(image_path)
        if frame is None:
            raise RuntimeError("Unable to decode image.")

        warmup = cfg["warmup"]
        iterations = cfg["iterations"]

        for _ in range(warmup):
            if self.stop_event.is_set():
                self._enqueue_log("Run interrupted during warmup")
                return
            self._infer_with_color_space(frame)

        samples: List[float] = []
        e2e_samples: List[float] = []
        system_samples: List[Dict[str, float]] = []
        detections_total = 0
        last_result: Optional[InferenceResult] = None

        for idx in range(iterations):
            if self.stop_event.is_set():
                self._enqueue_log("Run interrupted")
                break

            result, e2e_ms = self._infer_with_color_space(frame)
            samples.append(result.latency_ms)
            e2e_samples.append(e2e_ms)
            detections_total += result.detections
            last_result = result

            if (idx + 1) % max(1, iterations // 10) == 0:
                system_samples.append(self._sample_system_metrics())
                self._enqueue_log(f"Progress {idx + 1}/{iterations}")

        stats = compute_stats(samples)
        if stats:
            stats["avg_detections"] = detections_total / max(1, len(samples))
            e2e_stats = compute_stats(e2e_samples)
            if e2e_stats:
                stats["e2e_avg_ms"] = e2e_stats.get("avg_ms", 0.0)
                stats["e2e_p95_ms"] = e2e_stats.get("p95_ms", 0.0)

            system_samples.append(self._sample_system_metrics())
            stats.update(self._aggregate_metrics(system_samples))
            self._enqueue_stats(stats)

        if last_result and last_result.annotated_frame is not None:
            self._enqueue_preview(last_result.annotated_frame)
            self._enqueue_log(f"Last output: {last_result.output_summary}")

    def _run_dataset(self, cfg: Dict[str, Any]) -> None:
        assert self.backend is not None
        dataset_path = cfg["dataset_path"]
        dataset_split = cfg.get("dataset_split", "val")

        if not dataset_path:
            raise RuntimeError("No dataset folder selected.")
        if not os.path.isdir(dataset_path):
            raise RuntimeError(f"Dataset folder not found: {dataset_path}")

        layout = load_yolo_dataset_layout(dataset_path, dataset_split)
        if layout.get("is_yolo"):
            if isinstance(self.backend, (DetectorBackend, OnnxBackend)):
                self._enqueue_log(
                    f"YOLO dataset detected ({layout.get('yaml_path')}); split={dataset_split}. Running evaluation report mode."
                )
                self._run_yolo_dataset_eval(cfg=cfg, layout=layout, dataset_root=dataset_path)
                return

            self._enqueue_log(
                "YOLO dataset detected, but current backend does not expose class-wise detection outputs for YOLO metrics. "
                "Falling back to plain dataset benchmark mode (latency/throughput only)."
            )
            files = list(layout.get("images", []))
        else:
            files = discover_images(dataset_path)

        if not files:
            raise RuntimeError("No supported image files found in dataset folder.")

        warmup = min(cfg["warmup"], len(files))
        self._enqueue_log(f"Dataset files found: {len(files)}")

        for idx in range(warmup):
            if self.stop_event.is_set():
                return
            frame = cv2.imread(files[idx])
            if frame is not None:
                self._infer_with_color_space(frame)

        samples: List[float] = []
        e2e_samples: List[float] = []
        system_samples: List[Dict[str, float]] = []
        detections_total = 0
        processed = 0

        for idx, path in enumerate(files, start=1):
            if self.stop_event.is_set():
                self._enqueue_log("Run interrupted")
                break

            frame = cv2.imread(path)
            if frame is None:
                self._enqueue_log(f"Skipping unreadable file: {path}")
                continue

            result, e2e_ms = self._infer_with_color_space(frame)
            samples.append(result.latency_ms)
            e2e_samples.append(e2e_ms)
            detections_total += result.detections
            processed += 1

            if idx % 8 == 0 and result.annotated_frame is not None:
                self._enqueue_preview(result.annotated_frame)

            if idx % 20 == 0:
                system_samples.append(self._sample_system_metrics())
                self._enqueue_log(f"Processed {idx}/{len(files)}")

        stats = compute_stats(samples)
        if stats:
            stats["dataset_files"] = float(len(files))
            stats["processed_files"] = float(processed)
            stats["avg_detections"] = detections_total / max(1, processed)
            e2e_stats = compute_stats(e2e_samples)
            if e2e_stats:
                stats["e2e_avg_ms"] = e2e_stats.get("avg_ms", 0.0)
                stats["e2e_p95_ms"] = e2e_stats.get("p95_ms", 0.0)

            system_samples.append(self._sample_system_metrics())
            stats.update(self._aggregate_metrics(system_samples))
            self._enqueue_stats(stats)

        self._enqueue_log("Dataset benchmark complete")

    def _run_video(self, cfg: Dict[str, Any]) -> None:
        assert self.backend is not None
        video_path = cfg["video_path"]
        warmup = cfg["warmup"]

        if not video_path:
            raise RuntimeError("No video selected.")
        if not os.path.exists(video_path):
            raise RuntimeError(f"Video file not found: {video_path}")

        suffix = Path(video_path).suffix.lower()
        if suffix and suffix not in VIDEO_EXTENSIONS:
            self._enqueue_log(f"Video extension {suffix} is uncommon; attempting decode anyway.")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open video: {video_path}")

        source_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._enqueue_log(
            f"Video opened: {video_path} | source_fps={source_fps:.2f} | total_frames={total_frames if total_frames > 0 else 'unknown'}"
        )

        samples: List[float] = []
        e2e_samples: List[float] = []
        system_samples: List[Dict[str, float]] = []
        detections_total = 0
        preview_count = 0
        processed = 0

        try:
            warmup_done = 0
            while warmup_done < warmup and not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                self._infer_with_color_space(frame)
                warmup_done += 1

            start = time.perf_counter()
            last_report = start

            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    break

                result, e2e_ms = self._infer_with_color_space(frame)
                processed += 1
                samples.append(result.latency_ms)
                e2e_samples.append(e2e_ms)
                detections_total += result.detections

                if result.annotated_frame is not None and (preview_count % 3 == 0):
                    self._enqueue_preview(result.annotated_frame)
                preview_count += 1

                now = time.perf_counter()
                if now - last_report >= 1.0:
                    elapsed = now - start
                    run_fps = processed / elapsed if elapsed > 0 else 0.0
                    window_stats = compute_stats(samples[-120:])
                    window_e2e = compute_stats(e2e_samples[-120:])
                    sampled = self._sample_system_metrics()
                    system_samples.append(sampled)
                    summary = {
                        "count": float(processed),
                        "stream_fps": run_fps,
                        "avg_ms": window_stats.get("avg_ms", 0.0),
                        "p95_ms": window_stats.get("p95_ms", 0.0),
                        "e2e_avg_ms": window_e2e.get("avg_ms", 0.0),
                        "e2e_p95_ms": window_e2e.get("p95_ms", 0.0),
                        "avg_detections": detections_total / max(1, processed),
                    }
                    summary.update(sampled)
                    self._enqueue_stats(summary)
                    last_report = now

                if processed % 60 == 0:
                    if total_frames > 0:
                        self._enqueue_log(f"Video progress {processed}/{total_frames}")
                    else:
                        self._enqueue_log(f"Video processed {processed} frames")

            final_stats = compute_stats(samples)
            if final_stats:
                final_stats["stream_frames"] = float(processed)
                final_stats["avg_detections"] = detections_total / max(1, processed)
                e2e_final = compute_stats(e2e_samples)
                if e2e_final:
                    final_stats["e2e_avg_ms"] = e2e_final.get("avg_ms", 0.0)
                    final_stats["e2e_p95_ms"] = e2e_final.get("p95_ms", 0.0)

                system_samples.append(self._sample_system_metrics())
                final_stats.update(self._aggregate_metrics(system_samples))
                self._enqueue_stats(final_stats)

            if self.stop_event.is_set():
                self._enqueue_log("Video run stopped")
            else:
                self._enqueue_log("Video run complete")

        finally:
            cap.release()

    def _prediction_class_id(self, class_name: str, class_to_id: Dict[str, int], class_count: int) -> int:
        if class_name in class_to_id:
            return class_to_id[class_name]

        normalized = normalize_class_name(class_name)
        if normalized in class_to_id:
            return class_to_id[normalized]

        if class_name.startswith("class_"):
            try:
                idx = int(class_name.split("_", 1)[1])
                if 0 <= idx < class_count:
                    return idx
            except ValueError:
                pass

        if class_name.isdigit():
            idx = int(class_name)
            if 0 <= idx < class_count:
                return idx

        return -1

    def _run_yolo_dataset_eval(self, cfg: Dict[str, Any], layout: Dict[str, Any], dataset_root: str) -> None:
        assert self.backend is not None
        if not isinstance(self.backend, (DetectorBackend, OnnxBackend)):
            raise RuntimeError(
                "YOLO evaluation report requires parsed detection outputs (.pt/.pth/.hef or supported ONNX detection layout)."
            )

        files = layout.get("images", [])
        if not files:
            raise RuntimeError("No images found for YOLO dataset evaluation.")

        model_info = self.backend.get_model_info()
        class_names = list(layout.get("names", []))
        if not class_names:
            class_names = [str(name) for name in model_info.get("classes", [])]
        if not class_names:
            raise RuntimeError("No class names available. Ensure data.yaml has a valid names list.")

        class_count = len(class_names)
        class_to_id: Dict[str, int] = {}
        for idx, name in enumerate(class_names):
            class_to_id[name] = idx
            class_to_id[normalize_class_name(name)] = idx

        warmup = min(cfg.get("warmup", 0), len(files))
        if warmup > 0:
            self._enqueue_log(f"Warmup on {warmup} images")
            for idx in range(warmup):
                if self.stop_event.is_set():
                    return
                frame = cv2.imread(files[idx])
                if frame is not None:
                    self._infer_with_color_space(frame)

        records: List[Dict[str, Any]] = []
        latencies: List[float] = []
        e2e_samples: List[float] = []
        system_samples: List[Dict[str, float]] = []
        skipped = 0
        unknown_class_pred = 0
        report_every = max(1, len(files) // 20)

        for idx, image_path in enumerate(files, start=1):
            if self.stop_event.is_set():
                self._enqueue_log("YOLO evaluation interrupted")
                break

            frame = cv2.imread(image_path)
            if frame is None:
                skipped += 1
                continue

            image_h, image_w = frame.shape[:2]
            label_path = image_path_to_label_path(image_path)
            gt = parse_yolo_label_file(label_path, image_w=image_w, image_h=image_h, class_count=class_count)

            result, e2e_ms = self._infer_with_color_space(frame)
            latencies.append(result.latency_ms)
            e2e_samples.append(e2e_ms)

            preds_normalized: List[Dict[str, Any]] = []
            for pred in result.predictions or []:
                class_name = str(pred.get("class_name", ""))
                cls_id = self._prediction_class_id(class_name, class_to_id, class_count)
                if cls_id < 0:
                    unknown_class_pred += 1
                    continue

                bbox = pred.get("bbox")
                if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                    continue

                box = clip_box([float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])], image_w=image_w, image_h=image_h)
                conf = float(pred.get("confidence", 0.0))
                preds_normalized.append({"cls": cls_id, "conf": conf, "bbox": box})

            records.append({"gt": gt, "pred": preds_normalized})

            if idx % 8 == 0 and result.annotated_frame is not None:
                self._enqueue_preview(result.annotated_frame)

            if idx % report_every == 0:
                system_samples.append(self._sample_system_metrics())
                self._enqueue_log(f"YOLO eval progress {idx}/{len(files)}")

        if not records:
            raise RuntimeError("No valid images were processed for YOLO evaluation.")

        conf_thresholds = np.linspace(0.0, 1.0, 101)
        precision_curve = np.zeros_like(conf_thresholds)
        recall_curve = np.zeros_like(conf_thresholds)
        f1_curve = np.zeros_like(conf_thresholds)

        for idx, conf_thr in enumerate(conf_thresholds):
            tp, fp, fn = evaluate_confidence_at(records, conf_thr=float(conf_thr), class_count=class_count, iou_thr=0.5)
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = (2.0 * precision * recall) / max(precision + recall, 1e-9)
            precision_curve[idx] = precision
            recall_curve[idx] = recall
            f1_curve[idx] = f1

        best_idx = int(np.argmax(f1_curve))
        best_conf = float(conf_thresholds[best_idx])
        best_precision = float(precision_curve[best_idx])
        best_recall = float(recall_curve[best_idx])
        best_f1 = float(f1_curve[best_idx])

        iou_thresholds = np.arange(0.5, 0.96, 0.05)
        ap_per_iou: List[List[float]] = []
        gt_per_class: List[int] = [0 for _ in range(class_count)]

        for iou_thr in iou_thresholds:
            ap_this_iou: List[float] = []
            for cls_id in range(class_count):
                ap, gt_count = class_ap_for_iou(records, cls_id=cls_id, iou_thr=float(iou_thr))
                if iou_thr == 0.5:
                    gt_per_class[cls_id] = gt_count
                if np.isnan(ap):
                    ap_this_iou.append(float("nan"))
                else:
                    ap_this_iou.append(float(ap))
            ap_per_iou.append(ap_this_iou)

        ap_array = np.asarray(ap_per_iou, dtype=np.float64)
        map50 = float(np.nanmean(ap_array[0])) if ap_array.size else 0.0
        map50_95 = float(np.nanmean(ap_array)) if ap_array.size else 0.0

        ap50_per_class: Dict[str, float] = {}
        if ap_array.size:
            for cls_id, cls_name in enumerate(class_names):
                ap50_per_class[cls_name] = float(ap_array[0, cls_id]) if not np.isnan(ap_array[0, cls_id]) else 0.0

        confusion = compute_confusion_matrix(records, class_count=class_count, conf_thr=best_conf, iou_thr=0.5)
        latency_stats = compute_stats(latencies)
        e2e_stats = compute_stats(e2e_samples)

        report_dir = os.path.join(
            "data",
            "mitt",
            datetime.now().strftime("%Y%m%d_%H%M%S"),
        )

        summary: Dict[str, Any] = {
            "dataset_root": dataset_root,
            "data_yaml": layout.get("yaml_path"),
            "split": cfg.get("dataset_split", "val"),
            "images_total": len(files),
            "images_processed": len(records),
            "images_skipped": skipped,
            "unknown_class_predictions": unknown_class_pred,
            "class_names": class_names,
            "gt_per_class": {class_names[idx]: gt_per_class[idx] for idx in range(class_count)},
            "precision": best_precision,
            "recall": best_recall,
            "f1": best_f1,
            "best_confidence": best_conf,
            "map50": map50,
            "map50_95": map50_95,
            "ap50_per_class": ap50_per_class,
            "latency": latency_stats,
            "latency_e2e": e2e_stats,
        }

        report_files = save_yolo_eval_report(
            report_dir=report_dir,
            class_names=class_names,
            summary=summary,
            conf_thresholds=conf_thresholds,
            precision_curve=precision_curve,
            recall_curve=recall_curve,
            f1_curve=f1_curve,
            confusion_matrix=confusion,
        )

        ui_stats = {
            "dataset_files": float(len(files)),
            "processed_files": float(len(records)),
            "precision": best_precision,
            "recall": best_recall,
            "f1": best_f1,
            "best_conf": best_conf,
            "map50": map50,
            "map50_95": map50_95,
            "avg_ms": latency_stats.get("avg_ms", 0.0),
            "p95_ms": latency_stats.get("p95_ms", 0.0),
            "e2e_avg_ms": e2e_stats.get("avg_ms", 0.0),
            "e2e_p95_ms": e2e_stats.get("p95_ms", 0.0),
            "fps": latency_stats.get("fps", 0.0),
        }
        system_samples.append(self._sample_system_metrics())
        ui_stats.update(self._aggregate_metrics(system_samples))
        self._enqueue_stats(ui_stats)

        self._enqueue_log(f"YOLO evaluation complete. Report directory: {report_dir}")
        self._enqueue_log(f"Summary JSON: {report_files.get('summary_json', 'n/a')}")
        self._enqueue_log(f"PR curve: {report_files.get('pr_curve.png', 'n/a')}")
        self._enqueue_log(f"F1-confidence curve: {report_files.get('f1_conf_curve.png', 'n/a')}")
        self._enqueue_log(f"Confusion matrix: {report_files.get('confusion_matrix.png', 'n/a')}")

    def _open_camera(self, source: str, width: int, height: int, fps: int) -> Any:
        if source == "rpi_camera":
            return PiCamera2Capture(width=width, height=height, fps=fps)

        try:
            index = int(source)
        except ValueError as exc:
            raise RuntimeError("Camera source must be an integer index or 'rpi_camera'.") from exc

        return OpenCVCapture(index=index, width=width, height=height, fps=fps)

    def _run_camera(self, cfg: Dict[str, Any]) -> None:
        assert self.backend is not None
        source = cfg["camera_source"]
        width = cfg["cam_width"]
        height = cfg["cam_height"]
        fps = cfg["cam_fps"]
        warmup = cfg["warmup"]

        camera = self._open_camera(source=source, width=width, height=height, fps=fps)
        self._enqueue_log(f"Camera opened source={source} {width}x{height}@{fps}")

        samples: List[float] = []
        e2e_samples: List[float] = []
        camera_to_detect_samples: List[float] = []
        system_samples: List[Dict[str, float]] = []
        detections_total = 0
        preview_count = 0

        try:
            for _ in range(warmup):
                if self.stop_event.is_set():
                    return
                frame = camera.read()
                if frame is not None:
                    self._infer_with_color_space(frame)

            start = time.perf_counter()
            last_report = start
            frame_count = 0

            while not self.stop_event.is_set():
                capture_start = time.perf_counter()
                frame = camera.read()
                capture_ms = (time.perf_counter() - capture_start) * 1000.0
                if frame is None:
                    continue

                result, e2e_ms = self._infer_with_color_space(frame)
                frame_count += 1
                samples.append(result.latency_ms)
                e2e_samples.append(e2e_ms)
                camera_to_detect_samples.append(capture_ms + e2e_ms)
                detections_total += result.detections

                if result.annotated_frame is not None and (preview_count % 3 == 0):
                    self._enqueue_preview(result.annotated_frame)
                preview_count += 1

                now = time.perf_counter()
                if now - last_report >= 1.0:
                    elapsed = now - start
                    stream_fps = frame_count / elapsed if elapsed > 0 else 0.0
                    window_stats = compute_stats(samples[-120:])
                    window_e2e = compute_stats(e2e_samples[-120:])
                    window_cam_to_det = compute_stats(camera_to_detect_samples[-120:])
                    sampled = self._sample_system_metrics()
                    system_samples.append(sampled)
                    summary = {
                        "count": float(frame_count),
                        "stream_fps": stream_fps,
                        "avg_ms": window_stats.get("avg_ms", 0.0),
                        "p95_ms": window_stats.get("p95_ms", 0.0),
                        "e2e_avg_ms": window_e2e.get("avg_ms", 0.0),
                        "e2e_p95_ms": window_e2e.get("p95_ms", 0.0),
                        "camera_to_detect_avg_ms": window_cam_to_det.get("avg_ms", 0.0),
                        "avg_detections": detections_total / max(1, frame_count),
                    }
                    summary.update(sampled)
                    self._enqueue_stats(summary)
                    last_report = now

            final_stats = compute_stats(samples)
            if final_stats:
                final_stats["stream_frames"] = float(len(samples))
                final_stats["avg_detections"] = detections_total / max(1, len(samples))
                e2e_final = compute_stats(e2e_samples)
                if e2e_final:
                    final_stats["e2e_avg_ms"] = e2e_final.get("avg_ms", 0.0)
                    final_stats["e2e_p95_ms"] = e2e_final.get("p95_ms", 0.0)

                cam_to_det_final = compute_stats(camera_to_detect_samples)
                if cam_to_det_final:
                    final_stats["camera_to_detect_avg_ms"] = cam_to_det_final.get("avg_ms", 0.0)
                    final_stats["camera_to_detect_p95_ms"] = cam_to_det_final.get("p95_ms", 0.0)

                system_samples.append(self._sample_system_metrics())
                final_stats.update(self._aggregate_metrics(system_samples))
                self._enqueue_stats(final_stats)

            self._enqueue_log("Camera run stopped")

        finally:
            camera.release()

    def _enqueue_log(self, message: str) -> None:
        self.ui_queue.put(("log", message))

    def _enqueue_preview(self, frame_bgr: np.ndarray) -> None:
        self.ui_queue.put(("preview", frame_bgr))

    def _enqueue_stats(self, stats: Dict[str, float]) -> None:
        self.ui_queue.put(("stats", stats))

    def _enqueue_status(self, status: str) -> None:
        self.ui_queue.put(("status", status))

    def _enqueue_error(self, message: str) -> None:
        self.ui_queue.put(("error", message))

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()

                if kind == "log":
                    self._log(payload)
                elif kind == "preview":
                    self._render_preview(payload)
                elif kind == "stats":
                    self._update_stats(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "error":
                    self.status_var.set("Error")
                    self._log(f"ERROR: {payload}")
                    messagebox.showerror("Run Error", payload)
        except queue.Empty:
            pass

        self.root.after(60, self._poll_ui_queue)

    def _render_preview(self, frame_bgr: np.ndarray) -> None:
        target_w = 700
        target_h = 430

        h, w = frame_bgr.shape[:2]
        scale = min(target_w / max(w, 1), target_h / max(h, 1))
        resized = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        self.preview_image = ImageTk.PhotoImage(image=image)
        self.preview_label.configure(image=self.preview_image)

        if self.small_screen_mode and self.preview_label_popup is not None:
            popup_w = max(320, min(self.screen_w - 40, 900))
            popup_h = max(220, min(self.screen_h - 80, 620))
            ph, pw = frame_bgr.shape[:2]
            pscale = min(popup_w / max(pw, 1), popup_h / max(ph, 1))
            presized = cv2.resize(frame_bgr, (int(pw * pscale), int(ph * pscale)), interpolation=cv2.INTER_AREA)
            prgb = cv2.cvtColor(presized, cv2.COLOR_BGR2RGB)
            pimage = Image.fromarray(prgb)
            self.preview_image_popup = ImageTk.PhotoImage(image=pimage)
            self.preview_label_popup.configure(image=self.preview_image_popup)

    def _update_stats(self, stats: Dict[str, float]) -> None:
        ordered_keys = [
            "count",
            "dataset_files",
            "processed_files",
            "stream_frames",
            "precision",
            "recall",
            "f1",
            "best_conf",
            "map50",
            "map50_95",
            "avg_ms",
            "min_ms",
            "max_ms",
            "p50_ms",
            "p90_ms",
            "p95_ms",
            "p99_ms",
            "std_ms",
            "e2e_avg_ms",
            "e2e_p95_ms",
            "camera_to_detect_avg_ms",
            "camera_to_detect_p95_ms",
            "fps",
            "stream_fps",
            "avg_detections",
            "cpu_util_pct",
            "hailo_util_pct",
            "temp_c",
            "power_w",
        ]

        lines: List[str] = []
        for key in ordered_keys:
            if key not in stats:
                continue
            value = stats[key]
            if key in {"count", "dataset_files", "processed_files", "stream_frames"}:
                lines.append(f"{key}: {int(value)}")
            else:
                lines.append(f"{key}: {value:.3f}")

        self.stats_var.set("\n".join(lines) if lines else "No statistics yet")

    def _log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{stamp}] {message}\n")
        self.log_text.see(tk.END)

        if self.small_screen_mode and self.log_text_popup is not None:
            self.log_text_popup.insert(tk.END, f"[{stamp}] {message}\n")
            self.log_text_popup.see(tk.END)

    def _on_close(self) -> None:
        self.stop_event.set()

        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.5)

        if self.backend is not None:
            self.backend.close()
            self.backend = None

        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_window.destroy()
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.destroy()

        self.root.destroy()


def main() -> None:
    if HAS_TKDND and TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = InferenceToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
