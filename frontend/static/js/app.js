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
    configAutoReload: true,
    recording: false,
    recordingStartTime: null,
    recordingTimer: null,
    status: {
        wifi: false,
        camera: false
    }    
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
    },
    
    async delete(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'DELETE'
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
        updateStatus('camera', true);
        
        showToast('Camera started!', 'success');
        
    } catch (error) {
        console.error('Failed to start camera:', error);
        showToast('Failed to start camera', 'error');
        updateStatus('camera', false);        
    }
}

async function stopCamera() {
    try {
        showToast('Stopping camera...', 'info');
        await api.post('/camera/stop');
        
        state.streaming = false;
        document.getElementById('no-feed').style.display = 'flex';
        updateStatus('camera', false);        
        
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

// ============================================================================
// RECORDING FUNCTIONS
// ============================================================================

async function startRecording() {
    try {
        showToast('Starting recording...', 'info');
        const response = await api.post('/recording/start');
        
        state.recording = true;
        state.recordingStartTime = Date.now();
        
        // Update UI
        const btn = document.getElementById('btn-record');
        btn.classList.add('recording');
        btn.title = 'Stop Recording';
        
        // Show timer
        document.getElementById('recording-timer').style.display = 'flex';
        
        // Start timer update
        state.recordingTimer = setInterval(updateRecordingTimer, 1000);
        
        showToast(`Recording started: ${response.filename}`, 'success');
        
    } catch (error) {
        console.error('Failed to start recording:', error);
        showToast('Failed to start recording', 'error');
    }
}

async function stopRecording() {
    try {
        showToast('Stopping recording...', 'info');
        const response = await api.post('/recording/stop');
        
        state.recording = false;
        state.recordingStartTime = null;
        
        // Clear timer
        if (state.recordingTimer) {
            clearInterval(state.recordingTimer);
            state.recordingTimer = null;
        }
        
        // Update UI
        const btn = document.getElementById('btn-record');
        btn.classList.remove('recording');
        btn.title = 'Start Recording';
        
        // Hide timer
        document.getElementById('recording-timer').style.display = 'none';
        document.getElementById('recording-time').textContent = '00:00';
        
        showToast(`Recording saved: ${response.filename}`, 'success');
        
    } catch (error) {
        console.error('Failed to stop recording:', error);
        showToast('Failed to stop recording', 'error');
    }
}

function toggleRecording() {
    if (state.recording) {
        stopRecording();
    } else {
        startRecording();
    }
}

function updateRecordingTimer() {
    if (!state.recordingStartTime) return;
    
    const elapsed = Math.floor((Date.now() - state.recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    
    document.getElementById('recording-time').textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    // Check if approaching max duration (15 minutes = 900 seconds)
    if (elapsed >= 900) {
        // Recording will be auto-stopped by backend
        state.recording = false;
        state.recordingStartTime = null;
        if (state.recordingTimer) {
            clearInterval(state.recordingTimer);
            state.recordingTimer = null;
        }
        
        const btn = document.getElementById('btn-record');
        btn.classList.remove('recording');
        btn.title = 'Start Recording';
        
        document.getElementById('recording-timer').style.display = 'none';
        document.getElementById('recording-time').textContent = '00:00';
        
        showToast('Recording auto-stopped (max duration)', 'info');
    }
}

async function checkRecordingStatus() {
    try {
        const response = await api.get('/recording/status');
        
        if (response.recording && !state.recording) {
            // Sync state with backend
            state.recording = true;
            state.recordingStartTime = Date.now() - (response.elapsed_seconds * 1000);
            
            const btn = document.getElementById('btn-record');
            btn.classList.add('recording');
            btn.title = 'Stop Recording';
            
            document.getElementById('recording-timer').style.display = 'flex';
            
            if (!state.recordingTimer) {
                state.recordingTimer = setInterval(updateRecordingTimer, 1000);
            }
        }
    } catch (error) {
        console.error('Failed to check recording status:', error);
    }
}

// ============================================================================
// RECORDINGS MANAGEMENT
// ============================================================================

async function loadRecordings() {
    try {
        const response = await api.get('/recordings');
        const recordings = response.recordings || [];
        
        // Update header
        document.getElementById('recordings-count').textContent = `${recordings.length} recording${recordings.length !== 1 ? 's' : ''}`;
        document.getElementById('recordings-size').textContent = `${response.total_size_mb} MB`;
        
        const container = document.getElementById('recordings-list');
        
        if (recordings.length === 0) {
            container.innerHTML = '<div class="recordings-empty">No recordings yet</div>';
            return;
        }
        
        container.innerHTML = '';
        
        for (const rec of recordings) {
            const item = document.createElement('div');
            item.className = 'recording-item';
            
            // Parse timestamp from filename
            const timestamp = rec.filename.replace('recording_', '').replace('.mp4', '').replace('_', ' ');
            
            item.innerHTML = `
                <div class="recording-info">
                    <span class="recording-name">${rec.filename}</span>
                    <span class="recording-meta">${rec.size_mb} MB</span>
                </div>
                <div class="recording-actions">
                    <button class="btn btn-small btn-primary" onclick="playRecording('${rec.filename}')" title="Play">▶</button>
                    <button class="btn btn-small btn-danger" onclick="deleteRecording('${rec.filename}')" title="Delete">✕</button>
                </div>
            `;
            
            container.appendChild(item);
        }
        
    } catch (error) {
        console.error('Failed to load recordings:', error);
        showToast('Failed to load recordings', 'error');
    }
}

function playRecording(filename) {
    const modal = document.getElementById('video-modal');
    const video = document.getElementById('video-player');
    const source = document.getElementById('video-source');
    const title = document.getElementById('video-title');
    
    title.textContent = filename;
    source.src = `/api/recordings/${filename}`;
    video.load();
    
    modal.style.display = 'flex';
    video.play();
}

function closeVideoModal() {
    const modal = document.getElementById('video-modal');
    const video = document.getElementById('video-player');
    
    video.pause();
    modal.style.display = 'none';
}

async function deleteRecording(filename) {
    showConfirm(
        'Delete Recording',
        `Are you sure you want to delete "${filename}"? This cannot be undone.`,
        async () => {
            try {
                await api.delete(`/recordings/${filename}`);
                showToast(`Deleted ${filename}`, 'success');
                loadRecordings();
            } catch (error) {
                console.error('Failed to delete recording:', error);
                showToast('Failed to delete recording', 'error');
            }
        }
    );
}

// ============================================================================
// SYSTEM CONTROL FUNCTIONS
// ============================================================================

function shutdownApp() {
    showConfirm(
        'Shutdown Application',
        'Are you sure you want to shutdown the application? The camera will stop and you will need to manually restart the app.',
        async () => {
            try {
                showToast('Shutting down application...', 'info');
                await api.post('/system/shutdown-app');
            } catch (error) {
                // Expected - connection will be lost
                console.log('App shutdown initiated');
            }
        }
    );
}

function shutdownPi() {
    showConfirm(
        'Shutdown Raspberry Pi',
        'Are you sure you want to shutdown the Raspberry Pi? You will need physical access to turn it back on.',
        async () => {
            try {
                showToast('Shutting down Raspberry Pi...', 'warning');
                await api.post('/system/shutdown-pi');
            } catch (error) {
                // Expected - connection will be lost
                console.log('Pi shutdown initiated');
            }
        }
    );
}

function rebootPi() {
    showConfirm(
        'Reboot Raspberry Pi',
        'Are you sure you want to reboot the Raspberry Pi? The app will automatically restart after reboot.',
        async () => {
            try {
                showToast('Rebooting Raspberry Pi...', 'warning');
                await api.post('/system/reboot-pi');
            } catch (error) {
                // Expected - connection will be lost
                console.log('Pi reboot initiated');
            }
        }
    );
}

// ============================================================================
// CONFIRMATION MODAL
// ============================================================================

function showConfirm(title, message, onConfirm) {
    const modal = document.getElementById('confirm-modal');
    const titleEl = document.getElementById('confirm-title');
    const messageEl = document.getElementById('confirm-message');
    const cancelBtn = document.getElementById('confirm-cancel');
    const okBtn = document.getElementById('confirm-ok');
    
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    modal.style.display = 'flex';
    
    // Remove old listeners
    const newCancelBtn = cancelBtn.cloneNode(true);
    const newOkBtn = okBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    okBtn.parentNode.replaceChild(newOkBtn, okBtn);
    
    // Add new listeners
    newCancelBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    newOkBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        if (onConfirm) onConfirm();
    });
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
                    <span class="icon">\u2630</span>
                    <div>No activity yet</div>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Failed to load logs:', error);
        const logsContainer = document.getElementById('logs-content-friendly');
        logsContainer.innerHTML = `
            <div class="log-empty">
                <span class="icon">\u26A0</span>
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
        'Initializing camera': '\u25B6 Starting camera...',           // ▶ Play
        'Camera started': '\u2713 Camera ready',                      // ✓ Check
        'Camera stopped': '\u25A0 Camera stopped',                    // ■ Stop square
        'Initializing OpenCV VideoCapture': '\u25B6 Setting up camera', // ▶ Play
        'Sign Detection System Starting': '\u25B2 System starting...', // ▲ Up triangle
        'Registered config change callback': '\u2699 Configuration loaded', // ⚙ Gear
        'Config file reloaded': '\u21BB Settings updated',            // ↻ Reload
        'Camera resolution changed': '\u25A1 Resolution updated',     // □ Square
        'Detection started': '\u25CF Detection active',               // ● Bullet
        'Detection stopped': '\u25A0 Detection paused',               // ■ Square
        'Model loaded': '\u2713 AI model ready',                      // ✓ Check
        'Frame captured': '\u25A0 Image saved',                       // ■ Square
        'Server starting': '\u25CF Server starting...',               // ● Bullet
        'WebSocket connected': '\u2713 Connected',                    // ✓ Check
        'WebSocket disconnected': '\u2715 Disconnected',              // ✕ X mark
    };
    
    // Check for exact matches
    for (const [key, friendly] of Object.entries(friendlyMessages)) {
        if (message.includes(key)) {
            return friendly;
        }
    }
    
    // Check for patterns
    if (message.includes('FPS')) return `\u25BA ${message}`;          // ▸ Small triangle
    if (message.includes('detected')) return `\u25CF ${message}`;     // ● Bullet
    if (message.includes('error') || message.includes('Error')) return `\u2715 ${message}`; // ✕ X
    if (message.includes('warning') || message.includes('Warning')) return `\u26A0 ${message}`; // ⚠ Warning
    if (message.includes('success') || message.includes('Success')) return `\u2713 ${message}`; // ✓ Check
    
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
            <span class="icon">\u2713</span>
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
        
        // Load recordings list
        loadRecordings();
        
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
        updateStatus('backend', true);
        showToast('Connected to server', 'success');
        // Check full system status
        checkSystemStatus();        
    });
    
    state.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        updateStatus('backend', false);
        updateStatus('camera', false);
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
        console.log('\u21BB Configuration updated from server:', data);
        
        if (state.configAutoReload) {
            state.config = data.config;
            
            // Update UI if on settings page
            if (state.currentPage === 'settings') {
                loadSettings();
            }
            
            showToast('Configuration updated automatically', 'info');
        }
    });
    
    // Listen for recording auto-stop
    state.socket.on('recording_stopped', (data) => {
        console.log('Recording auto-stopped:', data);
        
        state.recording = false;
        state.recordingStartTime = null;
        
        if (state.recordingTimer) {
            clearInterval(state.recordingTimer);
            state.recordingTimer = null;
        }
        
        const btn = document.getElementById('btn-record');
        if (btn) {
            btn.classList.remove('recording');
            btn.title = 'Start Recording';
        }
        
        const timer = document.getElementById('recording-timer');
        if (timer) timer.style.display = 'none';
        
        const timeDisplay = document.getElementById('recording-time');
        if (timeDisplay) timeDisplay.textContent = '00:00';
        
        showToast(`Recording saved: ${data.filename}`, 'success');
    });
}

// ============================================================================
// SYSTEM STATUS
// ============================================================================

function updateStatus(component, isOnline) {
    state.status[component] = isOnline;
    
    const statusElement = document.getElementById(`status-${component}`);
    if (!statusElement) return;
    
    const dot = statusElement.querySelector('.status-dot');
    
    if (isOnline) {
        dot.className = 'status-dot dot online';
        statusElement.classList.add('connected');
    } else {
        dot.className = 'status-dot dot offline';
        statusElement.classList.remove('connected');
    }
}

async function checkWiFiStatus() {
    // Check WiFi by trying to reach the backend
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        
        await fetch('/api/status', { 
            signal: controller.signal,
            cache: 'no-cache'
        });
        
        clearTimeout(timeoutId);
        updateStatus('wifi', true);
        return true;
    } catch (error) {
        updateStatus('wifi', false);
        return false;
    }
}

async function checkSystemStatus() {
    try {
        // Check WiFi
        const hasWiFi = await checkWiFiStatus();
        
        if (!hasWiFi) {
            updateStatus('backend', false);
            updateStatus('camera', false);
            return;
        }
        
        // Check backend and camera
        const status = await api.get('/status');
        
        updateStatus('backend', true);
        updateStatus('camera', status.camera || false);
        
        // Update model info if available        
        if (status.model) {
            const modelElement = document.getElementById('model-name');
            if (modelElement) {
                modelElement.textContent = status.model.split('/').pop();
            }
        }
        
    } catch (error) {
        console.error('Failed to check status:', error);
        updateStatus('backend', false);
        updateStatus('camera', false);        
    }
}

// Legacy function for backward compatibility
async function checkStatus() {
    await checkSystemStatus();
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
    
    // System control buttons
    document.getElementById('btn-shutdown-app').addEventListener('click', shutdownApp);
    document.getElementById('btn-shutdown-pi').addEventListener('click', shutdownPi);
    document.getElementById('btn-reboot-pi').addEventListener('click', rebootPi);
    
    // Recording button
    document.getElementById('btn-record').addEventListener('click', toggleRecording);
    
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
    
    // Video modal close on outside click
    const videoModal = document.getElementById('video-modal');
    if (videoModal) {
        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) {
                closeVideoModal();
            }
        });
    }
    
    // Confirm modal close on outside click
    const confirmModal = document.getElementById('confirm-modal');
    if (confirmModal) {
        confirmModal.addEventListener('click', (e) => {
            if (e.target === confirmModal) {
                confirmModal.style.display = 'none';
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
    checkSystemStatus();
    checkRecordingStatus();
    
    // Periodic status checks
    setInterval(checkSystemStatus, 5000);  // Check every 5 seconds
    
    // Start on home page
    switchPage('home');
    
    console.log('\u2713 Application ready!');
});
