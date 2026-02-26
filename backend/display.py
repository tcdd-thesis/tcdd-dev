#!/usr/bin/env python3
"""
Display Brightness Controller
Controls Waveshare 2.8" LCD backlight via GPIO PWM
Supports Raspberry Pi GPIO and fallback for development environments
"""

import logging
from threading import Lock

logger = logging.getLogger(__name__)

# Try importing GPIO library for Raspberry Pi
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    logger.warning("RPi.GPIO not available, display brightness control will be simulated")


class DisplayController:
    """
    Controls Waveshare 2.8" LCD backlight brightness via PWM
    
    Default configuration for Waveshare 2.8" displays:
    - Backlight pin: GPIO 18 (PWM0 hardware PWM capable)
    - PWM frequency: 1000 Hz (smooth dimming)
    """
    
    # Default GPIO pin for Waveshare 2.8" LCD backlight
    DEFAULT_BACKLIGHT_PIN = 18
    DEFAULT_PWM_FREQUENCY = 1000  # Hz
    
    def __init__(self, config=None):
        """
        Initialize display controller
        
        Args:
            config: Configuration object with display settings
        """
        self.config = config
        self._lock = Lock()
        self._pwm = None
        self._initialized = False
        self._current_brightness = 100  # Default to full brightness
        
        # Get configuration values
        if config:
            self._backlight_pin = config.get('display.backlight_pin', self.DEFAULT_BACKLIGHT_PIN)
            self._pwm_frequency = config.get('display.pwm_frequency', self.DEFAULT_PWM_FREQUENCY)
            self._current_brightness = config.get('display.brightness', 100)
        else:
            self._backlight_pin = self.DEFAULT_BACKLIGHT_PIN
            self._pwm_frequency = self.DEFAULT_PWM_FREQUENCY
        
        self._initialize()
    
    def _initialize(self):
        """Initialize GPIO and PWM for backlight control"""
        if not HAS_GPIO:
            logger.info("Display controller initialized in simulation mode (no GPIO)")
            self._initialized = True
            return True
        
        try:
            # Set GPIO mode (use BCM numbering)
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup backlight pin as output
            GPIO.setup(self._backlight_pin, GPIO.OUT)
            
            # Create PWM instance
            self._pwm = GPIO.PWM(self._backlight_pin, self._pwm_frequency)
            
            # Start PWM with current brightness
            self._pwm.start(self._current_brightness)
            
            self._initialized = True
            logger.info(f"Display controller initialized on GPIO {self._backlight_pin}")
            logger.info(f"   Brightness: {self._current_brightness}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize display controller: {e}")
            self._initialized = False
            return False
    
    def set_brightness(self, brightness):
        """
        Set display backlight brightness
        
        Args:
            brightness: Brightness level 0-100 (percentage)
                       0 = backlight off
                       100 = maximum brightness
        
        Returns:
            bool: True if successful
        """
        # Clamp brightness to valid range
        brightness = max(0, min(100, int(brightness)))
        
        with self._lock:
            if not self._initialized:
                logger.warning("Display controller not initialized, cannot set brightness")
                return False
            
            try:
                if HAS_GPIO and self._pwm:
                    self._pwm.ChangeDutyCycle(brightness)
                
                self._current_brightness = brightness
                logger.info(f"🔆 Display brightness set to {brightness}%")
                
                # Save to config if available
                if self.config:
                    self.config.set('display.brightness', brightness, save=True)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to set brightness: {e}")
                return False
    
    def get_brightness(self):
        """
        Get current display brightness
        
        Returns:
            int: Current brightness level (0-100)
        """
        return self._current_brightness
    
    def is_available(self):
        """
        Check if display brightness control is available
        
        Returns:
            bool: True if GPIO control is available
        """
        return HAS_GPIO
    
    def is_initialized(self):
        """
        Check if display controller is initialized
        
        Returns:
            bool: True if initialized successfully
        """
        return self._initialized
    
    def cleanup(self):
        """Clean up GPIO resources"""
        with self._lock:
            try:
                if HAS_GPIO and self._pwm:
                    self._pwm.stop()
                    # Only cleanup our pin to avoid affecting other GPIO usage
                    GPIO.cleanup(self._backlight_pin)
                    logger.info("Display controller cleaned up")
            except Exception as e:
                logger.warning(f"Error during display cleanup: {e}")
            finally:
                self._initialized = False
                self._pwm = None
    
    def __del__(self):
        """Destructor to ensure GPIO cleanup"""
        self.cleanup()


# Alternative sysfs-based controller for displays that support it
class SysfsBacklightController:
    """
    Alternative backlight controller using sysfs interface
    Used for displays that expose /sys/class/backlight interface
    """
    
    BACKLIGHT_PATHS = [
        '/sys/class/backlight/rpi_backlight/brightness',
        '/sys/class/backlight/10-0045/brightness',
        '/sys/class/backlight/backlight/brightness',
    ]
    
    def __init__(self, config=None):
        """Initialize sysfs backlight controller"""
        self.config = config
        self._path = None
        self._max_brightness = 255
        self._current_brightness = 100
        
        self._find_backlight()
    
    def _find_backlight(self):
        """Find available backlight sysfs path"""
        import os
        
        for path in self.BACKLIGHT_PATHS:
            if os.path.exists(path):
                self._path = path
                # Read max brightness
                max_path = path.replace('/brightness', '/max_brightness')
                if os.path.exists(max_path):
                    try:
                        with open(max_path, 'r') as f:
                            self._max_brightness = int(f.read().strip())
                    except:
                        pass
                logger.info(f"Found sysfs backlight at: {path}")
                return True
        
        logger.warning("No sysfs backlight interface found")
        return False
    
    def set_brightness(self, brightness):
        """Set brightness (0-100 percentage)"""
        if not self._path:
            return False
        
        try:
            # Convert percentage to device value
            value = int((brightness / 100.0) * self._max_brightness)
            
            with open(self._path, 'w') as f:
                f.write(str(value))
            
            self._current_brightness = brightness
            logger.info(f"🔆 Display brightness set to {brightness}%")
            return True
            
        except PermissionError:
            logger.error("Permission denied writing to backlight. Try: sudo chmod 666 " + self._path)
            return False
        except Exception as e:
            logger.error(f"Failed to set sysfs brightness: {e}")
            return False
    
    def get_brightness(self):
        """Get current brightness (0-100)"""
        return self._current_brightness
    
    def is_available(self):
        """Check if sysfs control is available"""
        return self._path is not None
