#!/usr/bin/env python3
"""
Pipeline Benchmark — measure per-stage latency on the Raspberry Pi.

Run from project root:
    cd ~/tcdd-dev
    python backend/bench_pipeline.py

Requires the same venv as the main app.
"""

import os
import sys
import time
import statistics
from pathlib import Path

# ── Project root setup (same as main.py) ────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import cv2
import numpy as np
import base64
import json

from config import Config
from detector import Detector

# Optional fast JPEG encoder
try:
    import simplejpeg
    HAS_SIMPLEJPEG = True
except ImportError:
    HAS_SIMPLEJPEG = False

# Optional picamera2
try:
    from picamera2 import Picamera2
    HAS_PICAMERA = True
except ImportError:
    HAS_PICAMERA = False

# ── Configuration ───────────────────────────────────────────────────────────
config = Config()
CAM_W = int(config.get("camera.width", 640))
CAM_H = int(config.get("camera.height", 480))
CAM_FPS = int(config.get("camera.fps", 30))
JPEG_QUALITY = int(config.get("streaming.quality", 85))
MANUAL_AWB = bool(config.get("camera.manual_awb", False))
N_WARMUP = 10    # frames to discard before measuring
N_FRAMES = 100   # frames to measure

# ── Helpers ─────────────────────────────────────────────────────────────────

def fmt(values):
    """Return 'mean ± stdev  (min / max)' string in ms."""
    if not values:
        return "N/A"
    mn = min(values)
    mx = max(values)
    avg = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{avg:7.2f} ± {sd:5.2f}  (min {mn:.2f} / max {mx:.2f}) ms"


def bench(label, fn, n=N_FRAMES, warmup=N_WARMUP):
    """Benchmark fn() over n calls after warmup calls.  Returns list of ms."""
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    if times:
        effective_fps = 1000.0 / statistics.mean(times) if statistics.mean(times) > 0 else float('inf')
    else:
        effective_fps = 0
    print(f"  {label:36s}  {fmt(times)}   ~{effective_fps:.0f} FPS")
    return times


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. CAMERA CAPTURE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bench_camera():
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  1. Camera Capture                                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    cam = None
    if HAS_PICAMERA:
        try:
            cam = Picamera2()
            cam_cfg = cam.create_preview_configuration(
                main={"size": (CAM_W, CAM_H), "format": "RGB888"},
                buffer_count=4,
            )
            cam.configure(cam_cfg)
            frame_dur = int(1_000_000 / CAM_FPS)
            cam.set_controls({"AwbEnable": True, "AwbMode": 0,
                              "FrameDurationLimits": (frame_dur, frame_dur)})
            cam.start()
            time.sleep(1.0)

            def grab_picam():
                return cam.capture_array()

            bench("capture_array (PiCamera2 RGB888)", grab_picam)

            # Measure cvtColor separately
            rgb_frame = cam.capture_array()

            def cvt_rgb2bgr():
                return cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

            bench("cvtColor RGB→BGR", cvt_rgb2bgr)

            # Combined
            def grab_and_cvt():
                f = cam.capture_array()
                return cv2.cvtColor(f, cv2.COLOR_RGB2BGR)

            bench("capture + cvtColor (combined)", grab_and_cvt)

            # Grab a BGR frame for later stages
            bgr_frame = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)

            cam.stop()
            cam.close()
            return bgr_frame

        except Exception as e:
            print(f"  PiCamera2 failed: {e}")
            if cam:
                try: cam.stop(); cam.close()
                except: pass

    # Fallback: USB / OpenCV camera
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2 if os.name != "nt" else cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    cap.set(cv2.CAP_PROP_FPS, CAM_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        print("  No camera available — using synthetic frame")
        return np.random.randint(0, 255, (CAM_H, CAM_W, 3), dtype=np.uint8)

    for _ in range(5):
        cap.read()

    def grab_cv2():
        ret, f = cap.read()
        return f

    bench("VideoCapture.read (USB/cv2)", grab_cv2)
    _, bgr_frame = cap.read()
    cap.release()
    return bgr_frame


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. INFERENCE  (Hailo / NCNN / Ultralytics)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bench_inference(bgr_frame):
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  2. Inference (detect + NMS)                                ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    det = Detector(config)
    engine = config.get("detection.engine", "?")
    print(f"  Engine: {engine}  |  Model: {config.get('detection.model_files', '?')}")
    print(f"  Input frame: {bgr_frame.shape[1]}x{bgr_frame.shape[0]} BGR")

    # Sub-bench: resize only
    input_size = det.input_size  # (640, 640)

    def resize_only():
        return cv2.resize(bgr_frame, input_size, interpolation=cv2.INTER_LINEAR)

    bench(f"cv2.resize → {input_size}", resize_only)

    # Full detect (resize + send + recv + parse)
    def full_detect():
        return det.detect(bgr_frame)

    times = bench("detector.detect (full)", full_detect)

    # Grab one set of detections for later stages
    detections = det.detect(bgr_frame)
    return det, detections, times


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. DRAW DETECTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bench_draw(det, bgr_frame, detections):
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  3. Draw Detections                                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Detections to draw: {len(detections)}")

    def draw():
        return det.draw_detections(bgr_frame, detections)

    bench("draw_detections (with frame.copy)", draw)

    annotated = det.draw_detections(bgr_frame, detections)
    return annotated


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. JPEG ENCODING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bench_jpeg(annotated):
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  4. JPEG Encoding                                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Frame: {annotated.shape[1]}x{annotated.shape[0]}  quality={JPEG_QUALITY}")

    params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]

    def encode_cv2():
        _, buf = cv2.imencode(".jpg", annotated, params)
        return buf.tobytes()

    times_cv2 = bench("cv2.imencode", encode_cv2)
    jpeg_bytes_cv2 = encode_cv2()

    jpeg_bytes = jpeg_bytes_cv2
    if HAS_SIMPLEJPEG:
        def encode_sj():
            return simplejpeg.encode_jpeg(annotated, quality=JPEG_QUALITY, colorspace="BGR")

        times_sj = bench("simplejpeg.encode_jpeg", encode_sj)
        jpeg_bytes = encode_sj()
    else:
        print("  simplejpeg not installed — skipped")

    print(f"  JPEG size: {len(jpeg_bytes) / 1024:.1f} KB")
    return jpeg_bytes


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. BASE64 + WEBSOCKET SERIALIZATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bench_serialization(jpeg_bytes, detections):
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  5. Serialization (base64 + JSON)                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  JPEG payload: {len(jpeg_bytes) / 1024:.1f} KB  |  Detections: {len(detections)}")

    # base64 encode
    def b64_encode():
        return base64.b64encode(jpeg_bytes).decode("utf-8")

    bench("base64.b64encode + decode", b64_encode)
    b64_str = b64_encode()

    # Build the payload dict (what socketio.emit receives)
    det_list = [
        {"class_name": d["class_name"], "confidence": float(d["confidence"]), "bbox": d["bbox"]}
        for d in detections
    ]

    def build_payload_b64():
        return {
            "frame": b64_str,
            "detections": det_list,
            "count": len(det_list),
        }

    bench("build payload dict (base64 path)", build_payload_b64)

    # Measure json.dumps of the full payload (this is what SocketIO does internally)
    payload = build_payload_b64()

    def json_dumps():
        return json.dumps(payload)

    times_json = bench("json.dumps (full payload)", json_dumps)
    json_str = json_dumps()
    print(f"  JSON payload size: {len(json_str) / 1024:.1f} KB")

    # Binary path comparison (no base64, no JSON for the frame bytes)
    def build_payload_binary():
        return {
            "frame": jpeg_bytes,  # raw bytes — SocketIO sends as binary attachment
            "detections": det_list,
            "count": len(det_list),
        }

    bench("build payload dict (binary path)", build_payload_binary)

    payload_bin = build_payload_binary()
    # SocketIO binary: JSON part is only the small metadata dict
    meta_only = {"detections": det_list, "count": len(det_list)}

    def json_dumps_meta():
        return json.dumps(meta_only)

    bench("json.dumps (metadata only, binary)", json_dumps_meta)
    meta_json = json_dumps_meta()
    print(f"  Binary meta JSON size: {len(meta_json) / 1024:.1f} KB  (frame sent as binary attachment)")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. END-TO-END PIPELINE (simulated — no actual socket)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def bench_e2e(cam_grab_fn, det_obj):
    """Measure full pipeline: grab → detect → draw → encode → base64."""
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  6. End-to-End Pipeline (no socket emit)                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    use_sj = HAS_SIMPLEJPEG

    def pipeline_b64():
        frame = cam_grab_fn()
        dets = det_obj.detect(frame)
        ann = det_obj.draw_detections(frame, dets)
        if use_sj:
            jbytes = simplejpeg.encode_jpeg(ann, quality=JPEG_QUALITY, colorspace="BGR")
        else:
            _, buf = cv2.imencode(".jpg", ann, params)
            jbytes = buf.tobytes()
        b64 = base64.b64encode(jbytes).decode("utf-8")
        return b64

    def pipeline_binary():
        frame = cam_grab_fn()
        dets = det_obj.detect(frame)
        ann = det_obj.draw_detections(frame, dets)
        if use_sj:
            jbytes = simplejpeg.encode_jpeg(ann, quality=JPEG_QUALITY, colorspace="BGR")
        else:
            _, buf = cv2.imencode(".jpg", ann, params)
            jbytes = buf.tobytes()
        return jbytes  # no base64

    bench("full pipeline (base64 path)", pipeline_b64)
    bench("full pipeline (binary path)", pipeline_binary)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("=" * 64)
    print("  TCDD Pipeline Benchmark")
    print("=" * 64)
    print(f"  Camera:  {CAM_W}x{CAM_H} @ {CAM_FPS} FPS")
    print(f"  Engine:  {config.get('detection.engine', '?')}")
    print(f"  JPEG:    quality={JPEG_QUALITY}  simplejpeg={'yes' if HAS_SIMPLEJPEG else 'NO'}")
    print(f"  AWB:     {'manual (CPU)' if MANUAL_AWB else 'hardware'}")
    print(f"  Warmup:  {N_WARMUP} frames  |  Measure: {N_FRAMES} frames")
    print("=" * 64)

    # 1. Camera
    bgr_frame = bench_camera()

    # 2. Inference
    det_obj, detections, _ = bench_inference(bgr_frame)

    # 3. Draw
    annotated = bench_draw(det_obj, bgr_frame, detections)

    # 4. JPEG
    jpeg_bytes = bench_jpeg(annotated)

    # 5. Serialization
    bench_serialization(jpeg_bytes, detections)

    # 6. E2E — need a live camera grab function
    cam = None
    cam_grab_fn = None
    if HAS_PICAMERA:
        try:
            cam = Picamera2()
            cam_cfg = cam.create_preview_configuration(
                main={"size": (CAM_W, CAM_H), "format": "RGB888"},
                buffer_count=4,
            )
            cam.configure(cam_cfg)
            frame_dur = int(1_000_000 / CAM_FPS)
            cam.set_controls({"AwbEnable": True, "AwbMode": 0,
                              "FrameDurationLimits": (frame_dur, frame_dur)})
            cam.start()
            time.sleep(1.0)
            def grab():
                f = cam.capture_array()
                return cv2.cvtColor(f, cv2.COLOR_RGB2BGR)
            cam_grab_fn = grab
        except Exception as e:
            print(f"  PiCamera2 unavailable for E2E: {e}")

    if cam_grab_fn is None:
        # fallback: reuse static frame
        print("  (Using static frame for E2E — camera timing not included)")
        static = bgr_frame.copy()
        cam_grab_fn = lambda: static

    bench_e2e(cam_grab_fn, det_obj)

    if cam:
        try: cam.stop(); cam.close()
        except: pass

    print("\n" + "=" * 64)
    print("  Benchmark complete.")
    print("=" * 64)


if __name__ == "__main__":
    main()
