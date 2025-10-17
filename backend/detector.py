#!/usr/bin/env python3
"""
Sign Detector - Detection Engine
Handles sign detection using Ultralytics YOLOv8 or NCNN
"""

import logging
import numpy as np
import cv2
import os

logger = logging.getLogger(__name__)

# Try importing YOLO
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning("ultralytics not available, using mock detector")

# Try importing NCNN
try:
    import ncnn
    HAS_NCNN = True
except ImportError:
    HAS_NCNN = False
    logger.warning("ncnn not available, NCNN engine will not work")


class Detector:
    """Sign detector supporting Ultralytics YOLOv8 and NCNN"""
    
    def __init__(self, config):
        """
        Initialize detector
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.engine = config.get('detection.engine', 'ultralytics')
        self.model = None
        self.loaded = False
        self.labels = self._load_labels(config.get('detection.labels', 'backend/models/labels.txt'))
        self.confidence = self._get_confidence()
        self.iou_threshold = self._get_iou_threshold()
        self.model_path = config.get('detection.model', 'backend/models/best.pt')
        self.ncnn_param = config.get('detection.ncnn_param', 'backend/models/model.ncnn.param')
        self.ncnn_bin = config.get('detection.ncnn_bin', 'backend/models/model.ncnn.bin')
        self.input_size = (config.get('camera.width', 640), config.get('camera.height', 480))
        self._load_model()
    
    def _get_confidence(self):
        # Per-engine override, fallback to global
        if self.engine == 'ncnn':
            return self.config.get('detection.ncnn.confidence', self.config.get('detection.confidence', 0.5))
        else:
            return self.config.get('detection.ultralytics.confidence', self.config.get('detection.confidence', 0.5))

    def _get_iou_threshold(self):
        if self.engine == 'ncnn':
            return self.config.get('detection.ncnn.iou_threshold', self.config.get('detection.iou_threshold', 0.45))
        else:
            return self.config.get('detection.ultralytics.iou_threshold', self.config.get('detection.iou_threshold', 0.45))

    def _load_labels(self, labels_path):
        if not os.path.exists(labels_path):
            logger.warning(f"Labels file not found: {labels_path}")
            return None
        with open(labels_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def _load_model(self):
        if self.engine == 'ultralytics':
            if not HAS_YOLO:
                logger.warning("Ultralytics not available - using mock detector")
                self.loaded = False
                return
            logger.info(f"Loading Ultralytics YOLO model from {self.model_path}...")
            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found: {self.model_path}")
                logger.info("YOLO will download default model on first run")
            self.model = YOLO(self.model_path)
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy_frame, conf=self.confidence, verbose=False)
            self.loaded = True
            logger.info(f"Model loaded successfully! Classes: {len(self.model.names)}")
        elif self.engine == 'ncnn':
            if not HAS_NCNN:
                logger.warning("NCNN not available - using mock detector")
                self.loaded = False
                return
            logger.info(f"Loading NCNN model: {self.ncnn_param}, {self.ncnn_bin}")
            self.net = ncnn.Net()
            self.net.load_param(self.ncnn_param)
            self.net.load_model(self.ncnn_bin)
            self.loaded = True
            logger.info("NCNN model loaded successfully!")
        else:
            logger.warning(f"Unknown detection engine: {self.engine}")
            self.loaded = False
    
    def detect(self, frame):
        """
        Run detection on frame
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            list: List of detections, each containing:
                - class_name: Detected class name
                - confidence: Detection confidence (0-1)
                - bbox: Bounding box [x1, y1, x2, y2]
        """
        if frame is None:
            return []
        
        if not self.loaded:
            return self._mock_detect(frame)
        
        if self.engine == 'ultralytics':
            return self._detect_ultralytics(frame)
        elif self.engine == 'ncnn':
            return self._detect_ncnn(frame)
        else:
            return self._mock_detect(frame)
    
    def _detect_ultralytics(self, frame):
        try:
            results = self.model(
                frame,
                conf=self.confidence,
                iou=self.iou_threshold,
                verbose=False
            )
            detections = []
            
            if results and len(results) > 0:
                boxes = results[0].boxes
                
                if boxes is not None and len(boxes) > 0:
                    # Extract detections
                    for box in boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names[cls] if self.model and hasattr(self.model, 'names') else str(cls)
                        
                        detections.append({
                            'class_name': class_name,
                            'confidence': conf,
                            'bbox': [int(x) for x in xyxy]  # [x1, y1, x2, y2]
                        })
            
            return detections
        
        except Exception as e:
            logger.error(f"Ultralytics detection error: {e}")
            return []
    
    def _detect_ncnn(self, frame):
        try:
            # Preprocess: resize, normalize, convert to RGB
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, self.input_size)
            img = img.astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))  # HWC to CHW
            img = np.expand_dims(img, 0)  # Add batch dim
            img = np.ascontiguousarray(img)
            
            # NCNN expects ncnn.Mat
            ncnn_img = ncnn.Mat(img)
            ex = self.net.create_extractor()
            ex.input("input", ncnn_img)
            out = ex.extract("output")
            
            # Postprocess: parse output (assume YOLOv8 format)
            # This part may need adjustment for your model's output
            detections = []
            
            for i in range(out.h):
                row = out.row(i)
                conf = float(row[4])
                
                if conf < self.confidence:
                    continue
                
                x1, y1, x2, y2 = [int(row[j]) for j in range(0, 4)]
                cls = int(row[5]) if len(row) > 5 else 0
                class_name = self.labels[cls] if self.labels and cls < len(self.labels) else str(cls)
                
                detections.append({
                    'class_name': class_name,
                    'confidence': conf,
                    'bbox': [x1, y1, x2, y2]
                })
            
            return detections
        
        except Exception as e:
            logger.error(f"NCNN detection error: {e}")
            return []
    
    def _mock_detect(self, frame):
        """
        Mock detector for testing without YOLO or NCNN
        Returns dummy detections
        """
        import random
        
        if random.random() > 0.7:  # 30% chance
            h, w = frame.shape[:2]
            return [{
                'class_name': 'mock_sign',
                'confidence': random.uniform(0.6, 0.95),
                'bbox': [
                    int(w * 0.3),
                    int(h * 0.3),
                    int(w * 0.7),
                    int(h * 0.7)
                ]
            }]
        
        return []
    
    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Input frame
            detections: List of detections from detect()
            
        Returns:
            numpy.ndarray: Annotated frame
        """
        if not detections:
            return frame
        
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = det['class_name']
            conf = det['confidence']
            
            # Choose color based on confidence
            color = (0, 255, 0) if conf > 0.7 else (0, 255, 255)  # Green or Yellow
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            text = f"{label} {conf:.0%}"
            (text_w, text_h), baseline = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            
            cv2.rectangle(
                annotated,
                (x1, y1 - text_h - baseline - 5),
                (x1 + text_w + 5, y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                text,
                (x1 + 2, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )
        
        return annotated
    
    def is_loaded(self):
        """Check if model is loaded"""
        return self.loaded
    
    def get_info(self):
        """Get detector information"""
        return {
            'engine': self.engine,
            'model': self.model_path if self.engine == 'ultralytics' else self.ncnn_param,
            'loaded': self.loaded,
            'confidence_threshold': self.confidence,
            'classes': self.labels if self.labels else []
        }
