#!/usr/bin/env python3
"""
Configuration Manager
Handles loading and saving configuration from config.json
Supports real-time updates and file watching
"""

import json
import os
import logging
from threading import Lock, RLock
from datetime import datetime

logger = logging.getLogger(__name__)


def _strip_json_comments(text):
    """
    Strip // comments from JSON-with-comments text.
    Handles comments correctly even when // appears inside strings.
    Returns cleaned JSON string.
    """
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        in_string = False
        escape_next = False
        result = []
        i = 0
        while i < len(line):
            ch = line[i]
            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue
            if ch == '\\' and in_string:
                result.append(ch)
                escape_next = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                i += 1
                continue
            if not in_string and ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
                break  # Rest of line is a comment
            result.append(ch)
            i += 1

        stripped = ''.join(result).rstrip()
        if stripped.strip() == '':
            continue
        cleaned_lines.append(stripped)

    return '\n'.join(cleaned_lines)


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
        self._lock = RLock()  # Thread-safe access (reentrant for nested set→save calls)
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
                logger.info(f"Configuration loaded from {self.config_file}")
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
        """Get default configuration by parsing config-template-json.txt"""
        template_path = os.path.join(os.path.dirname(self.config_file), 'config-template-json.txt')
        try:
            with open(template_path, 'r') as f:
                content = f.read()

            cleaned_json = _strip_json_comments(content)
            with open(self.config_file, 'w') as f:
                f.write(cleaned_json)
            return json.loads(cleaned_json)

        except Exception as e:
            logger.error(f"Error parsing config template: {e}")
            return None
    
    def reload(self):
        """
        Reload configuration from file if it has been modified
        
        Returns:
            bool: True if configuration was reloaded
        """
        with self._lock:
            current_mtime = self._get_file_mtime()
            if current_mtime and current_mtime != self._last_modified:
                logger.info("Config file changed, reloading...")
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
            logger.info(f"Config updated: {key} = {value}")
            
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
            logger.info(f"Config batch update: {len(data)} changes")
            
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
            logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
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


def _parse_version(ver_str):
    """
    Parse a version string into a comparable tuple.
    Supports formats like '1.0.0' and '0.1.0-b20260226-1'.
    The base version (e.g. 1.0.0) is split into integer parts.
    A pre-release suffix (after '-') makes the version sort lower
    than the same base without a suffix.
    """
    # Split base version from pre-release suffix
    parts = ver_str.split('-', 1)
    base = parts[0]
    suffix = parts[1] if len(parts) > 1 else None

    # Convert base to tuple of ints
    base_tuple = tuple(int(x) for x in base.split('.'))

    # Versions without suffix sort higher than those with one
    # e.g. 1.0.0 > 1.0.0-beta1
    if suffix is None:
        return (base_tuple, (1,))  # no suffix = release
    else:
        return (base_tuple, (0, suffix))  # suffix = pre-release


def _merge_configs(template, current):
    """
    Recursively merge current config into template structure.
    - Keys in template but not in current: added (new settings)
    - Keys in current but not in template: dropped (obsolete)
    - Keys in both: keep current value; recurse if both are dicts
    """
    merged = {}
    for key, tmpl_value in template.items():
        if key in current:
            cur_value = current[key]
            if isinstance(tmpl_value, dict) and isinstance(cur_value, dict):
                merged[key] = _merge_configs(tmpl_value, cur_value)
            else:
                merged[key] = cur_value
        else:
            # New key from template
            merged[key] = tmpl_value
    return merged


def migrate_config(template_path, config_path):
    """
    Migrate config.json to match a newer template.
    Adds new keys, removes obsolete keys, preserves user values.
    Only runs if the template version is strictly newer.

    Called from start.sh when a version mismatch is detected.
    """
    # Parse template
    with open(template_path, 'r') as f:
        template = json.loads(_strip_json_comments(f.read()))

    # Load existing config
    with open(config_path, 'r') as f:
        current = json.load(f)

    tmpl_ver = template.get('version', '0.0.0')
    conf_ver = current.get('version', '0.0.0')

    # Compare versions — only migrate if template is strictly newer
    if _parse_version(tmpl_ver) <= _parse_version(conf_ver):
        print(f"Config is up to date (config: {conf_ver}, template: {tmpl_ver}) — skipping migration.")
        return

    print(f"Migrating config from {conf_ver} to {tmpl_ver}...")

    # Merge: template structure wins, user values preserved
    merged = _merge_configs(template, current)

    # Ensure version is updated to the template's version
    merged['version'] = tmpl_ver

    # Backup old config
    backup_path = f"{config_path}.backup"
    with open(config_path, 'r') as f:
        backup_data = f.read()
    with open(backup_path, 'w') as f:
        f.write(backup_data)
    print(f"Old config backed up to {backup_path}")

    # Save merged config
    with open(config_path, 'w') as f:
        json.dump(merged, f, indent=2)
    print(f"Config migrated successfully to version {tmpl_ver}.")
