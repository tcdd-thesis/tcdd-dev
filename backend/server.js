const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const { attachSocket } = require('./utils/socketHandler');
const config = require('./utils/configLoader');

const app = express();

// Optimized CORS configuration
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  credentials: true
}));

app.use(express.json({ limit: '1mb' }));

// Proxy configuration - from config.json or environment variables
const PYTHON_SERVER = process.env.PYTHON_SERVER || config.getPythonServerUrl();
const PROXY_TIMEOUT = parseInt(process.env.PROXY_TIMEOUT || '30000', 10);

// Video feed proxy with optimized settings
app.use('/video_feed', createProxyMiddleware({
  target: PYTHON_SERVER,
  changeOrigin: true,
  ws: false,
  logLevel: 'warn',
  timeout: PROXY_TIMEOUT,
  proxyTimeout: PROXY_TIMEOUT,
  onError: (err, req, res) => {
    console.error('Video feed proxy error:', err.message);
    res.status(503).send('Camera service unavailable');
  }
}));

// Detection API proxy with caching headers
app.use('/api/python', createProxyMiddleware({
  target: PYTHON_SERVER,
  changeOrigin: true,
  pathRewrite: { '^/api/python': '/api' },
  logLevel: 'warn',
  timeout: 10000,
  onProxyRes: (proxyRes, req, res) => {
    // Add caching headers for status endpoint
    if (req.path.includes('/status')) {
      proxyRes.headers['cache-control'] = 'public, max-age=2';
    }
  },
  onError: (err, req, res) => {
    console.error('API proxy error:', err.message);
    res.status(503).json({ 
      ok: false, 
      error: 'Detection service unavailable',
      message: err.message 
    });
  }
}));

// Health check endpoint with detailed info
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    pythonServer: PYTHON_SERVER
  });
});

// Config endpoint - serve configuration to frontend
app.get('/api/config', (req, res) => {
  try {
    res.json({
      detection: {
        pollIntervalMs: config.get('detection.pollIntervalMs'),
        maxDetectionsDisplay: config.get('detection.maxDetectionsDisplay'),
        confidenceThreshold: config.get('detection.confidenceThreshold')
      },
      display: config.get('display'),
      camera: config.getCameraConfig()
    });
  } catch (error) {
    console.error('Error serving config:', error);
    res.status(500).json({ error: 'Failed to load configuration' });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Express error:', err);
  res.status(500).json({
    ok: false,
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

const PORT = process.env.PORT || config.getBackendPort();
const server = app.listen(PORT, () => {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Backend Server Started`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Listening on port:     ${PORT}`);
  console.log(`Proxying Python from:  ${PYTHON_SERVER}`);
  console.log(`Configuration loaded:  shared/config.json`);
  console.log(`${'='.repeat(60)}\n`);
});

// attach socket.io (optional)
attachSocket(server);

// Watch for config changes
config.watchConfig((newConfig) => {
  console.log('⚠ Configuration updated. Restart server to apply changes to ports.');
});

module.exports = app;
