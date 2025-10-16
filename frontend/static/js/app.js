/**
 * Sign Detection System - Main Application
 * Vanilla JavaScript - No frameworks required
 */

// Global state
const state = {
    streaming: false,
    socket: null,
    currentPage: 'live',
    fps: 0,
    detectionCount: 0,
    config: null,
    configAutoReload: true  // Auto-reload config from server
};

// API helper
const api = {
    baseUrl: '/api',
    
    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    },
    
    async post(endpoint, data = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    },
    
    async put(endpoint, data = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }
};

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Page Navigation
function switchPage(pageName) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(`page-${pageName}`).classList.add('active');
    document.querySelector(`[data-page="${pageName}"]`).classList.add('active');
    
    state.currentPage = pageName;
    
    // Load page-specific content
    if (pageName === 'logs') loadLogs();
    if (pageName === 'settings') loadSettings();
}

// ============================================================================
// LIVE FEED PAGE
// ============================================================================

async function startCamera() {
    try {
        showToast('Starting camera...', 'info');
        await api.post('/camera/start');
        
        state.streaming = true;
        document.getElementById('btn-start').disabled = true;
        document.getElementById('btn-stop').disabled = false;
        document.getElementById('btn-capture').disabled = false;
        document.getElementById('no-feed').style.display = 'none';
        
        showToast('Camera started!', 'success');
        
    } catch (error) {
        console.error('Failed to start camera:', error);
        showToast('Failed to start camera', 'error');
    }
}

async function stopCamera() {
    try {
        showToast('Stopping camera...', 'info');
        await api.post('/camera/stop');
        
        state.streaming = false;
        document.getElementById('btn-start').disabled = false;
        document.getElementById('btn-stop').disabled = true;
        document.getElementById('btn-capture').disabled = true;
        document.getElementById('no-feed').style.display = 'flex';
        
        showToast('Camera stopped', 'success');
        
    } catch (error) {
        console.error('Failed to stop camera:', error);
        showToast('Failed to stop camera', 'error');
    }
}

function captureFrame() {
    const canvas = document.getElementById('video-canvas');
    const link = document.createElement('a');
    link.download = `capture_${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
    showToast('Frame captured!', 'success');
}

function handleVideoFrame(data) {
    const canvas = document.getElementById('video-canvas');
    const ctx = canvas.getContext('2d');
    
    const img = new Image();
    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        // Update stats
        state.detectionCount = data.count || 0;
        document.getElementById('detection-count').textContent = state.detectionCount;
    };
    img.src = 'data:image/jpeg;base64,' + data.frame;
    
    // Calculate FPS
    if (!state.lastFrameTime) state.lastFrameTime = Date.now();
    const now = Date.now();
    const delta = now - state.lastFrameTime;
    state.fps = Math.round(1000 / delta);
    document.getElementById('fps-value').textContent = state.fps;
    state.lastFrameTime = now;
}

// ============================================================================
// LOGS PAGE
// ============================================================================

async function loadLogs() {
    try {
        const response = await api.get('/logs?limit=200');
        const logsContent = document.getElementById('logs-content');
        
        if (response.logs && response.logs.length > 0) {
            const filter = document.getElementById('log-level-filter').value;
            let logs = response.logs;
            
            if (filter) {
                logs = logs.filter(log => log.includes(filter));
            }
            
            logsContent.textContent = logs.join('');
            logsContent.scrollTop = logsContent.scrollHeight;
        } else {
            logsContent.textContent = 'No logs available';
        }
        
    } catch (error) {
        console.error('Failed to load logs:', error);
        document.getElementById('logs-content').textContent = 'Error loading logs';
    }
}

function clearLogsDisplay() {
    document.getElementById('logs-content').textContent = 'Logs cleared';
    showToast('Display cleared', 'info');
}

// ============================================================================
// SETTINGS PAGE
// ============================================================================

async function loadSettings() {
    try {
        const response = await api.get('/config');
        state.config = response.config || response;  // Handle both old and new format
        const config = state.config;
        
        // Display metadata if available
        if (response.metadata) {
            console.log('Config metadata:', response.metadata);
            const metadataDiv = document.getElementById('config-metadata');
            if (metadataDiv) {
                metadataDiv.innerHTML = `
                    <small>
                        Last modified: ${response.metadata.last_modified || 'Unknown'}<br>
                        File: ${response.metadata.file}<br>
                        Active callbacks: ${response.metadata.callbacks_registered || 0}
                    </small>
                `;
            }
        }
        
        // Camera settings
        document.getElementById('setting-width').value = config.camera?.width || 640;
        document.getElementById('setting-height').value = config.camera?.height || 480;
        document.getElementById('setting-fps').value = config.camera?.fps || 30;
        
        // Detection settings
        const confidence = config.detection?.confidence || 0.5;
        document.getElementById('setting-confidence').value = confidence * 100;
        document.getElementById('confidence-display').textContent = confidence.toFixed(2);
        document.getElementById('setting-model').value = config.detection?.model || '';
        
        // System settings
        document.getElementById('setting-port').value = config.port || 5000;
        document.getElementById('setting-debug').checked = config.debug || false;
        
        // Update live stats
        document.getElementById('model-name').textContent = config.detection?.model?.split('/').pop() || 'Unknown';
        document.getElementById('confidence-value').textContent = `${Math.round(confidence * 100)}%`;
        
    } catch (error) {
        console.error('Failed to load settings:', error);
        showToast('Failed to load settings', 'error');
    }
}

async function saveSettings() {
    try {
        const confidence = parseFloat(document.getElementById('setting-confidence').value) / 100;
        
        const config = {
            port: parseInt(document.getElementById('setting-port').value),
            debug: document.getElementById('setting-debug').checked,
            camera: {
                width: parseInt(document.getElementById('setting-width').value),
                height: parseInt(document.getElementById('setting-height').value),
                fps: parseInt(document.getElementById('setting-fps').value)
            },
            detection: {
                model: document.getElementById('setting-model').value,
                confidence: confidence
            }
        };
        
        showToast('Saving configuration...', 'info');
        const response = await api.put('/config', config);
        
        // Update state with new config
        state.config = response.config;
        
        showToast('✅ Settings saved and applied!', 'success');
        console.log('Configuration saved:', response);
        
        // Update live display
        document.getElementById('confidence-value').textContent = `${Math.round(confidence * 100)}%`;
        if (response.config) {
            document.getElementById('model-name').textContent = config.detection?.model?.split('/').pop() || 'Unknown';
        }
        
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('❌ Failed to save settings', 'error');
    }
}

async function reloadConfig() {
    try {
        showToast('Reloading configuration from file...', 'info');
        const response = await api.post('/config/reload');
        
        state.config = response.config;
        
        if (state.currentPage === 'settings') {
            loadSettings();
        }
        
        showToast(response.message, 'success');
        console.log('Configuration reloaded:', response);
        
    } catch (error) {
        console.error('Failed to reload config:', error);
        showToast('❌ Failed to reload config', 'error');
    }
}

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

function connectWebSocket() {
    state.socket = io();
    
    state.socket.on('connect', () => {
        console.log('WebSocket connected');
        document.getElementById('status-dot').className = 'dot online';
        document.getElementById('status-text').textContent = 'Online';
        showToast('Connected to server', 'success');
    });
    
    state.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        document.getElementById('status-dot').className = 'dot offline';
        document.getElementById('status-text').textContent = 'Offline';
        showToast('Disconnected from server', 'warning');
    });
    
    state.socket.on('video_frame', (data) => {
        if (state.currentPage === 'live') {
            handleVideoFrame(data);
        }
    });
    
    state.socket.on('connection_response', (data) => {
        console.log('Connection response:', data);
    });
    
    // Listen for config updates from server
    state.socket.on('config_updated', (data) => {
        console.log('🔄 Configuration updated from server:', data);
        
        if (state.configAutoReload) {
            state.config = data.config;
            
            // Update UI if on settings page
            if (state.currentPage === 'settings') {
                loadSettings();
            }
            
            showToast('Configuration updated automatically', 'info');
        }
    });
}

// ============================================================================
// SYSTEM STATUS
// ============================================================================

async function checkStatus() {
    try {
        const status = await api.get('/status');
        
        if (status.model) {
            document.getElementById('model-name').textContent = status.model.split('/').pop();
        }
        
    } catch (error) {
        console.error('Failed to check status:', error);
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Sign Detection System...');
    
    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            switchPage(e.target.dataset.page);
        });
    });
    
    // Live Feed controls
    document.getElementById('btn-start').addEventListener('click', startCamera);
    document.getElementById('btn-stop').addEventListener('click', stopCamera);
    document.getElementById('btn-capture').addEventListener('click', captureFrame);
    
    // Logs controls
    document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);
    document.getElementById('btn-clear-display').addEventListener('click', clearLogsDisplay);
    document.getElementById('log-level-filter').addEventListener('change', loadLogs);
    
    // Settings controls
    document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
    document.getElementById('btn-load-settings').addEventListener('click', loadSettings);
    document.getElementById('btn-reload-config').addEventListener('click', reloadConfig);
    
    // Confidence slider update
    document.getElementById('setting-confidence').addEventListener('input', (e) => {
        const value = (e.target.value / 100).toFixed(2);
        document.getElementById('confidence-display').textContent = value;
    });
    
    // Connect WebSocket
    connectWebSocket();
    
    // Initial status check
    checkStatus();
    
    // Periodic status check
    setInterval(checkStatus, 10000);
    
    console.log('✓ Application ready!');
});
