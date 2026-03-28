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
    # Allowlist Ultralytics model class for safe unpickling in PyTorch 2.6+
    try:
        from torch.serialization import add_safe_globals
        from ultralytics.nn.tasks import DetectionModel
        add_safe_globals([DetectionModel])
    except Exception:
        pass
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

# Try importing Hailo Platform
try:
    from hailo_platform import (
        HEF, VDevice, HailoStreamInterface,
        ConfigureParams,
        InputVStreams, OutputVStreams,
        InputVStreamParams, OutputVStreamParams
    )
    HAS_HAILO = True
except ImportError:
    HAS_HAILO = False
    logger.warning("hailo_platform not available, HEF engine will not work")


class Detector:
    """Sign detector supporting Ultralytics YOLOv8 and NCNN"""
    
    def __init__(self, config):
        """
        Initialize detector
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.engine = config.get('detection.engine', 'pytorch')
        self.device = config.get('detection.device', 'cpu')
        self.model = None
        self.net = None
        self.loaded = False
        
        # Hailo-specific state
        self.hailo_device = None
        self.hailo_hef = None
        self.hailo_network_group = None
        self.hailo_network_group_context = None
        self._hailo_activation_ctx = None
        self._input_vstreams_ctx = None
        self._output_vstreams_ctx = None
        self._input_vstreams = None
        self._output_vstreams = None
        self._hailo_input_vstream = None
        self._hailo_input_names = []
        
        # Parse model path(s) based on engine
        model_config = config.get('detection.model_files', [])
        if not isinstance(model_config, list):
            model_config = [model_config]  # Convert to list for backward compatibility
        
        if self.engine == 'ncnn':
            if len(model_config) < 2:
                raise ValueError("NCNN engine requires 2 model files: [param_path, bin_path]")
            self.ncnn_param = model_config[0]
            self.ncnn_bin = model_config[1]
            self.model_path = None
            logger.info(f"NCNN model configured: param={self.ncnn_param}, bin={self.ncnn_bin}")
        elif self.engine == 'hef':
            if len(model_config) < 1:
                raise ValueError("HEF engine requires 1 model file: [hef_path]")
            self.model_path = model_config[0]
            self.ncnn_param = None
            self.ncnn_bin = None
            logger.info(f"HEF model configured: {self.model_path} (device={self.device})")
        else:  # ultralytics
            if len(model_config) < 1:
                self.model_path = 'backend/models/best.pt'  # Default fallback
            else:
                self.model_path = model_config[0]
            self.ncnn_param = None
            self.ncnn_bin = None
            logger.info(f"Ultralytics model configured: {self.model_path}")
        
        self.labels = self._load_labels(config.get('detection.labels', 'backend/models/labels.txt'))
        self.confidence = config.get('detection.confidence', 0.5)
        self.iou_threshold = config.get('detection.iou_threshold', 0.45)
        self.input_size = (640, 640)  # Standard YOLO input size
        
        self._load_model()
    
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
            
            try:
                if not os.path.exists(self.model_path):
                    logger.warning(f"Model file not found: {self.model_path}")
                    logger.info("Loading default YOLOv8n model...")
                    self.model = YOLO('yolov8n.pt')
                else:
                    self.model = YOLO(self.model_path)
                
                # Warmup inference
                dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
                _ = self.model(dummy_frame, conf=self.confidence, verbose=False)
                
                self.loaded = True
                logger.info(f"Ultralytics model loaded. Classes: {len(self.model.names)}")
                
            except Exception as e:
                logger.error(f"Failed to load Ultralytics model: {e}")
                self.loaded = False
                
        elif self.engine == 'ncnn':
            if not HAS_NCNN:
                logger.error("NCNN not available - using mock detector")
                logger.error("Please install ncnn: python -m pip install ncnn")
                self.loaded = False
                return
            
            logger.info(f"Loading NCNN model: param={self.ncnn_param}, bin={self.ncnn_bin}")
            logger.debug(f"Confidence threshold: {self.confidence}, IOU threshold: {self.iou_threshold}")
            
            try:
                if not os.path.exists(self.ncnn_param):
                    raise FileNotFoundError(f"NCNN param file not found: {self.ncnn_param}")
                if not os.path.exists(self.ncnn_bin):
                    raise FileNotFoundError(f"NCNN bin file not found: {self.ncnn_bin}")
                
                self.net = ncnn.Net()
                ret_param = self.net.load_param(self.ncnn_param)
                ret_model = self.net.load_model(self.ncnn_bin)
                
                if ret_param != 0 or ret_model != 0:
                    raise RuntimeError(f"Failed to load NCNN model (param={ret_param}, model={ret_model})")
                
                self.loaded = True
                logger.info("NCNN model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load NCNN model: {e}")
                self.loaded = False
                
        elif self.engine == 'hef':
            self._load_hailo_model()
        else:
            logger.warning(f"Unknown detection engine: {self.engine}")
            self.loaded = False
    
    def _load_hailo_model(self):
        """Load HEF model onto Hailo AI HAT+ NPU"""
        if not HAS_HAILO:
            logger.error("\u274c hailo_platform not available - using mock detector")
            logger.error("Please install hailo-all on your Raspberry Pi")
            self.loaded = False
            return
        
        if self.device != 'hailo':
            logger.error(f"\u274c HEF engine requires device=hailo, got device={self.device}")
            self.loaded = False
            return
        
        logger.info(f"Loading HEF model: {self.model_path}")
        
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"HEF model file not found: {self.model_path}")
            
            # Create virtual device (connects to Hailo NPU)
            self.hailo_device = VDevice()
            
            # Load HEF file
            self.hailo_hef = HEF(self.model_path)
            
            # Configure network on the device
            configure_params = ConfigureParams.create_from_hef(
                self.hailo_hef,
                interface=HailoStreamInterface.PCIe
            )
            network_groups = self.hailo_device.configure(self.hailo_hef, configure_params)
            self.hailo_network_group = network_groups[0]
            
            # Create vstream params
            input_params = InputVStreamParams.make(self.hailo_network_group)
            output_params = OutputVStreamParams.make(self.hailo_network_group)
            self._hailo_input_names = list(input_params.keys())
            
            # Create persistent InputVStreams and OutputVStreams
            # NOTE: We use send/recv API instead of InferVStreams.infer() because
            # the latter passes input data as Python dict → C++ std::map<string, py::array>
            # which can produce 0-byte MemoryView on aarch64/pybind11 ("got 0" error).
            # send/recv passes py::array directly, avoiding the dict→map conversion.
            self._input_vstreams_ctx = InputVStreams(
                self.hailo_network_group, input_params)
            self._output_vstreams_ctx = OutputVStreams(
                self.hailo_network_group, output_params)
            self._input_vstreams = self._input_vstreams_ctx.__enter__()
            self._output_vstreams = self._output_vstreams_ctx.__enter__()
            
            # Activate network group AFTER vstreams are created
            self._hailo_activation_ctx = self.hailo_network_group.activate()
            self.hailo_network_group_context = self._hailo_activation_ctx.__enter__()
            
            # Cache the input vstream object for fast per-frame access
            self._hailo_input_vstream = self._input_vstreams.get(
                self._hailo_input_names[0])
            
            self.loaded = True
            logger.info("\u2705 HEF model loaded on Hailo NPU!")
            logger.info(f"\u26a1 Running on Hailo AI HAT+ (device={self.device})")
            logger.info(f"   Input stream(s): {self._hailo_input_names}")
            
        except Exception as e:
            logger.error(f"\u274c Failed to load HEF model: {e}")
            self.loaded = False
            self._cleanup_hailo()
    
    def _cleanup_hailo(self):
        """Release Hailo resources in reverse order of creation"""
        try:
            # 1. Deactivate network group (must deactivate before destroying vstreams)
            if self._hailo_activation_ctx is not None:
                try:
                    self._hailo_activation_ctx.__exit__(None, None, None)
                except Exception:
                    pass
                self._hailo_activation_ctx = None
            self.hailo_network_group_context = None
            
            # 2. Release output vstreams
            if self._output_vstreams_ctx is not None:
                try:
                    self._output_vstreams_ctx.__exit__(None, None, None)
                except Exception:
                    pass
                self._output_vstreams_ctx = None
                self._output_vstreams = None
            
            # 3. Release input vstreams
            if self._input_vstreams_ctx is not None:
                try:
                    self._input_vstreams_ctx.__exit__(None, None, None)
                except Exception:
                    pass
                self._input_vstreams_ctx = None
                self._input_vstreams = None
            self._hailo_input_vstream = None
            
            # 4. Release network group, HEF, device
            self.hailo_network_group = None
            self.hailo_hef = None
            if self.hailo_device is not None:
                self.hailo_device.release()
                self.hailo_device = None
        except Exception as e:
            logger.warning(f"Error during Hailo cleanup: {e}")
    
    def detect(self, frame):
        """
        Run detection on frame
        Args:
            frame: Input frame (RGB format for NCNN)
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
        elif self.engine == 'hef':
            return self._detect_hailo(frame)
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
                    for box in boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names[cls] if self.model and hasattr(self.model, 'names') else str(cls)
                        
                        detections.append({
                            'class_name': class_name,
                            'confidence': conf,
                            'bbox': [int(x) for x in xyxy]
                        })
            
            return detections
        
        except Exception as e:
            logger.error(f"Ultralytics detection error: {e}")
            return []
    
    def _detect_ncnn(self, frame):
        try:
            h, w = frame.shape[:2]
            logger.debug(f"Processing frame: {w}x{h}")
            
            # Preprocess: resize to model input size
            img = cv2.resize(frame, self.input_size)
            # Create NCNN Mat from numpy array (use RGB format directly)
            mat_in = ncnn.Mat.from_pixels(img, ncnn.Mat.PixelType.PIXEL_RGB, self.input_size[0], self.input_size[1])
            
            # Normalize to [0, 1] (standard YOLO preprocessing)
            mean_vals = [0.0, 0.0, 0.0]
            norm_vals = [1/255.0, 1/255.0, 1/255.0]
            mat_in.substract_mean_normalize(mean_vals, norm_vals)
            
            # Run inference
            ex = self.net.create_extractor()
            ex.input("in0", mat_in)  # YOLOv8 NCNN typically uses "in0" as input name
            
            ret, mat_out = ex.extract("out0")  # YOLOv8 NCNN typically uses "out0" as output name
            
            if ret != 0:
                logger.error(f"NCNN extraction failed with code {ret}")
                return []
            
            logger.debug(f"NCNN output shape: h={mat_out.h}, w={mat_out.w}, c={mat_out.c}")
            
            # Parse YOLO output format
            # For YOLOv8 NCNN: output shape is typically (84, 8400) or (num_classes+4, num_predictions)
            # Each column: [x_center, y_center, width, height, class0_conf, class1_conf, ...]
            
            detections = []
            num_classes = len(self.labels) if self.labels else 80
            
            # Convert NCNN Mat to numpy array for easier processing
            import numpy as np
            
            # NCNN Mat format: try different interpretations based on output shape
            if mat_out.w > mat_out.h:
                # Format: (num_classes+4, num_predictions) - typical YOLOv8 NCNN output
                num_predictions = mat_out.w
                num_features = mat_out.h
                logger.debug(f"Detected YOLOv8 format: {num_features} features x {num_predictions} predictions")
                
                # Process each prediction (column)
                for i in range(num_predictions):
                    # Extract bbox coordinates
                    x_center = mat_out[0 * mat_out.w + i]
                    y_center = mat_out[1 * mat_out.w + i]
                    width = mat_out[2 * mat_out.w + i]
                    height = mat_out[3 * mat_out.w + i]
                    
                    # Find class with highest confidence
                    max_conf = 0.0
                    max_class = 0
                    
                    for c in range(num_classes):
                        conf = mat_out[(4 + c) * mat_out.w + i]
                        if conf > max_conf:
                            max_conf = conf
                            max_class = c
                    
                    if max_conf < self.confidence:
                        continue
                    
                    # Convert from center format to corner format and scale to original image size
                    scale_x = w / self.input_size[0]
                    scale_y = h / self.input_size[1]
                    
                    x1 = int((x_center - width / 2) * scale_x)
                    y1 = int((y_center - height / 2) * scale_y)
                    x2 = int((x_center + width / 2) * scale_x)
                    y2 = int((y_center + height / 2) * scale_y)
                    
                    # Clip to image boundaries
                    x1 = max(0, min(x1, w))
                    y1 = max(0, min(y1, h))
                    x2 = max(0, min(x2, w))
                    y2 = max(0, min(y2, h))
                    
                    class_name = self.labels[max_class] if self.labels and max_class < len(self.labels) else str(max_class)
                    
                    logger.debug(f"Detection: {class_name} ({max_conf:.3f}) at [{x1}, {y1}, {x2}, {y2}]")
                    
                    detections.append({
                        'class_name': class_name,
                        'confidence': float(max_conf),
                        'bbox': [x1, y1, x2, y2]
                    })
            else:
                # Format: (num_predictions, num_classes+4) - row-based format
                num_predictions = mat_out.h
                logger.debug(f"Detected row-based format: {num_predictions} predictions")
                
                for i in range(num_predictions):
                    # Get the detection data
                    x_center = mat_out[i * mat_out.w + 0]
                    y_center = mat_out[i * mat_out.w + 1]
                    width = mat_out[i * mat_out.w + 2]
                    height = mat_out[i * mat_out.w + 3]
                    
                    # Find class with highest confidence
                    max_conf = 0.0
                    max_class = 0
                    
                    for c in range(num_classes):
                        conf = mat_out[i * mat_out.w + 4 + c]
                        if conf > max_conf:
                            max_conf = conf
                            max_class = c
                    
                    if max_conf < self.confidence:
                        continue
                    
                    # Convert from center format to corner format and scale to original image size
                    scale_x = w / self.input_size[0]
                    scale_y = h / self.input_size[1]
                    
                    x1 = int((x_center - width / 2) * scale_x)
                    y1 = int((y_center - height / 2) * scale_y)
                    x2 = int((x_center + width / 2) * scale_x)
                    y2 = int((y_center + height / 2) * scale_y)
                    
                    # Clip to image boundaries
                    x1 = max(0, min(x1, w))
                    y1 = max(0, min(y1, h))
                    x2 = max(0, min(x2, w))
                    y2 = max(0, min(y2, h))
                    
                    class_name = self.labels[max_class] if self.labels and max_class < len(self.labels) else str(max_class)
                    
                    logger.debug(f"Detection: {class_name} ({max_conf:.3f}) at [{x1}, {y1}, {x2}, {y2}]")
                    
                    detections.append({
                        'class_name': class_name,
                        'confidence': float(max_conf),
                        'bbox': [x1, y1, x2, y2]
                    })
            
            logger.debug(f"Found {len(detections)} detections above confidence threshold {self.confidence}")
            
            # Apply NMS to remove overlapping detections (add this BEFORE return)
            if len(detections) > 1:
                detections = self._apply_nms(detections, self.iou_threshold)
                logger.debug(f"After NMS: {len(detections)} detections remaining")

            return detections
        
        except Exception as e:
            logger.error(f"NCNN detection error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _apply_nms(self, detections, iou_threshold):
        """
        Apply Non-Maximum Suppression to remove overlapping detections
        
        Args:
            detections: List of detection dicts with 'bbox' and 'confidence'
            iou_threshold: IOU threshold for considering boxes as duplicates
            
        Returns:
            Filtered list of detections after NMS
        """
        if len(detections) == 0:
            return detections
        
        # Extract boxes and scores
        boxes = np.array([d['bbox'] for d in detections])  # [[x1, y1, x2, y2], ...]
        scores = np.array([d['confidence'] for d in detections])
        
        # Calculate areas
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        
        # Sort by confidence (descending)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            # Pick detection with highest confidence
            i = order[0]
            keep.append(i)
            
            # Calculate IOU with remaining boxes
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            # Keep only boxes with IOU less than threshold
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        # Return filtered detections
        return [detections[i] for i in keep]    

    def _mock_detect(self, frame):
        """Mock detector for testing without YOLO or NCNN"""
        import random
        
        if random.random() > 0.7:
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
    
    def _detect_hailo(self, frame):
        """Run YOLO inference on Hailo AI HAT+ NPU via HEF model.
        
        Uses InputVStream.send() / OutputVStream.recv() instead of
        InferVStreams.infer() to avoid the Python dict → C++ std::map<string,
        py::array> conversion that causes 0-byte MemoryView on aarch64.
        """
        try:
            frame_h, frame_w = frame.shape[:2]
            
            # Preprocess: resize to 640x640
            resized = cv2.resize(frame, self.input_size, interpolation=cv2.INTER_LINEAR)
            
            # Camera pipeline now delivers BGR directly — no conversion needed.
            # HEF models have quantization built-in: send uint8 [0-255] directly.
            # Ensure C-contiguous array so Hailo C library can read the buffer.
            input_frame = np.ascontiguousarray(resized, dtype=np.uint8)
            input_batch = np.expand_dims(input_frame, axis=0)  # (1, 640, 640, 3)
            
            logger.debug(f"Hailo send: shape={input_batch.shape}, "
                         f"dtype={input_batch.dtype}, nbytes={input_batch.nbytes}")
            
            # Send frame through InputVStream (passes py::array directly to C++)
            self._hailo_input_vstream.send(input_batch)
            
            # Receive and parse output from each OutputVStream
            detections = []
            class_names = self.labels if self.labels else []
            
            for output_vstream in self._output_vstreams:
                # recv() returns:
                #   NMS output: list[class_idx] -> ndarray(N, 5) per frame
                #   Non-NMS:    ndarray
                nms_output = output_vstream.recv()
                
                if not isinstance(nms_output, list):
                    continue
                
                for class_idx, det_array in enumerate(nms_output):
                    if not isinstance(det_array, np.ndarray) or det_array.size == 0:
                        continue
                    
                    if det_array.ndim == 1:
                        det_array = det_array.reshape(1, -1)
                    
                    for det in det_array:
                        if len(det) < 5:
                            continue
                        
                        # Hailo NMS format: [y_min, x_min, y_max, x_max, confidence]
                        y1, x1, y2, x2, confidence = det[:5]
                        
                        if confidence < self.confidence:
                            continue
                        
                        # Scale normalized coords to original frame size
                        x1_scaled = int(max(0, min(frame_w - 1, x1 * frame_w)))
                        y1_scaled = int(max(0, min(frame_h - 1, y1 * frame_h)))
                        x2_scaled = int(max(0, min(frame_w - 1, x2 * frame_w)))
                        y2_scaled = int(max(0, min(frame_h - 1, y2 * frame_h)))
                        
                        class_name = (class_names[class_idx]
                                      if class_idx < len(class_names)
                                      else f'class_{class_idx}')
                        
                        detections.append({
                            'class_name': class_name,
                            'confidence': float(confidence),
                            'bbox': [x1_scaled, y1_scaled, x2_scaled, y2_scaled]
                        })
            
            return detections
            
        except Exception as e:
            logger.error(f"Hailo inference error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_hailo_nms_output(self, raw_output, frame_w, frame_h):
        """
        Parse Hailo YOLO NMS post-process output.
        
        The Python InferVStreams.infer() with tf_nms_format=False returns:
            dict[output_name] -> list[frame_idx] -> list[class_idx] -> ndarray(N, 5)
        Each detection row: [y_min, x_min, y_max, x_max, confidence] (normalized 0-1)
        """
        detections = []
        class_names = self.labels if self.labels else []
        
        for output_name, output_data in raw_output.items():
            if not isinstance(output_data, list):
                continue
            
            # Iterate over frames (batch dimension)
            for frame_detections in output_data:
                if not isinstance(frame_detections, list):
                    continue
                
                # Iterate over classes — each element is an ndarray(N, 5)
                for class_idx, det_array in enumerate(frame_detections):
                    if not isinstance(det_array, np.ndarray) or det_array.size == 0:
                        continue
                    
                    if det_array.ndim == 1:
                        det_array = det_array.reshape(1, -1)
                    
                    for det in det_array:
                        if len(det) < 5:
                            continue
                        
                        # Hailo NMS format: [y_min, x_min, y_max, x_max, confidence]
                        y1, x1, y2, x2, confidence = det[:5]
                        
                        if confidence < self.confidence:
                            continue
                        
                        # Scale normalized coords to original frame size
                        x1_scaled = int(max(0, min(frame_w - 1, x1 * frame_w)))
                        y1_scaled = int(max(0, min(frame_h - 1, y1 * frame_h)))
                        x2_scaled = int(max(0, min(frame_w - 1, x2 * frame_w)))
                        y2_scaled = int(max(0, min(frame_h - 1, y2 * frame_h)))
                        
                        class_name = class_names[class_idx] if class_idx < len(class_names) else f'class_{class_idx}'
                        
                        detections.append({
                            'class_name': class_name,
                            'confidence': float(confidence),
                            'bbox': [x1_scaled, y1_scaled, x2_scaled, y2_scaled]
                        })
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw bounding boxes and labels on frame"""
        if not detections:
            return frame
        
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = det['class_name']
            conf = det['confidence']
            
            color = (0, 255, 0) if conf > 0.7 else (0, 255, 255)
            
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
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
        if self.engine == 'ncnn':
            model_display = f"{self.ncnn_param} + {self.ncnn_bin}"
        elif self.engine == 'hef':
            model_display = self.model_path
        else:
            model_display = self.model_path
            
        return {
            'engine': self.engine,
            'device': self.device,
            'model': model_display,
            'loaded': self.loaded,
            'confidence_threshold': self.confidence,
            'classes': self.labels if self.labels else []
        }
