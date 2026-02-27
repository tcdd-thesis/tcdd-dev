#!/usr/bin/env python3
"""
Device Pairing Manager
Handles secure pairing of a single phone/tablet to the system.
Uses Hotspot Mode - Pi creates its own WiFi network for direct connection.

Only one device can be paired at a time.
Touchscreen (local) always has full access.
"""

import json
import os
import secrets
import logging
from datetime import datetime
from threading import Lock
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Default hotspot IP (NetworkManager default)
HOTSPOT_IP = '10.42.0.1'

# Default local domain for hotspot access
HOTSPOT_DOMAIN = 'tcdd.local'


class PairingManager:
    """
    Manages device pairing for remote access.
    
    Features:
    - Single device pairing (strict)
    - Token-based authentication
    - Persists across reboots
    - Pending token for QR code generation
    - Automatic disconnect of old device when new one pairs
    """
    
    def __init__(self, data_dir: str = 'data'):
        """
        Initialize pairing manager.
        
        Args:
            data_dir: Directory to store pairing data
        """
        self.data_dir = data_dir
        self.pairing_file = os.path.join(data_dir, 'pairing.json')
        self._lock = Lock()
        
        # Current pairing state
        self._paired_device: Optional[Dict[str, Any]] = None
        self._pending_token: Optional[str] = None
        
        # Callback for disconnecting old device (set by main.py)
        self._disconnect_callback = None
        
        # Load existing pairing from file
        self._load_pairing()
    
    def _load_pairing(self):
        """Load pairing state from file."""
        try:
            if os.path.exists(self.pairing_file):
                with open(self.pairing_file, 'r') as f:
                    data = json.load(f)
                    self._paired_device = data.get('paired_device')
                    if self._paired_device:
                        logger.info(f"Loaded existing pairing: {self._paired_device.get('device_name', 'Unknown')}")
            else:
                logger.info("No existing pairing found")
        except Exception as e:
            logger.error(f"Error loading pairing data: {e}")
            self._paired_device = None
    
    def _save_pairing(self):
        """Save pairing state to file."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.pairing_file, 'w') as f:
                json.dump({
                    'paired_device': self._paired_device,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
            logger.info("Pairing data saved")
        except Exception as e:
            logger.error(f"Error saving pairing data: {e}")
    
    def generate_pairing_token(self) -> str:
        """
        Generate a new pairing token for QR code.
        Token remains valid until used (no expiry).
        
        Returns:
            str: 8-character alphanumeric token (easy to type manually)
        """
        with self._lock:
            # Generate a short, easy-to-type token
            # Using uppercase + digits, excluding confusing chars (0, O, I, 1, L)
            alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
            self._pending_token = ''.join(secrets.choice(alphabet) for _ in range(8))
            logger.info(f"Generated pairing token: {self._pending_token}")
            return self._pending_token
    
    def get_pending_token(self) -> Optional[str]:
        """Get the current pending token (if any)."""
        return self._pending_token
    
    def validate_and_pair(self, token: str, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a pairing token and pair the device.
        
        Args:
            token: The pairing token to validate
            device_info: Information about the device being paired
                - device_id: Unique identifier (from browser)
                - device_name: User-friendly name (e.g., "iPhone", "Chrome on Android")
                - user_agent: Browser user agent string
        
        Returns:
            dict: Result with 'success', 'message', and optionally 'session_token'
        """
        with self._lock:
            # Check if token matches pending token
            if not self._pending_token:
                return {
                    'success': False,
                    'message': 'No pairing code has been generated. Please generate a code on the device first.'
                }
            
            if token.upper() != self._pending_token:
                logger.warning(f"Invalid pairing token attempt: {token}")
                return {
                    'success': False,
                    'message': 'Invalid pairing code. Please check and try again.'
                }
            
            # Token is valid! Check if another device is already paired
            old_device = self._paired_device
            
            # Generate a session token for this device (longer, for auth)
            session_token = secrets.token_urlsafe(32)
            
            # Create new pairing
            self._paired_device = {
                'device_id': device_info.get('device_id', secrets.token_urlsafe(16)),
                'device_name': device_info.get('device_name', 'Unknown Device'),
                'user_agent': device_info.get('user_agent', ''),
                'session_token': session_token,
                'paired_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
            
            # Clear the pending token (one-time use)
            self._pending_token = None
            
            # Save to file
            self._save_pairing()
            
            # If there was an old device, trigger disconnect
            if old_device and self._disconnect_callback:
                logger.info(f"Disconnecting old device: {old_device.get('device_name')}")
                try:
                    self._disconnect_callback(old_device.get('session_token'))
                except Exception as e:
                    logger.error(f"Error disconnecting old device: {e}")
            
            logger.info(f"Device paired: {self._paired_device['device_name']}")
            
            return {
                'success': True,
                'message': 'Device paired successfully!',
                'session_token': session_token,
                'device_id': self._paired_device['device_id']
            }
    
    def validate_session(self, session_token: str) -> bool:
        """
        Validate a session token for an already-paired device.
        
        Args:
            session_token: The session token to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        with self._lock:
            if not self._paired_device:
                return False
            
            is_valid = self._paired_device.get('session_token') == session_token
            
            if is_valid:
                # Update last seen
                self._paired_device['last_seen'] = datetime.now().isoformat()
                # Don't save on every validation (too frequent), just update in memory
            
            return is_valid
    
    def is_paired(self) -> bool:
        """Check if any device is currently paired."""
        return self._paired_device is not None
    
    def get_paired_device_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently paired device.
        
        Returns:
            dict: Device info (without session_token for security) or None
        """
        if not self._paired_device:
            return None
        
        # Return sanitized info (no session token)
        return {
            'device_id': self._paired_device.get('device_id'),
            'device_name': self._paired_device.get('device_name'),
            'paired_at': self._paired_device.get('paired_at'),
            'last_seen': self._paired_device.get('last_seen')
        }
    
    def unpair(self) -> bool:
        """
        Unpair the currently paired device.
        
        Returns:
            bool: True if a device was unpaired, False if none was paired
        """
        with self._lock:
            if not self._paired_device:
                return False
            
            old_device = self._paired_device
            old_token = old_device.get('session_token')
            
            # Clear pairing
            self._paired_device = None
            self._pending_token = None
            
            # Save to file
            self._save_pairing()
            
            # Trigger disconnect callback
            if self._disconnect_callback and old_token:
                try:
                    self._disconnect_callback(old_token)
                except Exception as e:
                    logger.error(f"Error disconnecting device during unpair: {e}")
            
            logger.info(f"Device unpaired: {old_device.get('device_name')}")
            return True
    
    def set_disconnect_callback(self, callback):
        """
        Set callback function to disconnect a device.
        Called with session_token when device should be disconnected.
        
        Args:
            callback: Function(session_token: str) -> None
        """
        self._disconnect_callback = callback
    
    def is_local_request(self, remote_addr: str) -> bool:
        """
        Check if request is from local machine (touchscreen).
        Local requests bypass pairing requirements.
        
        Args:
            remote_addr: IP address of the requester
            
        Returns:
            bool: True if local (touchscreen), False if remote
        """
        local_addresses = ['127.0.0.1', '::1', 'localhost']
        return remote_addr in local_addresses
    
    def get_hotspot_ip(self) -> str:
        """
        Get the hotspot IP address (constant for NetworkManager hotspot).
        
        Returns:
            str: Hotspot IP address (always 10.42.0.1)
        """
        return HOTSPOT_IP
    
    def generate_pairing_data(self, port: int = 80, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate complete pairing data including QR code content.
        Uses the domain name if provided, otherwise falls back to IP.
        
        Args:
            port: Server port number
            domain: Optional domain name (e.g., 'tcdd.local')
            
        Returns:
            dict: Pairing data with token, URL, and QR content
        """
        # Generate or get pending token
        token = self._pending_token or self.generate_pairing_token()
        
        # Use domain if provided, otherwise fall back to IP
        host = domain or HOTSPOT_DOMAIN
        
        # URL for phone to connect (domain-based URL for easy typing)
        # Note: Port 80 is implicit if using standard HTTP
        if port == 80:
            url = f"http://{host}/pair?token={token}"
        else:
            url = f"http://{host}:{port}/pair?token={token}"
        
        # Also provide IP-based URL as fallback
        ip_url = f"http://{HOTSPOT_IP}:{port}/pair?token={token}"
        
        return {
            'token': token,
            'ip': HOTSPOT_IP,
            'domain': host,
            'port': port,
            'url': url,
            'ip_url': ip_url,
            'qr_content': url  # QR code should encode the domain URL
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get full pairing status for API response.
        
        Returns:
            dict: Complete pairing status
        """
        return {
            'is_paired': self.is_paired(),
            'paired_device': self.get_paired_device_info(),
            'has_pending_token': self._pending_token is not None,
            'hotspot_ip': HOTSPOT_IP,
            'hotspot_domain': HOTSPOT_DOMAIN
        }


# Singleton instance
_pairing_manager: Optional[PairingManager] = None


def get_pairing_manager(data_dir: str = 'data') -> PairingManager:
    """
    Get the singleton PairingManager instance.
    
    Args:
        data_dir: Directory for pairing data (only used on first call)
        
    Returns:
        PairingManager: The singleton instance
    """
    global _pairing_manager
    if _pairing_manager is None:
        _pairing_manager = PairingManager(data_dir)
    return _pairing_manager
