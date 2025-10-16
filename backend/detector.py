#!/usr/bin/env python3
"""
Sign Detector - YOLO Detection Engine
Handles sign detection using YOLOv8
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


class Detector:
    """YOLO-based sign detector"""
    
    def __init__(self, config):
        """
        Initialize detector
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.model = None
        self.loaded = False
        
        # Detection settings
        self.model_path = config.get('detection.model', 'backend/models/yolov8n.pt')
        self.confidence = config.get('detection.confidence', 0.5)
        
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model"""
        try:
            if not HAS_YOLO:
                logger.warning("YOLO not available - using mock detector")
                self.loaded = False
                return
            
            logger.info(f"Loading YOLO model from {self.model_path}...")
            
            # Check if model exists
            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found: {self.model_path}")
                logger.info("YOLO will download default model on first run")
            
            # Load model
            self.model = YOLO(self.model_path)
            
            # Warm up model with dummy input
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy_frame, conf=self.confidence, verbose=False)
            
            self.loaded = True
            logger.info(f"Model loaded successfully! Classes: {len(self.model.names)}")
            logger.info(f"Model classes: {list(self.model.names.values())}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
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
        
        try:
            if not self.loaded or not HAS_YOLO:
                return self._mock_detect(frame)
            
            # Run inference
            results = self.model(
                frame,
                conf=self.confidence,
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
                        
                        detections.append({
                            'class_name': self.model.names[cls],
                            'confidence': conf,
                            'bbox': [int(x) for x in xyxy]  # [x1, y1, x2, y2]
                        })
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def _mock_detect(self, frame):
        """
        Mock detector for testing without YOLO
        Returns dummy detections
        """
        # Occasionally return a mock detection
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
            'model': self.model_path,
            'loaded': self.loaded,
            'confidence_threshold': self.confidence,
            'classes': list(self.model.names.values()) if self.loaded and self.model else []
        }
