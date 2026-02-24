#!/usr/bin/env python3
"""
Configuration Manager
Handles loading and saving configuration from config.json
Supports real-time updates and file watching
"""

import json
import os
import logging
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)


class Config:
    """
    Centralized configuration manager with real-time updates
    This is the single source of truth for all configuration
    """
    
    def __init__(self, config_file='config.json'):
        """
        Initialize configuration
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self._lock = Lock()  # Thread-safe access
        self._last_modified = self._get_file_mtime()
        self._change_callbacks = []  # Callbacks to notify on changes
    
    def _get_file_mtime(self):
        """Get file modification time"""
        try:
            if os.path.exists(self.config_file):
                return os.path.getmtime(self.config_file)
        except:
            pass
        return None
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"✅ Configuration loaded from {self.config_file}")
                return config
            else:
                logger.warning(f"Config file not found: {self.config_file}")
                logger.info("Creating default configuration")
                config = self._get_default_config()
                self._save_config(config)
                return config
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Get default configuration"""
        return {
            "port": 5000,
            "debug": False,
            "camera": {
                "width": 640,
                "height": 480,
                "fps": 30
            },
            "detection": {
                "model": "backend/models/yolov8n.pt",
                "confidence": 0.5
            },
            "display": {
                "brightness": 50,
                "backlight_pin": 18,
                "pwm_frequency": 1000
            },
            "logging": {
                "level": "INFO",
                "file": "data/logs/app.log"
            },
            "tts": {
                "enabled": True,
                "speech_rate": 160,
                "volume": 1.0,
                "cooldown_seconds": 10
            }
        }
    
    def reload(self):
        """
        Reload configuration from file if it has been modified
        
        Returns:
            bool: True if configuration was reloaded
        """
        with self._lock:
            current_mtime = self._get_file_mtime()
            if current_mtime and current_mtime != self._last_modified:
                logger.info("🔄 Config file changed, reloading...")
                old_config = self.config.copy()
                self.config = self._load_config()
                self._last_modified = current_mtime
                
                # Notify callbacks of changes
                self._notify_changes(old_config, self.config)
                return True
        return False
    
    def register_change_callback(self, callback):
        """
        Register a callback to be notified when configuration changes
        
        Args:
            callback: Function to call with (old_config, new_config)
        """
        self._change_callbacks.append(callback)
        logger.info(f"Registered config change callback: {callback.__name__}")
    
    def _notify_changes(self, old_config, new_config):
        """Notify all registered callbacks of configuration changes"""
        for callback in self._change_callbacks:
            try:
                callback(old_config, new_config)
            except Exception as e:
                logger.error(f"Error in config change callback: {e}")
    
    def get(self, key, default=None):
        """
        Get configuration value using dot notation
        Thread-safe access with automatic reload check
        
        Args:
            key: Configuration key (e.g., 'camera.width')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check for file changes before reading
        self.reload()
        
        with self._lock:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def set(self, key, value, save=True):
        """
        Set configuration value using dot notation
        Automatically saves to file and notifies components
        
        Args:
            key: Configuration key (e.g., 'camera.width')
            value: Value to set
            save: Whether to save to file immediately (default: True)
        """
        with self._lock:
            old_config = self.config.copy()
            
            keys = key.split('.')
            config = self.config
            
            # Navigate to the parent dict
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set the value
            config[keys[-1]] = value
            logger.info(f"⚙️ Config updated: {key} = {value}")
            
            # Save to file if requested
            if save:
                self.save()
            
            # Notify callbacks
            self._notify_changes(old_config, self.config)
    
    def get_all(self):
        """
        Get entire configuration (with automatic reload)
        
        Returns:
            dict: Copy of entire configuration
        """
        self.reload()
        with self._lock:
            return self.config.copy()
    
    def update(self, data, save=True):
        """
        Update configuration with new data
        Automatically saves to file and notifies components
        
        Args:
            data: Dictionary of configuration updates
            save: Whether to save to file immediately (default: True)
        """
        with self._lock:
            old_config = self.config.copy()
            self._deep_update(self.config, data)
            logger.info(f"⚙️ Config batch update: {len(data)} changes")
            
            # Save to file if requested
            if save:
                self._save_config(self.config)
            
            # Notify callbacks
            self._notify_changes(old_config, self.config)
    
    def _deep_update(self, target, source):
        """Recursively update nested dictionaries"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _save_config(self, config):
        """Internal method to save configuration to file"""
        try:
            # Create backup before saving
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                with open(self.config_file, 'r') as f:
                    backup_data = f.read()
                with open(backup_file, 'w') as f:
                    f.write(backup_data)
            
            # Save new configuration
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Update modification time
            self._last_modified = self._get_file_mtime()
            logger.info(f"💾 Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            return False
    
    def save(self):
        """
        Save current configuration to file
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            return self._save_config(self.config)
    
    def get_metadata(self):
        """
        Get configuration metadata
        
        Returns:
            dict: Metadata about configuration
        """
        return {
            'file': self.config_file,
            'exists': os.path.exists(self.config_file),
            'last_modified': datetime.fromtimestamp(self._last_modified).isoformat() if self._last_modified else None,
            'callbacks_registered': len(self._change_callbacks),
            'keys': list(self.config.keys())
        }
