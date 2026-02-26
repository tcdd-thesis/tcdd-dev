#!/usr/bin/env python3
"""
WiFi Hotspot Manager
Manages the Raspberry Pi's WiFi hotspot for direct device connections.
Uses NetworkManager (nmcli) for reliable hotspot management.
Settings are stored in the centralized config.json.
Includes local DNS via dnsmasq for easy access (e.g., http://tcdd.local).
"""

import subprocess
import logging
import secrets
import os
from typing import Optional, Dict, Any, Tuple
from threading import Lock

logger = logging.getLogger(__name__)

# Default hotspot IP (NetworkManager assigns this)
HOTSPOT_IP = '10.42.0.1'

# Default local domain for hotspot access
HOTSPOT_DOMAIN = 'tcdd.local'

# dnsmasq config file path
DNSMASQ_CONFIG_FILE = '/etc/dnsmasq.d/tcdd-hotspot.conf'


class HotspotManager:
    """
    Manages WiFi hotspot for direct phone/tablet connections.
    
    Features:
    - Create hotspot with auto-generated or custom credentials
    - Start/stop hotspot on demand
    - Persist hotspot settings
    - Check hotspot status
    - Works with NetworkManager (nmcli)
    """
    
    # Default hotspot configuration
    DEFAULT_SSID_PREFIX = "TCDD"
    DEFAULT_PASSWORD_LENGTH = 8
    HOTSPOT_CONNECTION_NAME = "TCDD-Hotspot"
    
    def __init__(self, config=None):
        """
        Initialize hotspot manager.
        
        Args:
            config: Config object from config.py for reading/writing settings
        """
        self.config = config
        self._lock = Lock()
        self._is_active: bool = False
        
        # Load settings from config or generate defaults
        self._load_from_config()
        
        # Check current hotspot status
        self._check_status()
    
    def _load_from_config(self):
        """Load hotspot settings from config.json."""
        if self.config:
            self._ssid = self.config.get('pairing.ssid', '')
            self._password = self.config.get('pairing.password', '')
            self._interface = self.config.get('pairing.interface', 'wlan0')
            self._auto_start = self.config.get('pairing.auto_start', True)
            self._enabled = self.config.get('pairing.enabled', True)
            self._domain = self.config.get('pairing.domain', HOTSPOT_DOMAIN)
            self._last_ssid = self.config.get('wifi.last_ssid', '')
            
            # Generate credentials if not set
            if not self._ssid or not self._password:
                self._generate_credentials()
            else:
                logger.info(f"Loaded hotspot config: SSID={self._ssid}, domain={self._domain}")
        else:
            # No config object, generate defaults
            self._interface = 'wlan0'
            self._auto_start = True
            self._enabled = True
            self._domain = HOTSPOT_DOMAIN
            self._last_ssid = ''
            self._generate_credentials()
    
    def _save_to_config(self):
        """Save hotspot settings to config.json."""
        if self.config:
            self.config.set('pairing.ssid', self._ssid, save=False)
            self.config.set('pairing.password', self._password, save=False)
            self.config.set('pairing.interface', self._interface, save=False)
            self.config.save()
            logger.info("Hotspot config saved to config.json")
    
    def _generate_credentials(self):
        """Generate new hotspot SSID and password."""
        # Generate a 4-character suffix for SSID
        suffix = ''.join(secrets.choice('ABCDEFGHJKMNPQRSTUVWXYZ23456789') for _ in range(4))
        self._ssid = f"{self.DEFAULT_SSID_PREFIX}-{suffix}"
        
        # Generate an 8-character password (easy to type)
        # Using only alphanumeric, no confusing characters
        alphabet = 'abcdefghjkmnpqrstuvwxyz23456789'
        self._password = ''.join(secrets.choice(alphabet) for _ in range(self.DEFAULT_PASSWORD_LENGTH))
        
        logger.info(f"Generated hotspot credentials: SSID={self._ssid}")
        self._save_to_config()
    
    def _setup_dns(self) -> bool:
        """
        Configure dnsmasq to provide local DNS for the hotspot.
        Maps the domain (e.g., tcdd.local) to the hotspot IP.
        
        NOTE: NetworkManager handles DHCP for the hotspot automatically.
        We only use dnsmasq for DNS resolution of the local domain.
        
        Returns:
            bool: True if successful
        """
        try:
            # Create dnsmasq config content - DNS ONLY, no DHCP
            # NetworkManager handles DHCP for hotspot clients
            config_content = f"""# TCDD Hotspot Captive Portal DNS Configuration
# Auto-generated - do not edit manually
# Redirects ALL DNS queries to {HOTSPOT_IP} for captive portal

# Resolve ALL domains to hotspot IP (captive portal)
address=/#/{HOTSPOT_IP}

# Also explicitly map local domain
address=/{self._domain}/{HOTSPOT_IP}
address=/www.{self._domain}/{HOTSPOT_IP}

# Don't forward any queries upstream — full captive portal
no-resolv

# Don't run DHCP - NetworkManager handles that for the hotspot
no-dhcp-interface={self._interface}

# Listen on hotspot interface
listen-address={HOTSPOT_IP}
listen-address=127.0.0.1
bind-interfaces
"""
            
            # Write config file (requires sudo)
            # Use a temp file and sudo mv approach
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(config_content)
                temp_path = f.name
            
            # Move to dnsmasq.d with sudo
            result = subprocess.run(
                ['sudo', 'mv', temp_path, DNSMASQ_CONFIG_FILE],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to create dnsmasq config: {result.stderr}")
                return False
            
            # Set proper permissions
            subprocess.run(['sudo', 'chmod', '644', DNSMASQ_CONFIG_FILE], timeout=5)
            
            # Restart dnsmasq to apply changes
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'dnsmasq'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"DNS configured: {self._domain} -> {HOTSPOT_IP}")
                return True
            else:
                # dnsmasq might not be installed, try to install it
                logger.warning(f"dnsmasq restart failed, attempting install...")
                install_result = subprocess.run(
                    ['sudo', 'apt-get', 'install', '-y', 'dnsmasq'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if install_result.returncode == 0:
                    subprocess.run(['sudo', 'systemctl', 'restart', 'dnsmasq'], timeout=30)
                    logger.info(f"dnsmasq installed and DNS configured")
                    return True
                else:
                    logger.warning(f"Could not setup DNS (dnsmasq not available)")
                    return False
                
        except Exception as e:
            logger.error(f"DNS setup error: {e}")
            return False
    
    def _cleanup_dns(self) -> bool:
        """
        Remove dnsmasq configuration for the hotspot.
        
        Returns:
            bool: True if successful
        """
        try:
            # Check if config file exists
            if not os.path.exists(DNSMASQ_CONFIG_FILE):
                return True
            
            # Remove config file
            result = subprocess.run(
                ['sudo', 'rm', '-f', DNSMASQ_CONFIG_FILE],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Restart dnsmasq
            subprocess.run(
                ['sudo', 'systemctl', 'restart', 'dnsmasq'],
                capture_output=True,
                timeout=30
            )
            
            logger.info("DNS config cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"DNS cleanup error: {e}")
            return False
    
    def _run_nmcli(self, args: list, timeout: int = 30) -> Tuple[str, str, int]:
        """
        Run nmcli command.
        
        Args:
            args: Command arguments
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        try:
            result = subprocess.run(
                ['nmcli'] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return '', 'Command timed out', -1
        except FileNotFoundError:
            return '', 'nmcli not found (NetworkManager not installed)', -2
        except Exception as e:
            return '', str(e), -3
    
    def _check_status(self):
        """Check if hotspot is currently active."""
        try:
            # Check if our hotspot connection is active
            stdout, stderr, code = self._run_nmcli([
                '-t', '-f', 'NAME,TYPE,DEVICE',
                'connection', 'show', '--active'
            ])
            
            if code == 0:
                for line in stdout.strip().split('\n'):
                    if self.HOTSPOT_CONNECTION_NAME in line:
                        self._is_active = True
                        logger.info("Hotspot is currently active")
                        return
            
            self._is_active = False
        except Exception as e:
            logger.error(f"Error checking hotspot status: {e}")
            self._is_active = False
    
    def is_available(self) -> bool:
        """
        Check if hotspot functionality is available on this system.
        
        Returns:
            bool: True if hotspot can be used
        """
        # Check if nmcli is available
        stdout, stderr, code = self._run_nmcli(['--version'])
        if code != 0:
            return False
        
        # Check if WiFi device exists
        stdout, stderr, code = self._run_nmcli(['-t', '-f', 'DEVICE,TYPE', 'device'])
        if code == 0:
            for line in stdout.strip().split('\n'):
                if ':wifi' in line:
                    return True
        
        return False
    
    def start(self) -> Dict[str, Any]:
        """
        Start the WiFi hotspot.
        
        Returns:
            dict: Result with 'success', 'message', and hotspot details
        """
        with self._lock:
            if self._is_active:
                return {
                    'success': True,
                    'message': 'Hotspot is already running',
                    'ssid': self._ssid,
                    'password': self._password,
                    'ip': HOTSPOT_IP
                }
            
            try:
                logger.info(f"Starting hotspot: {self._ssid}")
                
                # Stop dnsmasq first to avoid DHCP conflicts with NetworkManager
                subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], 
                              capture_output=True, timeout=10)
                
                # First, try to delete any existing hotspot connection with same name
                self._run_nmcli(['connection', 'delete', self.HOTSPOT_CONNECTION_NAME], timeout=5)
                
                # Ensure WiFi is on and not connected elsewhere
                self._run_nmcli(['radio', 'wifi', 'on'], timeout=5)
                self._run_nmcli(['device', 'disconnect', self._interface], timeout=5)
                
                # Create and activate hotspot
                # Using nmcli device wifi hotspot command
                stdout, stderr, code = self._run_nmcli([
                    'device', 'wifi', 'hotspot',
                    'ifname', self._interface,
                    'con-name', self.HOTSPOT_CONNECTION_NAME,
                    'ssid', self._ssid,
                    'password', self._password
                ], timeout=30)
                
                if code == 0:
                    self._is_active = True
                    logger.info(f"Hotspot started: {self._ssid} (IP: {HOTSPOT_IP})")
                    
                    # Setup DNS for local domain access
                    dns_ok = self._setup_dns()
                    
                    return {
                        'success': True,
                        'message': f'Hotspot "{self._ssid}" started',
                        'ssid': self._ssid,
                        'password': self._password,
                        'ip': HOTSPOT_IP,
                        'domain': self._domain if dns_ok else None,
                        'url': f'http://{self._domain}' if dns_ok else f'http://{HOTSPOT_IP}'
                    }
                else:
                    error_msg = stderr.strip() or 'Failed to start hotspot'
                    logger.error(f"Hotspot start failed: {error_msg}")
                    return {
                        'success': False,
                        'message': error_msg
                    }
                    
            except Exception as e:
                logger.error(f"Hotspot start error: {e}")
                return {
                    'success': False,
                    'message': str(e)
                }
    
    def _reconnect_wifi(self):
        """
        Reconnect WiFi to the best available known network.
        Called after stopping the hotspot to restore regular WiFi connectivity.
        """
        try:
            import time
            
            logger.info("Attempting to reconnect WiFi...")
            
            # Ensure autoconnect is enabled on the interface
            self._run_nmcli([
                'device', 'set', self._interface, 'autoconnect', 'yes'
            ], timeout=5)
            
            # Small delay to let the interface settle after hotspot teardown
            time.sleep(1)

            # Reload to get the latest last_ssid in case it changed
            if self.config:
                self._last_ssid = self.config.get('wifi.last_ssid', '')
            
            if self._last_ssid:
                logger.info(f"Attempting to reconnect to last known SSID: {self._last_ssid}")
                stdout, stderr, code = self._run_nmcli([
                    'connection', 'up', self._last_ssid
                ], timeout=15)
                
                if code == 0:
                    logger.info(f"Successfully reconnected to last SSID: {self._last_ssid}")
                    return
                else:
                    logger.warning(f"Failed to reconnect to last SSID ({stderr.strip()}), falling back to auto-connect...")

            
            # Tell NetworkManager to connect the device (picks best known network)
            stdout, stderr, code = self._run_nmcli([
                'device', 'connect', self._interface
            ], timeout=15)
            
            if code == 0:
                logger.info(f"WiFi reconnected: {stdout.strip()}")
            else:
                # Fallback: try to activate the most recent WiFi connection
                logger.warning(f"Auto-connect failed ({stderr.strip()}), trying saved connections...")
                
                # List saved WiFi connections
                stdout2, _, code2 = self._run_nmcli([
                    '-t', '-f', 'NAME,TYPE', 'connection', 'show'
                ], timeout=5)
                
                if code2 == 0:
                    for line in stdout2.strip().split('\n'):
                        if ':802-11-wireless' in line:
                            conn_name = line.split(':')[0]
                            if conn_name and conn_name != self.HOTSPOT_CONNECTION_NAME:
                                logger.info(f"Trying saved connection: {conn_name}")
                                _, _, rc = self._run_nmcli([
                                    'connection', 'up', conn_name
                                ], timeout=15)
                                if rc == 0:
                                    logger.info(f"Connected to: {conn_name}")
                                    return
                
                logger.warning("Could not auto-reconnect WiFi. Use the UI to connect manually.")
                
        except Exception as e:
            logger.error(f"WiFi reconnect error: {e}")
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop the WiFi hotspot.
        
        Returns:
            dict: Result with 'success' and 'message'
        """
        with self._lock:
            if not self._is_active:
                return {
                    'success': True,
                    'message': 'Hotspot is not running'
                }
            
            try:
                logger.info("Stopping hotspot...")
                
                # Clean up DNS config first
                self._cleanup_dns()
                
                # Deactivate the hotspot connection
                stdout, stderr, code = self._run_nmcli([
                    'connection', 'down', self.HOTSPOT_CONNECTION_NAME
                ], timeout=15)
                
                if code == 0:
                    self._is_active = False
                    logger.info("Hotspot stopped")
                    
                    # Reconnect WiFi to the best available known network in background
                    # so we don't block the API response and freeze the UI
                    import threading
                    threading.Thread(target=self._reconnect_wifi, daemon=True).start()
                    
                    return {
                        'success': True,
                        'message': 'Hotspot stopped'
                    }
                else:
                    # Try alternative: turn off wifi and back on
                    self._run_nmcli(['radio', 'wifi', 'off'], timeout=5)
                    self._run_nmcli(['radio', 'wifi', 'on'], timeout=5)
                    self._is_active = False
                    
                    # Give radio a moment to come back, then reconnect in background
                    import threading
                    def delayed_reconnect():
                        import time
                        time.sleep(2)
                        self._reconnect_wifi()
                        
                    threading.Thread(target=delayed_reconnect, daemon=True).start()
                    
                    return {
                        'success': True,
                        'message': 'Hotspot stopped (radio reset)'
                    }
                    
            except Exception as e:
                logger.error(f"Hotspot stop error: {e}")
                return {
                    'success': False,
                    'message': str(e)
                }
    
    def get_credentials(self) -> Dict[str, str]:
        """
        Get current hotspot credentials.
        
        Returns:
            dict: SSID and password
        """
        return {
            'ssid': self._ssid,
            'password': self._password
        }
    
    def set_credentials(self, ssid: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Set custom hotspot credentials.
        
        Args:
            ssid: Custom SSID (None to keep current)
            password: Custom password (None to keep current)
            
        Returns:
            dict: Result with new credentials
        """
        with self._lock:
            if self._is_active:
                return {
                    'success': False,
                    'message': 'Cannot change credentials while hotspot is active. Stop it first.'
                }
            
            if ssid:
                if len(ssid) < 1 or len(ssid) > 32:
                    return {
                        'success': False,
                        'message': 'SSID must be 1-32 characters'
                    }
                self._ssid = ssid
            
            if password:
                if len(password) < 8 or len(password) > 63:
                    return {
                        'success': False,
                        'message': 'Password must be 8-63 characters'
                    }
                self._password = password
            
            self._save_to_config()
            
            return {
                'success': True,
                'message': 'Credentials updated',
                'ssid': self._ssid,
                'password': self._password
            }
    
    def regenerate_credentials(self) -> Dict[str, Any]:
        """
        Generate new random credentials.
        
        Returns:
            dict: New credentials
        """
        with self._lock:
            if self._is_active:
                return {
                    'success': False,
                    'message': 'Cannot regenerate while hotspot is active. Stop it first.'
                }
            
            self._generate_credentials()
            
            return {
                'success': True,
                'message': 'New credentials generated',
                'ssid': self._ssid,
                'password': self._password
            }
    
    def is_active(self) -> bool:
        """Check if hotspot is currently active."""
        self._check_status()
        return self._is_active
    
    def is_enabled(self) -> bool:
        """Check if hotspot is enabled in config."""
        return self._enabled
    
    def is_auto_start(self) -> bool:
        """Check if hotspot should auto-start."""
        return self._auto_start
    
    def set_auto_start(self, enabled: bool) -> Dict[str, Any]:
        """
        Set whether hotspot should auto-start.
        
        Args:
            enabled: True to enable auto-start
            
        Returns:
            dict: Result
        """
        self._auto_start = enabled
        if self.config:
            self.config.set('pairing.auto_start', enabled, save=True)
        
        return {
            'success': True,
            'message': f'Auto-start {"enabled" if enabled else "disabled"}',
            'auto_start': enabled
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get full hotspot status.
        
        Returns:
            dict: Complete hotspot status
        """
        self._check_status()
        
        return {
            'available': self.is_available(),
            'enabled': self._enabled,
            'active': self._is_active,
            'auto_start': self._auto_start,
            'ssid': self._ssid,
            'password': self._password if self._is_active else None,
            'interface': self._interface,
            'ip': HOTSPOT_IP,
            'domain': self._domain,
            'url': f'http://{self._domain}' if self._is_active else None
        }
    
    def get_domain(self) -> str:
        """Get the configured local domain for hotspot access."""
        return self._domain
    
    def get_connected_clients(self) -> list:
        """
        Get list of connected clients (if available).
        
        Returns:
            list: Connected client information
        """
        # This is a best-effort attempt to get connected clients
        # Use ip neigh on Linux to only get REACHABLE or STALE clients,
        # ignoring old FAILED or INCOMPLETE arp cache entries.
        clients = []
        
        try:
            # Try to read from ip neigh (Linux)
            result = subprocess.run(
                ['ip', 'neigh', 'show', 'dev', self._interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    # Match entries like: 10.42.0.123 lladdr aa:bb:cc:dd:ee:ff REACHABLE
                    if '10.42.0.' in line and '10.42.0.1 ' not in line:
                        parts = line.split()
                        # Only count if state is REACHABLE or STALE (recently seen)
                        if len(parts) >= 5 and parts[-1] in ['REACHABLE', 'STALE', 'DELAY']:
                            clients.append({
                                'ip': parts[0],
                                'mac': parts[4] if parts[3] == 'lladdr' else 'unknown'
                            })
                            
            # Fallback for non-Linux or if ip command fails
            if not clients:
                result = subprocess.run(
                    ['arp', '-a'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if '10.42.0.' in line and '10.42.0.1' not in line:
                            # Only include Dynamic/active looking IPs in windows fallback
                            if 'dynamic' in line.lower() or 'ether' in line.lower():
                                parts = line.split()
                                if len(parts) >= 3:
                                    clients.append({
                                        'ip': parts[0] if not parts[0].startswith('(') else parts[1].strip('()'),
                                        'mac': parts[1] if not parts[0].startswith('(') else parts[3]
                                    })
        except:
            pass
        
        return clients


# Singleton instance
_hotspot_manager: Optional[HotspotManager] = None


def get_hotspot_manager(config=None) -> HotspotManager:
    """
    Get the singleton HotspotManager instance.
    
    Args:
        config: Config object (only used on first call)
        
    Returns:
        HotspotManager: The singleton instance
    """
    global _hotspot_manager
    if _hotspot_manager is None:
        _hotspot_manager = HotspotManager(config)
    return _hotspot_manager
