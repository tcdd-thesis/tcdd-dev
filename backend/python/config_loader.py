#!/usr/bin/env python3
"""
Configuration loader utility for Python scripts
Loads and provides access to shared/config.json
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """Load and access configuration from shared/config.json"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Default path relative to this file: backend/python -> shared/config.json
            config_path = Path(__file__).parent.parent.parent / 'shared' / 'config.json'
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✓ Configuration loaded from: {self.config_path}")
        except FileNotFoundError:
            print(f"⚠ Config file not found: {self.config_path}")
            print("Using default configuration values")
            self.config = self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"⚠ Error parsing config file: {e}")
            print("Using default configuration values")
            self.config = self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "backendPort": 5000,
            "pythonServerPort": 5001,
            "frontendPort": 3000,
            "camera": {
                "width": 640,
                "height": 480,
                "fps": 30,
                "bufferSize": 1
            },
            "detection": {
                "modelPath": "backend/python/model/best.pt",
                "confidenceThreshold": 0.5,
                "pollIntervalMs": 500,
                "maxDetectionsDisplay": 5,
                "detectionInterval": 1,
                "jpegQuality": 80
            },
            "display": {
                "fullscreen": False,
                "optimizedForPi": True,
                "theme": "dark"
            },
            "performance": {
                "enableGPU": False,
                "modelFormat": "pt",
                "maxCacheSize": 100,
                "compressionLevel": 6
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        Example: get('camera.width') returns config['camera']['width']
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_model_path(self) -> str:
        """Get model file path (converts relative to absolute)"""
        model_path = self.get('detection.modelPath', 'backend/python/model/best.pt')
        # Convert to absolute path relative to project root
        if not os.path.isabs(model_path):
            project_root = Path(__file__).parent.parent.parent
            model_path = str(project_root / model_path)
        return model_path
    
    def get_confidence_threshold(self) -> float:
        """Get confidence threshold for detections"""
        return self.get('detection.confidenceThreshold', 0.5)
    
    def get_detection_interval(self) -> int:
        """Get detection interval (frames between detections)"""
        return self.get('detection.detectionInterval', 1)
    
    def get_jpeg_quality(self) -> int:
        """Get JPEG quality for encoding"""
        return self.get('detection.jpegQuality', 80)
    
    def get_camera_width(self) -> int:
        """Get camera width"""
        return self.get('camera.width', 640)
    
    def get_camera_height(self) -> int:
        """Get camera height"""
        return self.get('camera.height', 480)
    
    def get_camera_fps(self) -> int:
        """Get camera FPS"""
        return self.get('camera.fps', 30)
    
    def get_python_server_port(self) -> int:
        """Get Python server port"""
        return self.get('pythonServerPort', 5001)


# Create singleton instance
_config_loader = None

def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """Get or create singleton ConfigLoader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


if __name__ == '__main__':
    # Test the config loader
    print("\n" + "="*60)
    print("Configuration Loader Test")
    print("="*60)
    
    config = get_config_loader()
    
    print(f"\nPorts:")
    print(f"  Backend Port:        {config.get('backendPort')}")
    print(f"  Python Server Port:  {config.get_python_server_port()}")
    
    print(f"\nModel Configuration:")
    print(f"  Model Path:          {config.get_model_path()}")
    print(f"  Confidence:          {config.get_confidence_threshold()}")
    print(f"  Detection Interval:  {config.get_detection_interval()}")
    print(f"  JPEG Quality:        {config.get_jpeg_quality()}")
    
    print(f"\nCamera Configuration:")
    print(f"  Resolution:          {config.get_camera_width()}x{config.get_camera_height()}")
    print(f"  FPS:                 {config.get_camera_fps()}")
    
    print(f"\n" + "="*60)
    print("✓ Configuration test completed successfully!")
    print("="*60 + "\n")
