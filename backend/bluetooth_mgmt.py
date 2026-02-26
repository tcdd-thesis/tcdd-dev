import subprocess
import logging
import time
import re

logger = logging.getLogger(__name__)

class BluetoothManager:
    """Wrapper around bluetoothctl and pactl for managing Bluetooth audio."""
    
    def __init__(self, config=None):
        self.config = config
        self.enabled = config.get("bluetooth.enabled", False) if config else False
        self.preferred_mac = config.get("bluetooth.preferred_mac", "") if config else ""
        self.auto_connect = config.get("bluetooth.auto_connect", True) if config else True
        
        if self.enabled:
            logger.info("Initializing Bluetooth Manager...")
            # Ensure bluetooth agent is running and we are pairable
            self._run_cmd(["bluetoothctl", "power", "on"])
            self._run_cmd(["bluetoothctl", "agent", "on"])
            self._run_cmd(["bluetoothctl", "default-agent"])
            
            if self.auto_connect and self.preferred_mac:
                logger.info(f"Attempting auto-connect to default Bluetooth device {self.preferred_mac}")
                self.connect(self.preferred_mac)

    def _run_cmd(self, args, timeout=10):
        """Run a shell command and return its output and status."""
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1
        except Exception as e:
            return "", str(e), -2

    def status(self):
        """Check if connected, and if so, to what."""
        out, _, code = self._run_cmd(["bluetoothctl", "info"])
        if code != 0 or "Missing device address" in out:
            return {"connected": False, "device": None, "mac": None}
            
        connected_match = re.search(r"Connected:\s+(yes|no)", out, re.IGNORECASE)
        name_match = re.search(r"Name:\s+(.*)", out)
        mac_match = re.search(r"Device\s+([A-F0-9:]+)", out)
        
        is_connected = connected_match and connected_match.group(1).lower() == "yes"
        
        return {
            "connected": is_connected,
            "device": name_match.group(1).strip() if name_match else "Unknown",
            "mac": mac_match.group(1).strip() if mac_match else None
        }

    def scan(self, duration=5):
        """Scan for nearby Bluetooth devices."""
        logger.info(f"Scanning for Bluetooth devices for {duration} seconds...")
        
        # Start scanning
        self._run_cmd(["bluetoothctl", "scan", "on"])
        time.sleep(duration)
        self._run_cmd(["bluetoothctl", "scan", "off"])
        
        # Parse the available devices
        out, err, code = self._run_cmd(["bluetoothctl", "devices"])
        if code != 0:
            logger.error(f"Failed to get bluetooth devices: {err}")
            return []
            
        devices = []
        for line in out.strip().split("\n"):
            if not line: continue
            
            # Line format: Device XX:XX:XX:XX:XX:XX Name...
            parts = line.split(" ", 2)
            if len(parts) >= 3 and parts[0] == "Device":
                mac = parts[1]
                name = parts[2]
                devices.append({
                    "mac": mac,
                    "name": name,
                    # We can use info to see if we've already trusted/paired it
                    "known": self._is_known(mac)
                })
        return devices

    def _is_known(self, mac):
        """Check if a device is paired/trusted."""
        out, _, _ = self._run_cmd(["bluetoothctl", "info", mac])
        paired = re.search(r"Paired:\s+yes", out, re.IGNORECASE)
        trusted = re.search(r"Trusted:\s+yes", out, re.IGNORECASE)
        return bool(paired or trusted)

    def connect(self, mac):
        """Pair (if needed), trust, and connect to a device. Then route audio."""
        logger.info(f"Attempting to connect to Bluetooth device: {mac}")
        
        if not self._is_known(mac):
            logger.info(f"Device {mac} is new. Attempting to pair and trust.")
            # Often, audio devices don't need a PIN, so this blind pair works
            out, err, code = self._run_cmd(["bluetoothctl", "pair", mac], timeout=15)
            if "AuthenticationFailed" in out or "Failed to pair" in out:
                return False, f"Pairing failed: {out.strip()}"
            self._run_cmd(["bluetoothctl", "trust", mac])
            
        out, err, code = self._run_cmd(["bluetoothctl", "connect", mac], timeout=15)
        
        if "Connection successful" in out or "already connected" in out.lower():
            # Force PulseAudio/Pipewire to use this sink
            self._set_pulse_sink()
            
            if self.config:
                 self.config.set("bluetooth.preferred_mac", mac, save=True)
                 
            return True, "Connected successfully"
            
        return False, f"Connection failed: {out.strip()} {err.strip()}"

    def disconnect(self, mac):
        """Disconnect a device."""
        logger.info(f"Disconnecting from Bluetooth device: {mac}")
        out, err, code = self._run_cmd(["bluetoothctl", "disconnect", mac])
        
        if "Successful disconnected" in out or "not connected" in out:
            return True, "Disconnected"
        return False, f"Disconnect failed: {out.strip()} {err.strip()}"

    def _set_pulse_sink(self):
        """Tell PulseAudio/Pipewire to route audio to the newly connected Bluetooth sink."""
        # Give PulseAudio a moment to register the new sink
        time.sleep(2)
        
        out, err, code = self._run_cmd(["pactl", "list", "short", "sinks"])
        if code != 0:
            logger.warning(f"Failed to list pulseaudio sinks: {err}")
            return
            
        # Look for the bluez sink
        sink_name = None
        for line in out.strip().split("\n"):
            if "bluez_sink" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    sink_name = parts[1]
                    break
                    
        if sink_name:
            logger.info(f"Setting default audio sink to {sink_name}")
            self._run_cmd(["pactl", "set-default-sink", sink_name])
        else:
            logger.warning("No bluez sink found after connection.")

# Factory function similar to what we do for hotspot
_bluetooth_manager_instance = None
def get_bluetooth_manager(config=None):
    global _bluetooth_manager_instance
    if _bluetooth_manager_instance is None:
        _bluetooth_manager_instance = BluetoothManager(config)
    return _bluetooth_manager_instance
