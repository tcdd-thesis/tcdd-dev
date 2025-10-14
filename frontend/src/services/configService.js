/**
 * Frontend configuration service
 * Loads configuration from backend API endpoint
 */

const DEFAULT_CONFIG = {
  detection: {
    pollIntervalMs: 500,
    maxDetectionsDisplay: 5,
    confidenceThreshold: 0.5
  },
  display: {
    fullscreen: false,
    optimizedForPi: true,
    theme: 'dark'
  },
  camera: {
    width: 640,
    height: 480,
    fps: 30
  }
};

class ConfigService {
  constructor() {
    this.config = DEFAULT_CONFIG;
    this.loaded = false;
  }

  /**
   * Load configuration from backend API
   */
  async loadConfig() {
    const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
    
    try {
      const response = await fetch(`${API_URL}/api/config`);
      if (response.ok) {
        this.config = await response.json();
        this.loaded = true;
        console.log('✓ Configuration loaded from backend');
        return this.config;
      }
    } catch (error) {
      console.warn('Could not load config from backend, using defaults:', error.message);
    }
    
    // Fall back to defaults
    this.config = DEFAULT_CONFIG;
    this.loaded = true;
    return this.config;
  }

  /**
   * Get configuration value using dot notation
   */
  get(key, defaultValue = undefined) {
    const keys = key.split('.');
    let value = this.config;
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return defaultValue;
      }
    }
    
    return value;
  }

  getPollInterval() {
    return this.get('detection.pollIntervalMs', 500);
  }

  getMaxDetectionsDisplay() {
    return this.get('detection.maxDetectionsDisplay', 5);
  }

  getConfidenceThreshold() {
    return this.get('detection.confidenceThreshold', 0.5);
  }

  getTheme() {
    return this.get('display.theme', 'dark');
  }

  /**
   * Ensure config is loaded before accessing
   */
  async ensureLoaded() {
    if (!this.loaded) {
      await this.loadConfig();
    }
    return this.config;
  }
}

// Export singleton instance
const configService = new ConfigService();
export default configService;
