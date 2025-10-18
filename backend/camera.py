#!/usr/bin/env python3
"""
Camera Handler - PiCamera2 Integration
Handles frame capture from Raspberry Pi Camera Module
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Try importing picamera2 for Raspberry Pi camera
try:
    from picamera2 import Picamera2
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False
    logger.warning("picamera2 not available, will use mock camera or OpenCV")

# Fallback to OpenCV
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV not available")


class Camera:
    """Camera handler for frame capture"""
    
    def __init__(self, config):
        """
        Initialize camera
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.camera = None
        self.running = False
        self.use_picamera = HAS_PICAMERA2
        
        # Camera settings from config
        self.width = config.get('camera.width', 640)
        self.height = config.get('camera.height', 480)
        self.fps = config.get('camera.fps', 30)
        
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize the camera hardware"""
        try:
            if HAS_PICAMERA2:
                logger.info("Initializing Raspberry Pi Camera (PiCamera2)...")
                self.camera = Picamera2()
                
                # Configure camera
                camera_config = self.camera.create_preview_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"},
                    buffer_count=2
                )
                self.camera.configure(camera_config)
                
                logger.info(f"Camera configured: {self.width}x{self.height} @ {self.fps}fps")
                self.use_picamera = True
                
            elif HAS_OPENCV:
                logger.info("Initializing OpenCV VideoCapture...")
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                self.use_picamera = False
                
                if not self.camera.isOpened():
                    raise RuntimeError("Failed to open camera")
                
                logger.info(f"OpenCV camera initialized: {self.width}x{self.height}")
                
            else:
                logger.warning("No camera available - using mock camera")
                self.use_picamera = False
                
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise
    
    def start(self):
        """Start camera capture"""
        try:
            if self.use_picamera and self.camera:
                self.camera.start()
                # Warm up camera
                import time
                time.sleep(0.5)
            
            self.running = True
            logger.info("Camera started")
            
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            raise
    
    def stop(self):
        """Stop camera capture"""
        try:
            self.running = False
            
            if self.use_picamera and self.camera:
                self.camera.stop()
            elif self.camera and hasattr(self.camera, 'release'):
                self.camera.release()
            
            logger.info("Camera stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")
    
    def get_frame(self):
        """
        Capture a single frame
        Returns:
            numpy.ndarray: Frame in RGB format for NCNN, or None if failed
        """
        if not self.running:
            return None
        try:
            if self.use_picamera and self.camera:
                # PiCamera2 returns RGB888, perfect for NCNN
                frame = self.camera.capture_array()
                return frame  # Already RGB
            elif HAS_OPENCV and self.camera:
                # OpenCV VideoCapture returns BGR, convert to RGB for NCNN
                ret, frame = self.camera.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return frame if ret else None
            else:
                # Mock camera - return a blank frame in RGB
                return self._get_mock_frame()
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def _get_mock_frame(self):
        """
        Generate a mock frame for testing without camera
        Returns:
            numpy.ndarray: Mock frame in RGB format
        """
        import cv2
        from datetime import datetime
        # Create blank frame
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Add text (OpenCV uses BGR, so convert to RGB before returning)
        text = f"Mock Camera - {datetime.now().strftime('%H:%M:%S')}"
        cv2.putText(frame, text, (50, self.height // 2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "No camera detected", (50, self.height // 2 + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 1)
        # Convert BGR to RGB for NCNN
        if HAS_OPENCV:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame
    
    def is_running(self):
        """Check if camera is running"""
        return self.running
    
    def get_info(self):
        """Get camera information"""
        return {
            'type': 'PiCamera2' if self.use_picamera else 'OpenCV' if HAS_OPENCV else 'Mock',
            'resolution': f"{self.width}x{self.height}",
            'fps': self.fps,
            'running': self.running
        }
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.running:
            self.stop()
