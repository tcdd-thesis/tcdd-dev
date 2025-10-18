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
    if (pageName === 'logs') { loadViolations(); }
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

// ---------------------------------------------------------------------------
// VIOLATIONS (Violation-centric logs for users)
// ---------------------------------------------------------------------------

async function loadViolations() {
    try {
        const response = await api.get('/violations?limit=100');
        const container = document.getElementById('violations-list');
        if (!container) return;

        const events = response.violations || [];
        if (!events.length) {
            container.innerHTML = `
                <div class="log-empty">
                    <span class="icon">\u26A0</span>
                    <div>No violations recorded</div>
                    <small style="color: #888; margin-top: 8px;">Violations will appear here when detected</small>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        // Reverse to show newest first
        for (const ev of events.reverse()) {
            container.appendChild(renderViolationCard(ev));
        }
    } catch (err) {
        console.error('Failed to load violations:', err);
        const container = document.getElementById('violations-list');
        if (container) {
            container.innerHTML = `
                <div class="log-empty">
                    <span class="icon">\u26A0</span>
                    <div>Could not load violations</div>
                </div>
            `;
        }
    }
}

function renderViolationCard(ev) {
    const card = document.createElement('div');
    card.className = `violation-card severity-${(ev.severity||'low')}`;
    card.style.cursor = 'pointer';  // Ensure cursor shows it's clickable
    
    // Parse timestamp
    const timestamp = new Date(ev.timestamp);
    const timeStr = timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const dateStr = timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    
    // Violation type display
    const violationType = (ev.violation_type || 'unknown').replace(/_/g, ' ');
    const violationIcon = getViolationIcon(ev.violation_type);
    
    // Driver action display
    const actionIcon = ev.driver_action === 'wrong' ? '\u2715' : ev.driver_action === 'right' ? '\u2713' : '\u003F';
    const actionClass = ev.driver_action === 'wrong' ? 'action-wrong' : ev.driver_action === 'right' ? 'action-right' : 'action-unknown';
    
    // Confidence
    const confidence = Math.round((ev.confidence || 0) * 100);
    
    // Location
    const location = ev.context?.road_name || ev.context?.camera_id || 'Unknown location';
    
    card.innerHTML = `
        <div class="violation-card-header">
            <div class="violation-icon">${violationIcon}</div>
            <div class="violation-main">
                <div class="violation-type">${violationType}</div>
                <div class="violation-location">${location}</div>
            </div>
            <div class="violation-meta">
                <div class="violation-time">${timeStr}</div>
                <div class="violation-date">${dateStr}</div>
            </div>
        </div>
        <div class="violation-card-footer">
            <div class="violation-badge">
                <span class="badge-label">Confidence:</span>
                <span class="badge-value">${confidence}%</span>
            </div>
            <div class="violation-badge ${actionClass}">
                <span class="badge-label">Action:</span>
                <span class="badge-value">${actionIcon} ${ev.driver_action || 'unknown'}</span>
            </div>
            <div class="violation-badge">
                <span class="badge-label">Vehicle:</span>
                <span class="badge-value">${ev.vehicle?.track_id || 'N/A'}</span>
            </div>
        </div>
    `;
    
    // Click to show details - simple handler
    card.addEventListener('click', function(e) {
        console.log('Violation card clicked:', ev.id, ev);
        showViolationDetail(ev);
    });
    
    return card;
}

function getViolationIcon(type) {
    const icons = {
        'overspeed': '\u26A1',        // ⚡ Lightning bolt
        'red_light': '\u25CF',        // ● Red circle
        'stop_sign': '\u26D4',        // ⛔ No entry
        'wrong_way': '\u26A0',        // ⚠ Warning sign
        'illegal_turn': '\u21AA',     // ↪ Turn arrow
        'lane_departure': '\u2194',   // ↔ Left-right arrow
        'tailgating': '\u25A0',       // ■ Square (car representation)
        'none': '\u2713'              // ✓ Check mark
    };
    return icons[type] || '\u25A1'; // □ Empty square as fallback
}

function showViolationDetail(ev) {
    console.log('showViolationDetail called with:', ev);
    
    const modal = document.getElementById('violation-detail-modal');
    const content = document.getElementById('violation-detail-content');
    
    console.log('Modal element:', modal);
    console.log('Content element:', content);
    
    if (!modal || !content) {
        console.error('Modal or content element not found!');
        return;
    }
    
    // Parse timestamp
    const timestamp = new Date(ev.timestamp);
    const fullTimeStr = timestamp.toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    
    // Build detail HTML
    let detailHTML = `
        <div class="detail-section">
            <h4>Basic Information</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">ID:</span>
                    <span class="detail-value">${ev.id || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Timestamp:</span>
                    <span class="detail-value">${fullTimeStr}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Violation Type:</span>
                    <span class="detail-value violation-badge-${ev.severity}">${(ev.violation_type || 'unknown').replace(/_/g, ' ')}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Severity:</span>
                    <span class="detail-value severity-badge severity-${ev.severity}">${ev.severity || 'low'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Confidence:</span>
                    <span class="detail-value">${Math.round((ev.confidence || 0) * 100)}%</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Driver Action:</span>
                    <span class="detail-value action-${ev.driver_action}">${ev.driver_action || 'unknown'} (${Math.round((ev.action_confidence || 0) * 100)}%)</span>
                </div>
            </div>
        </div>
    `;
    
    // Vehicle info
    if (ev.vehicle) {
        detailHTML += `
            <div class="detail-section">
                <h4>Vehicle</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Track ID:</span>
                        <span class="detail-value">${ev.vehicle.track_id || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Context
    if (ev.context) {
        detailHTML += `
            <div class="detail-section">
                <h4>Context</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Camera ID:</span>
                        <span class="detail-value">${ev.context.camera_id || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Frame ID:</span>
                        <span class="detail-value">${ev.context.frame_id || 'N/A'}</span>
                    </div>
                    ${ev.context.road_name ? `
                    <div class="detail-item">
                        <span class="detail-label">Road:</span>
                        <span class="detail-value">${ev.context.road_name}</span>
                    </div>
                    ` : ''}
                    ${ev.context.location ? `
                    <div class="detail-item">
                        <span class="detail-label">Location:</span>
                        <span class="detail-value">${ev.context.location.lat}, ${ev.context.location.lon}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    // Evidence
    if (ev.evidence) {
        detailHTML += `
            <div class="detail-section">
                <h4>Evidence</h4>
                <div class="detail-grid">
        `;
        
        // Overspeed evidence
        if (ev.evidence.speed !== undefined) {
            detailHTML += `
                <div class="detail-item">
                    <span class="detail-label">Speed:</span>
                    <span class="detail-value">${ev.evidence.speed} km/h</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Speed Limit:</span>
                    <span class="detail-value">${ev.evidence.speed_limit} km/h</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Exceeded By:</span>
                    <span class="detail-value detail-highlight">${ev.evidence.delta_speed} km/h</span>
                </div>
            `;
        }
        
        // Red light evidence
        if (ev.evidence.signal_state) {
            detailHTML += `
                <div class="detail-item">
                    <span class="detail-label">Signal State:</span>
                    <span class="detail-value">${ev.evidence.signal_state}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Time Since Red:</span>
                    <span class="detail-value">${ev.evidence.time_since_red}s</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Crossed Stop Line:</span>
                    <span class="detail-value">${ev.evidence.crossed_stop_line ? 'Yes' : 'No'}</span>
                </div>
            `;
        }
        
        // Stop sign evidence
        if (ev.evidence.stopped !== undefined) {
            detailHTML += `
                <div class="detail-item">
                    <span class="detail-label">Stopped:</span>
                    <span class="detail-value">${ev.evidence.stopped ? 'Yes' : 'No'}</span>
                </div>
                ${ev.evidence.stop_duration_s !== undefined ? `
                <div class="detail-item">
                    <span class="detail-label">Stop Duration:</span>
                    <span class="detail-value">${ev.evidence.stop_duration_s}s</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Required:</span>
                    <span class="detail-value">${ev.evidence.required_stop_s}s</span>
                </div>
                ` : ''}
            `;
        }
        
        // Sign detected
        if (ev.evidence.sign_detected) {
            detailHTML += `
                <div class="detail-item">
                    <span class="detail-label">Sign Detected:</span>
                    <span class="detail-value">${ev.evidence.sign_detected.label} (${Math.round((ev.evidence.sign_detected.conf || 0) * 100)}%)</span>
                </div>
            `;
        }
        
        // Media links
        if (ev.evidence.snapshot_url) {
            detailHTML += `
                <div class="detail-item full-width">
                    <span class="detail-label">Snapshot:</span>
                    <a href="${ev.evidence.snapshot_url}" target="_blank" class="detail-link">View Image</a>
                </div>
            `;
        }
        if (ev.evidence.clip_url) {
            detailHTML += `
                <div class="detail-item full-width">
                    <span class="detail-label">Video Clip:</span>
                    <a href="${ev.evidence.clip_url}" target="_blank" class="detail-link">Watch Video</a>
                </div>
            `;
        }
        
        detailHTML += `
                </div>
            </div>
        `;
    }
    
    // Thresholds
    if (ev.thresholds) {
        detailHTML += `
            <div class="detail-section">
                <h4>Thresholds</h4>
                <div class="detail-grid">
        `;
        for (const [key, value] of Object.entries(ev.thresholds)) {
            detailHTML += `
                <div class="detail-item">
                    <span class="detail-label">${key.replace(/_/g, ' ')}:</span>
                    <span class="detail-value">${value}</span>
                </div>
            `;
        }
        detailHTML += `
                </div>
            </div>
        `;
    }
    
    // Review status
    if (ev.review) {
        detailHTML += `
            <div class="detail-section">
                <h4>Review</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value status-${ev.review.status}">${ev.review.status || 'auto'}</span>
                    </div>
                    ${ev.review.reviewer ? `
                    <div class="detail-item">
                        <span class="detail-label">Reviewer:</span>
                        <span class="detail-value">${ev.review.reviewer}</span>
                    </div>
                    ` : ''}
                    ${ev.review.notes ? `
                    <div class="detail-item full-width">
                        <span class="detail-label">Notes:</span>
                        <span class="detail-value">${ev.review.notes}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    // Model info
    if (ev.model) {
        detailHTML += `
            <div class="detail-section">
                <h4>Model Information</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Engine:</span>
                        <span class="detail-value">${ev.model.engine || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Model Version:</span>
                        <span class="detail-value">${ev.model.model_version || ev.model.model || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    content.innerHTML = detailHTML;
    modal.style.display = 'flex';
    console.log('Modal displayed, style.display:', modal.style.display);
}

function closeViolationDetail() {
    const modal = document.getElementById('violation-detail-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function clearViolationsDisplay() {
    const container = document.getElementById('violations-list');
    if (container) {
        container.innerHTML = `
            <div class="log-empty">
                <span class="icon">\u2713</span>
                <div>Display cleared</div>
            </div>
        `;
    }
    showToast('Display cleared', 'info');
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
    document.getElementById('btn-refresh-logs').addEventListener('click', loadViolations);
    document.getElementById('btn-clear-display').addEventListener('click', clearViolationsDisplay);
    
    // Modal close handlers
    const modal = document.getElementById('violation-detail-modal');
    if (modal) {
        // Close button
        const closeBtn = modal.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeViolationDetail);
        }
        
        // Click outside modal to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeViolationDetail();
            }
        });
    }
    
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
