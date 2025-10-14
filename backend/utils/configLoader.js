const fs = require('fs');
const path = require('path');

/**
 * Configuration loader utility for Node.js backend
 * Loads and provides access to shared/config.json
 */
class ConfigLoader {
  constructor(configPath = '../../shared/config.json') {
    this.configPath = path.join(__dirname, configPath);
    this.config = null;
    this.loadConfig();
  }

  loadConfig() {
    try {
      const configData = fs.readFileSync(this.configPath, 'utf8');
      this.config = JSON.parse(configData);
      console.log('✓ Configuration loaded from:', this.configPath);
    } catch (error) {
      console.error('⚠ Error loading configuration:', error.message);
      console.warn('Using default configuration values');
      this.config = this.getDefaultConfig();
    }
  }

  getDefaultConfig() {
    return {
      backendPort: 5000,
      pythonServerPort: 5001,
      frontendPort: 3000,
      camera: {
        width: 640,
        height: 480,
        fps: 30,
        bufferSize: 1
      },
      detection: {
        modelPath: 'backend/python/model/best.pt',
        confidenceThreshold: 0.5,
        pollIntervalMs: 500,
        maxDetectionsDisplay: 5,
        detectionInterval: 1,
        jpegQuality: 80
      },
      display: {
        fullscreen: false,
        optimizedForPi: true,
        theme: 'dark'
      },
      performance: {
        enableGPU: false,
        modelFormat: 'pt',
        maxCacheSize: 100,
        compressionLevel: 6
      }
    };
  }

  get(key) {
    const keys = key.split('.');
    let value = this.config;
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return undefined;
      }
    }
    
    return value;
  }

  getBackendPort() {
    return this.get('backendPort') || 5000;
  }

  getPythonServerPort() {
    return this.get('pythonServerPort') || 5001;
  }

  getPythonServerUrl() {
    return `http://localhost:${this.getPythonServerPort()}`;
  }

  getCameraConfig() {
    return this.get('camera') || this.getDefaultConfig().camera;
  }

  getDetectionConfig() {
    return this.get('detection') || this.getDefaultConfig().detection;
  }

  watchConfig(callback) {
    if (fs.existsSync(this.configPath)) {
      fs.watch(this.configPath, (eventType) => {
        if (eventType === 'change') {
          console.log('⚠ Configuration file changed, reloading...');
          this.loadConfig();
          if (callback) callback(this.config);
        }
      });
      console.log('✓ Watching configuration file for changes');
    }
  }
}

// Export singleton instance
module.exports = new ConfigLoader();
