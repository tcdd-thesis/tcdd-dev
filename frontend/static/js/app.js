/**
 * Sign Detection System - Touchscreen Application
 * Optimized for 2.8" LCD (640x480)
 */

// Global state
const state = {
    streaming: false,
    socket: null,
    currentPage: 'home',
    fps: 0,
    detectionCount: 0,
    config: null,
    configAutoReload: true
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
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Navigation
function goHome() {
    // Stop camera if streaming
    if (state.streaming) {
        stopCamera();
    }
    
    switchPage('home');
}

function switchPage(pageName) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    document.getElementById(`page-${pageName}`).classList.add('active');
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
// LOGS PAGE (User-Friendly Version)
// ============================================================================

async function loadLogs() {
    try {
        const response = await api.get('/logs?limit=100');
        const logsContainer = document.getElementById('logs-content-friendly');
        
        if (response.logs && response.logs.length > 0) {
            logsContainer.innerHTML = '';
            
            // Parse and format logs
            response.logs.forEach(logLine => {
                const entry = parseLogLine(logLine);
                if (entry) {
                    logsContainer.appendChild(createLogEntry(entry));
                }
            });
            
            // Scroll to bottom
            logsContainer.scrollTop = logsContainer.scrollHeight;
        } else {
            logsContainer.innerHTML = `
                <div class="log-empty">
                    <span class="icon">📋</span>
                    <div>No activity yet</div>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Failed to load logs:', error);
        const logsContainer = document.getElementById('logs-content-friendly');
        logsContainer.innerHTML = `
            <div class="log-empty">
                <span class="icon">⚠️</span>
                <div>Could not load activity log</div>
            </div>
        `;
    }
}

function parseLogLine(logLine) {
    // Parse log format: "2025-10-17 12:04:44,454 - module - LEVEL - message"
    const match = logLine.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - (.+?) - (\w+) - (.+)/);
    
    if (match) {
        const [, timestamp, module, level, message] = match;
        return {
            timestamp,
            module,
            level,
            message: formatMessage(message, level)
        };
    }
    
    return null;
}

function formatMessage(message, level) {
    // Make messages more user-friendly
    const friendlyMessages = {
        'Initializing camera': '📹 Starting camera...',
        'Camera started': '✅ Camera ready',
        'Camera stopped': '⏹️ Camera stopped',
        'Initializing OpenCV VideoCapture': '📹 Setting up camera',
        'Sign Detection System Starting': '🚀 System starting...',
        'Registered config change callback': '⚙️ Configuration loaded',
        'Config file reloaded': '🔄 Settings updated',
        'Camera resolution changed': '📐 Resolution updated',
        'Detection started': '🎯 Detection active',
        'Detection stopped': '⏸️ Detection paused',
        'Model loaded': '🤖 AI model ready',
        'Frame captured': '📸 Image saved',
        'Server starting': '🌐 Server starting...',
        'WebSocket connected': '🔌 Connected',
        'WebSocket disconnected': '🔌 Disconnected',
    };
    
    // Check for exact matches
    for (const [key, friendly] of Object.entries(friendlyMessages)) {
        if (message.includes(key)) {
            return friendly;
        }
    }
    
    // Check for patterns
    if (message.includes('FPS')) return `📊 ${message}`;
    if (message.includes('detected')) return `🎯 ${message}`;
    if (message.includes('error') || message.includes('Error')) return `❌ ${message}`;
    if (message.includes('warning') || message.includes('Warning')) return `⚠️ ${message}`;
    if (message.includes('success') || message.includes('Success')) return `✅ ${message}`;
    
    return message;
}

function createLogEntry(entry) {
    const div = document.createElement('div');
    const levelClass = entry.level.toLowerCase();
    div.className = `log-entry ${levelClass}`;
    
    // Format time (show only HH:MM:SS)
    const time = entry.timestamp.split(' ')[1];
    
    div.innerHTML = `
        <div class="log-time">${time}</div>
        <div class="log-message">${entry.message}</div>
    `;
    
    return div;
}

function clearLogsDisplay() {
    const logsContainer = document.getElementById('logs-content-friendly');
    logsContainer.innerHTML = `
        <div class="log-empty">
            <span class="icon">✨</span>
            <div>Display cleared</div>
        </div>
    `;
    showToast('Display cleared', 'info');
}

// ============================================================================
// SETTINGS PAGE
// ============================================================================

async function loadSettings() {
    try {
        const response = await api.get('/config');
        state.config = response.config || response;
        const config = state.config;
        
        // Resolution dropdown
        const resolution = `${config.camera?.width || 640}x${config.camera?.height || 480}`;
        const resolutionSelect = document.getElementById('setting-resolution');
        if (resolutionSelect) {
            resolutionSelect.value = resolution;
        }
        
        // FPS dropdown
        const fpsSelect = document.getElementById('setting-fps');
        if (fpsSelect) {
            fpsSelect.value = config.camera?.fps || 30;
        }
        
        // Confidence slider
        const confidence = config.detection?.confidence || 0.5;
        const confidenceSlider = document.getElementById('setting-confidence');
        const confidenceDisplay = document.getElementById('confidence-display');
        if (confidenceSlider && confidenceDisplay) {
            confidenceSlider.value = Math.round(confidence * 100);
            confidenceDisplay.textContent = Math.round(confidence * 100) + '%';
        }
        
        showToast('Settings loaded', 'success');
        
    } catch (error) {
        console.error('Failed to load settings:', error);
        showToast('Failed to load settings', 'error');
    }
}

async function saveSettings() {
    try {
        // Parse resolution
        const resolution = document.getElementById('setting-resolution').value.split('x');
        const width = parseInt(resolution[0]);
        const height = parseInt(resolution[1]);
        
        // Get FPS
        const fps = parseInt(document.getElementById('setting-fps').value);
        
        // Get confidence
        const confidence = parseFloat(document.getElementById('setting-confidence').value) / 100;
        
        const config = {
            camera: {
                width: width,
                height: height,
                fps: fps
            },
            detection: {
                confidence: confidence
            }
        };
        
        showToast('Saving...', 'info');
        const response = await api.put('/config', config);
        
        state.config = response.config;
        showToast('Settings saved!', 'success');
        
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('Save failed', 'error');
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
    
    // Menu buttons - Home page navigation
    document.querySelectorAll('.menu-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.getAttribute('data-page');
            switchPage(page);
        });
    });
    
    // Live Feed controls
    document.getElementById('btn-start').addEventListener('click', startCamera);
    document.getElementById('btn-stop').addEventListener('click', stopCamera);
    document.getElementById('btn-capture').addEventListener('click', captureFrame);
    
    // Driving Mode buttons
    document.getElementById('btn-casual-mode').addEventListener('click', () => {
        showToast('Casual Mode - Coming Soon!', 'info');
        // TODO: Implement casual driving mode
    });
    
    document.getElementById('btn-gamified-mode').addEventListener('click', () => {
        showToast('Gamified Mode - Coming Soon!', 'info');
        // TODO: Implement gamified driving mode
    });
    
    // Logs controls
    document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);
    document.getElementById('btn-clear-display').addEventListener('click', clearLogsDisplay);
    
    // Settings controls
    document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
    document.getElementById('btn-load-settings').addEventListener('click', loadSettings);
    
    // Confidence slider update
    document.getElementById('setting-confidence').addEventListener('input', (e) => {
        const value = e.target.value;
        document.getElementById('confidence-display').textContent = value + '%';
    });
    
    // Connect WebSocket
    connectWebSocket();
    
    // Initial status check
    checkStatus();
    
    // Periodic status check
    setInterval(checkStatus, 10000);
    
    // Start on home page
    switchPage('home');
    
    console.log('✓ Application ready!');
});
