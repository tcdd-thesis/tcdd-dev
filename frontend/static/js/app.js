// ============================================================================
// HOTSPOT TOGGLE LOGIC
// ============================================================================

/**
 * Toggle hotspot on/off via the button.
 * Reads current state from the button label text.
 */
function toggleHotspotUI() {
    const label = document.getElementById('hotspot-toggle-label');
    const isCurrentlyEnabled = label && label.textContent.trim().startsWith('Disable');

    if (isCurrentlyEnabled) {
        // Stop hotspot
        api.post('/hotspot/stop')
            .then(res => {
                if (res.success) {
                    showToast('Hotspot disabled. Reconnecting WiFi...', 'info');
                    updateHotspotUI(false);
                    // Backend auto-reconnects WiFi; refresh status after delay
                    setTimeout(() => {
                        loadWifiStatus();
                        checkWiFiStatus();
                    }, 3000);
                } else {
                    showToast('Failed to stop hotspot', 'error');
                }
            })
            .catch(err => {
                showToast('Failed to disable hotspot', 'error');
            });
    } else {
        // Prompt user about WiFi disconnect before enabling
        showHotspotPrompt();
    }
}

function showHotspotPrompt() {
    const modal = document.getElementById('hotspot-prompt-modal');
    if (modal) modal.style.display = 'flex';
}

function closeHotspotPrompt() {
    const modal = document.getElementById('hotspot-prompt-modal');
    if (modal) modal.style.display = 'none';
}

function confirmHotspotEnable() {
    closeHotspotPrompt();
    showToast('Starting hotspot...', 'info');

    // Enable + start hotspot
    api.post('/hotspot/toggle', { enabled: true })
        .then(() => api.post('/hotspot/start'))
        .then(result => {
            if (result.success) {
                showToast('Hotspot enabled!', 'success');
                updateHotspotUI(true, result.ssid);
                // WiFi is now disconnected — update WiFi UI
                loadWifiStatus();
                checkWiFiStatus();
            } else {
                showToast(result.message || 'Failed to start hotspot', 'error');
            }
        })
        .catch(err => {
            showToast('Failed to enable hotspot', 'error');
        });
}

/**
 * Update hotspot UI elements (button label, status text, SSID)
 */
function updateHotspotUI(active, ssid) {
    const label = document.getElementById('hotspot-toggle-label');
    const statusText = document.getElementById('hotspot-status-text');
    const ssidSpan = document.getElementById('hotspot-ssid');

    if (label) label.textContent = active ? 'Disable Hotspot' : 'Enable Hotspot';
    if (statusText) {
        statusText.textContent = active ? 'Active' : 'Inactive';
        statusText.classList.toggle('active', !!active);
    }
    if (ssidSpan && ssid) ssidSpan.textContent = ssid;
}

/**
 * Load current hotspot status from backend and update UI.
 * Called from loadSettings().
 */
function loadHotspotStatus() {
    api.get('/hotspot/status').then(status => {
        updateHotspotUI(status.active, status.ssid);
        const ssidSpan = document.getElementById('hotspot-ssid');
        if (ssidSpan) ssidSpan.textContent = status.ssid || '---';
    }).catch(err => {
        console.error('Failed to load hotspot status:', err);
        const statusText = document.getElementById('hotspot-status-text');
        if (statusText) statusText.textContent = 'Unavailable';
    });
}

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
    brightness: 50, // Default brightness (0-100)
    status: {
        wifi: false,
        camera: false
    },
    // Track original settings for unsaved changes detection
    originalSettings: {
        brightness: 50,
        confidence: 50
    }
};

// ============================================================================
// TOUCH SCROLL IMPLEMENTATION  
// ============================================================================

/**
 * Initialize touch scrolling for an element (simplified version)
 * Uses direct DOM manipulation for maximum compatibility
 */
function initTouchScroll(element) {
    if (!element) return;
    if (element.dataset.touchScrollInit) return;
    element.dataset.touchScrollInit = 'true';

    let startY = 0;
    let scrollStart = 0;

    element.addEventListener('touchstart', function (e) {
        startY = e.touches[0].clientY;
        scrollStart = element.scrollTop;
    }, { passive: true });

    element.addEventListener('touchmove', function (e) {
        const touch = e.touches[0];
        const deltaY = startY - touch.clientY;
        element.scrollTop = scrollStart + deltaY;
    }, { passive: true });
}

/**
 * Initialize all scrollable containers
 * Only needed on touchscreen (RPi) — mobile uses native CSS scrolling
 */
function initAllTouchScrolling() {
    // Skip manual touch-scroll on non-touchscreen devices (mobile uses native scroll)
    if (!document.body.classList.contains('touchscreen')) {
        console.log('Non-touchscreen device: using native scrolling');
        return;
    }

    const scrollables = document.querySelectorAll(
        '.settings-container-compact, .violations-log-container, #wifi-networks-list, #wifi-saved-list, .modal-content'
    );
    scrollables.forEach(el => initTouchScroll(el));
    console.log('Touch scrolling initialized for', scrollables.length, 'elements');
}

// ============================================================================
// SCREEN BRIGHTNESS CONTROL (CSS Overlay Dimming)
// ============================================================================

/**
 * Set screen brightness using CSS overlay dimming and brightness filter
 * @param {number} brightness - Brightness level 0-100
 *   0 = darkest (heavy black overlay)
 *   50 = normal (no effect, native screen brightness)
 *   100 = brightest (200% brightness boost via CSS filter)
 */
function setScreenBrightness(brightness) {
    brightness = Math.max(0, Math.min(100, brightness));
    state.brightness = brightness;

    const overlay = document.getElementById('brightness-overlay');
    const body = document.body;

    if (brightness <= 50) {
        // 0-50%: Use black overlay for dimming
        // 0% = 0.9 opacity (very dark), 50% = 0 opacity (no dimming)
        const opacity = (50 - brightness) / 50 * 0.9;
        if (overlay) {
            overlay.style.opacity = opacity.toString();
            overlay.style.backgroundColor = '#000000';
        }
        // Remove brightness filter
        body.style.filter = '';
    } else {
        // 50-100%: Use CSS brightness filter for boosting
        // 50% = 1.0 (normal), 100% = 2.0 (double brightness)
        const filterValue = 1 + ((brightness - 50) / 50);
        body.style.filter = `brightness(${filterValue})`;
        // Hide overlay
        if (overlay) {
            overlay.style.opacity = '0';
        }
    }

    console.log(`Brightness: ${brightness}%`);
}

/**
 * Get current screen brightness
 * @returns {number} Current brightness level 0-100
 */
function getScreenBrightness() {
    return state.brightness;
}

// API helper
const api = {
    baseUrl: '/api',

    // Build headers with optional session token for mobile auth
    _headers() {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('tcdd_session_token');
        if (token) headers['X-Session-Token'] = token;
        return headers;
    },

    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            headers: this._headers()
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    },

    async post(endpoint, data = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: this._headers(),
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    },

    async put(endpoint, data = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: this._headers(),
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

// ============================================================================
// SHUTDOWN FUNCTIONS
// ============================================================================

function showShutdownConfirm() {
    const modal = document.getElementById('shutdown-confirm-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function cancelShutdown() {
    const modal = document.getElementById('shutdown-confirm-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function confirmShutdown() {
    // Hide confirmation modal
    const confirmModal = document.getElementById('shutdown-confirm-modal');
    if (confirmModal) {
        confirmModal.style.display = 'none';
    }

    // Show progress modal
    const progressModal = document.getElementById('shutdown-progress-modal');
    if (progressModal) {
        progressModal.style.display = 'flex';
    }

    try {
        await api.post('/shutdown');
        // The system will shut down after 2 seconds
        // Keep the progress modal visible
    } catch (error) {
        console.error('Shutdown request failed:', error);
        // Hide progress modal on error
        if (progressModal) {
            progressModal.style.display = 'none';
        }
        showToast('Shutdown failed: ' + error.message, 'error');
    }
}

// ============================================================================
// REBOOT FUNCTIONS
// ============================================================================

function showRebootConfirm() {
    const modal = document.getElementById('reboot-confirm-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function cancelReboot() {
    const modal = document.getElementById('reboot-confirm-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function confirmReboot() {
    // Hide confirmation modal
    const confirmModal = document.getElementById('reboot-confirm-modal');
    if (confirmModal) {
        confirmModal.style.display = 'none';
    }

    // Show progress modal
    const progressModal = document.getElementById('reboot-progress-modal');
    if (progressModal) {
        progressModal.style.display = 'flex';
    }

    try {
        await api.post('/reboot');
        // The system will reboot after 2 seconds
        // Keep the progress modal visible
    } catch (error) {
        console.error('Reboot request failed:', error);
        // Hide progress modal on error
        if (progressModal) {
            progressModal.style.display = 'none';
        }
        showToast('Reboot failed: ' + error.message, 'error');
    }
}

// ============================================================================
// CLOSE APP FUNCTIONS
// ============================================================================

function showCloseAppConfirm() {
    const modal = document.getElementById('closeapp-confirm-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function cancelCloseApp() {
    const modal = document.getElementById('closeapp-confirm-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function confirmCloseApp() {
    // Hide confirmation modal
    const confirmModal = document.getElementById('closeapp-confirm-modal');
    if (confirmModal) {
        confirmModal.style.display = 'none';
    }

    // Show progress modal
    const progressModal = document.getElementById('closeapp-progress-modal');
    if (progressModal) {
        progressModal.style.display = 'flex';
    }

    try {
        await api.post('/close-app');
        // Server will kill Chromium and itself
    } catch (error) {
        console.error('Close app request failed:', error);
        // Hide progress modal on error
        if (progressModal) {
            progressModal.style.display = 'none';
        }
        showToast('Close app failed: ' + error.message, 'error');
    }
}

// Navigation
function goHome() {
    // Stop camera if streaming
    if (state.streaming) {
        stopCamera();
    }

    // Check for unsaved settings changes
    if (state.currentPage === 'settings' && hasSettingsChanged()) {
        showUnsavedSettingsModal();
        return;
    }

    switchPage('home');
}

/**
 * Check if settings have been modified
 */
function hasSettingsChanged() {
    const brightnessSlider = document.getElementById('setting-brightness');
    const confidenceSlider = document.getElementById('setting-confidence');

    const currentBrightness = brightnessSlider ? parseInt(brightnessSlider.value) : state.originalSettings.brightness;
    const currentConfidence = confidenceSlider ? parseInt(confidenceSlider.value) : state.originalSettings.confidence;

    return currentBrightness !== state.originalSettings.brightness ||
        currentConfidence !== state.originalSettings.confidence;
}

/**
 * Show unsaved settings confirmation modal
 */
function showUnsavedSettingsModal() {
    const modal = document.getElementById('unsaved-settings-modal');
    if (modal) modal.style.display = 'flex';
}

/**
 * Save settings and go home
 */
async function saveSettingsAndGoHome() {
    const modal = document.getElementById('unsaved-settings-modal');
    if (modal) modal.style.display = 'none';

    await saveSettings();
    switchPage('home');
}

/**
 * Discard settings changes and go home
 */
function discardSettingsAndGoHome() {
    const modal = document.getElementById('unsaved-settings-modal');
    if (modal) modal.style.display = 'none';

    // Restore original brightness visually
    setScreenBrightness(state.originalSettings.brightness);

    switchPage('home');
}

/**
 * Cancel and stay on settings page
 */
function cancelUnsavedSettings() {
    const modal = document.getElementById('unsaved-settings-modal');
    if (modal) modal.style.display = 'none';
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

    // Re-initialize touch scrolling for newly visible containers
    setTimeout(initAllTouchScrolling, 100);
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
                    <span class="icon"><i class="fa-solid fa-bars"></i></span>
                    <div>No activity yet</div>
                </div>
            `;
        }

    } catch (error) {
        console.error('Failed to load logs:', error);
        const logsContainer = document.getElementById('logs-content-friendly');
        logsContainer.innerHTML = `
            <div class="log-empty">
                <span class="icon"><i class="fa-solid fa-triangle-exclamation"></i></span>
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
                    <span class="icon"><i class="fa-solid fa-shield-halved"></i></span>
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
                    <span class="icon"><i class="fa-solid fa-triangle-exclamation"></i></span>
                    <div>Could not load violations</div>
                </div>
            `;
        }
    }
}

function renderViolationCard(ev) {
    const card = document.createElement('div');
    card.className = `violation-card severity-${(ev.severity || 'low')}`;
    card.style.cursor = 'pointer';  // Ensure cursor shows it's clickable

    // Parse timestamp
    const timestamp = new Date(ev.timestamp);
    const timeStr = timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const dateStr = timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    // Violation type display
    const violationType = (ev.violation_type || 'unknown').replace(/_/g, ' ');
    const violationIcon = getViolationIcon(ev.violation_type);

    // Driver action display
    const actionIcon = ev.driver_action === 'wrong' ? '<i class="fa-solid fa-xmark"></i>' : ev.driver_action === 'right' ? '<i class="fa-solid fa-check"></i>' : '<i class="fa-solid fa-question"></i>';
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
    card.addEventListener('click', function (e) {
        console.log('Violation card clicked:', ev.id, ev);
        showViolationDetail(ev);
    });

    return card;
}

function getViolationIcon(type) {
    const icons = {
        'overspeed': '<i class="fa-solid fa-gauge-high"></i>',        // Speedometer
        'red_light': '<i class="fa-solid fa-circle" style="color:#e53935"></i>',  // Red circle
        'stop_sign': '<i class="fa-solid fa-hand"></i>',              // Stop hand
        'wrong_way': '<i class="fa-solid fa-triangle-exclamation"></i>', // Warning
        'illegal_turn': '<i class="fa-solid fa-arrow-turn-up"></i>',  // Turn arrow
        'lane_departure': '<i class="fa-solid fa-arrows-left-right"></i>', // Lane change
        'tailgating': '<i class="fa-solid fa-car-rear"></i>',         // Car rear
        'none': '<i class="fa-solid fa-check"></i>'                   // Check mark
    };
    return icons[type] || '<i class="fa-solid fa-question"></i>'; // Question as fallback
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
                <span class="icon"><i class="fa-solid fa-check"></i></span>
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
        'Initializing camera': '<i class="fa-solid fa-play"></i> Starting camera...',
        'Camera started': '<i class="fa-solid fa-check"></i> Camera ready',
        'Camera stopped': '<i class="fa-solid fa-stop"></i> Camera stopped',
        'Initializing OpenCV VideoCapture': '<i class="fa-solid fa-play"></i> Setting up camera',
        'Sign Detection System Starting': '<i class="fa-solid fa-arrow-up"></i> System starting...',
        'Registered config change callback': '<i class="fa-solid fa-gear"></i> Configuration loaded',
        'Config file reloaded': '<i class="fa-solid fa-rotate"></i> Settings updated',
        'Camera resolution changed': '<i class="fa-solid fa-display"></i> Resolution updated',
        'Detection started': '<i class="fa-solid fa-circle"></i> Detection active',
        'Detection stopped': '<i class="fa-solid fa-stop"></i> Detection paused',
        'Model loaded': '<i class="fa-solid fa-check"></i> AI model ready',
        'Frame captured': '<i class="fa-solid fa-image"></i> Image saved',
        'Server starting': '<i class="fa-solid fa-circle"></i> Server starting...',
        'WebSocket connected': '<i class="fa-solid fa-check"></i> Connected',
        'WebSocket disconnected': '<i class="fa-solid fa-xmark"></i> Disconnected',
    };

    // Check for exact matches
    for (const [key, friendly] of Object.entries(friendlyMessages)) {
        if (message.includes(key)) {
            return friendly;
        }
    }

    // Check for patterns
    if (message.includes('FPS')) return `<i class="fa-solid fa-caret-right"></i> ${message}`;
    if (message.includes('detected')) return `<i class="fa-solid fa-circle"></i> ${message}`;
    if (message.includes('error') || message.includes('Error')) return `<i class="fa-solid fa-xmark"></i> ${message}`;
    if (message.includes('warning') || message.includes('Warning')) return `<i class="fa-solid fa-triangle-exclamation"></i> ${message}`;
    if (message.includes('success') || message.includes('Success')) return `<i class="fa-solid fa-check"></i> ${message}`;

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
            <span class="icon"><i class="fa-solid fa-check"></i></span>
            <div>Display cleared</div>
        </div>
    `;
    showToast('Display cleared', 'info');
}

// ============================================================================
// DEVICE PAIRING
// ============================================================================

/**
 * Load and display current pairing status in the Settings page
 */
async function loadPairingStatus() {
    const badge = document.getElementById('pairing-status-badge');
    const infoDiv = document.getElementById('pairing-device-info');
    const nameSpan = document.getElementById('pairing-device-name');
    const unpairBtn = document.getElementById('btn-unpair');
    const generateBtn = document.getElementById('btn-start-pairing-wizard');

    try {
        const status = await api.get('/pair/status');

        if (status.is_paired && status.paired_device) {
            // Paired state
            badge.className = 'pairing-badge pairing-paired';
            badge.innerHTML = '<i class="fa-solid fa-circle"></i> Paired';
            if (infoDiv) infoDiv.style.display = 'block';
            if (nameSpan) nameSpan.textContent = status.paired_device.device_name || 'Unknown';
            if (unpairBtn) unpairBtn.style.display = 'inline-flex';
            if (generateBtn) {
                generateBtn.style.display = 'none'; // Hide Start Pairing when paired
            }
        } else {
            // Not paired state
            badge.className = 'pairing-badge pairing-unpaired';
            badge.innerHTML = '<i class="fa-solid fa-circle"></i> Not Paired';
            if (infoDiv) infoDiv.style.display = 'none';
            if (unpairBtn) unpairBtn.style.display = 'none';
            if (generateBtn) {
                generateBtn.style.display = 'inline-flex'; // Show Start Pairing when not paired
            }
        }
    } catch (error) {
        console.error('Failed to load pairing status:', error);
    }
}

/**
 * Unpair the currently paired device
 */
async function unpairDevice() {
    try {
        const result = await api.post('/pair/unpair');

        if (result.success) {
            showToast('Device unpaired', 'success');
            // Also stop the hotspot automatically to return to WiFi
            await api.post('/hotspot/stop').catch(e => console.warn('Failed to stop hotspot after unpair', e));
        } else {
            showToast(result.message || 'Nothing to unpair', 'info');
        }

        loadPairingStatus();
    } catch (error) {
        console.error('Failed to unpair:', error);
        showToast('Failed to unpair device', 'error');
    }
}

// ============================================================================
// PAIRING WIZARD LOGIC
// ============================================================================

let wizardPollingInterval = null;

async function startPairingWizard() {
    const modal = document.getElementById('pairing-wizard-modal');
    if (!modal) return;

    // Reset Wizard State
    setWizardStep(1);
    modal.style.display = 'flex';

    try {
        // Step 1: Start Hotspot
        // Auto-triggers API which now regenerates credentials automatically
        const response = await api.post('/hotspot/start', { force: true });

        if (response.success || response.ssid) {
            // Successfully started hotspot, setup Step 2 UI
            setupWizardStep2(response.ssid, response.password);
            setWizardStep(2);
        } else if (response.prompt) {
            // If it asks for confirmation (e.g. WiFi is connected)
            showToast('Disconnecting WiFi to enable Hotspot...', 'info');
            closePairingWizard();
            document.getElementById('hotspot-prompt-modal').style.display = 'flex';
        } else {
            throw new Error(response.message || 'Failed to start hotspot');
        }
    } catch (e) {
        console.error('Wizard Step 1 failed:', e);
        showToast('Failed to start hotspot for pairing', 'error');
        closePairingWizard();
    }
}

function setWizardStep(stepNum) {
    // Update Circles and Lines
    for (let i = 1; i <= 3; i++) {
        const circle = document.querySelector(`#wizard-step-${i} .step-circle`);
        const line = document.getElementById(`wizard-line-${i}`);

        if (circle) {
            circle.className = 'step-circle';
            if (i < stepNum) circle.classList.add('step-completed');
            if (i === stepNum) circle.classList.add('step-active');
        }

        if (line) {
            line.className = 'step-line';
            if (i < stepNum) line.classList.add('line-completed');
            if (i === stepNum) line.classList.add('line-active');
        }
    }

    // Show corresponding content
    for (let i = 1; i <= 3; i++) {
        const content = document.getElementById(`wizard-content-step${i}`);
        if (content) {
            if (i === stepNum) {
                content.style.display = 'block';
                content.classList.add('active');
            } else {
                content.style.display = 'none';
                content.classList.remove('active');
            }
        }
    }
}

function setupWizardStep2(ssid, password) {
    document.getElementById('wizard-hotspot-ssid').textContent = `SSID: ${ssid}`;
    document.getElementById('wizard-hotspot-password').textContent = `Password: ${password}`;

    const qrContainer = document.getElementById('wizard-hotspot-qr');
    // Random cache buster to ensure new QR is loaded since credentials change
    const cacheBuster = new Date().getTime();
    qrContainer.innerHTML = `<img src="/api/hotspot/qr?type=wifi&_t=${cacheBuster}" alt="WiFi QR">`;

    // Start polling for connected clients
    startClientPolling();
}

function startClientPolling() {
    stopPolling(); // Clear any existing

    wizardPollingInterval = setInterval(async () => {
        try {
            const res = await api.get('/hotspot/clients');
            if (res && res.count === 1) {
                // Exactly 1 client connected!
                stopPolling();
                wizardAdvanceToStep3();
            }
        } catch (e) {
            console.error('Polling clients failed', e);
        }
    }, 3000); // Poll every 3 seconds
}

function stopPolling() {
    if (wizardPollingInterval) {
        clearInterval(wizardPollingInterval);
        wizardPollingInterval = null;
    }
}

async function wizardAdvanceToStep3() {
    stopPolling(); // In case manual Next was clicked
    setWizardStep(3);

    try {
        const data = await api.post('/pair/generate');
        if (data.success) {
            document.getElementById('wizard-webapp-token').textContent = data.token;

            const url = data.url || data.ip_url || '';
            const ip = data.ip || '';
            const port = data.port || 5000;
            const finalUrl = url ? url : (ip ? `http://${ip}:${port}/pair` : '');

            document.getElementById('wizard-webapp-url').textContent = finalUrl;

            const qrContainer = document.getElementById('wizard-webapp-qr');
            qrContainer.innerHTML = `<img src="/api/pair/qr?token=${encodeURIComponent(data.token)}" alt="Web App QR">`;
        } else {
            throw new Error(data.error || 'Failed to generate code');
        }
    } catch (e) {
        console.error('Wizard Step 3 failed:', e);
        showToast('Failed to generate pairing token', 'error');
    }
}

function closePairingWizard() {
    stopPolling();
    const modal = document.getElementById('pairing-wizard-modal');
    if (modal) modal.style.display = 'none';
    loadPairingStatus();
}

// ============================================================================
// SETTINGS PAGE
// ============================================================================

async function loadSettings() {
    try {
        const response = await api.get('/config');
        state.config = response.config || response;
        const config = state.config;

        // Display brightness slider
        const brightness = config.display?.brightness ?? 50;
        const brightnessSlider = document.getElementById('setting-brightness');
        const brightnessDisplay = document.getElementById('brightness-display');
        if (brightnessSlider && brightnessDisplay) {
            brightnessSlider.value = brightness;
            brightnessDisplay.textContent = brightness + '%';
            // Apply brightness to screen
            setScreenBrightness(brightness);
        }

        // Confidence slider
        const confidence = config.detection?.confidence || 0.5;
        const confidenceSlider = document.getElementById('setting-confidence');
        const confidenceDisplay = document.getElementById('confidence-display');
        if (confidenceSlider && confidenceDisplay) {
            confidenceSlider.value = Math.round(confidence * 100);
            confidenceDisplay.textContent = Math.round(confidence * 100) + '%';
        }

        // Store original settings for change detection
        state.originalSettings.brightness = brightness;
        state.originalSettings.confidence = Math.round(confidence * 100);

        // Load WiFi status
        await loadWifiStatus();

        // Load hotspot status
        loadHotspotStatus();

        // Load pairing status
        await loadPairingStatus();

        // Load Bluetooth status
        loadBluetoothStatus();

    } catch (error) {
        console.error('Failed to load settings:', error);
        showToast('Failed to load settings', 'error');
    }
}

/**
 * Load and apply brightness on app startup (without showing toast)
 */
async function loadInitialBrightness() {
    try {
        const response = await api.get('/config');
        const config = response.config || response;
        const brightness = config.display?.brightness ?? 50;
        setScreenBrightness(brightness);
        console.log(`Brightness loaded from config: ${brightness}%`);
    } catch (error) {
        console.error('Failed to load brightness from config:', error);
        // Apply default brightness on error (50% = normal)
        setScreenBrightness(50);
    }
}

async function saveSettings() {
    try {
        // Get display brightness
        const brightness = parseInt(document.getElementById('setting-brightness').value);

        // Get confidence
        const confidence = parseFloat(document.getElementById('setting-confidence').value) / 100;

        const config = {
            display: {
                brightness: brightness
            },
            detection: {
                confidence: confidence
            }
        };

        showToast('Saving...', 'info');
        const response = await api.put('/config', config);

        state.config = response.config;

        // Update original settings after successful save
        state.originalSettings.brightness = brightness;
        state.originalSettings.confidence = Math.round(confidence * 100);

        showToast('Settings saved!', 'success');

    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('Save failed', 'error');
    }
}

/**
 * Reset settings to default values
 */
function resetToDefaults() {
    // Default values
    const defaultBrightness = 50;
    const defaultConfidence = 50;

    // Update sliders
    const brightnessSlider = document.getElementById('setting-brightness');
    const brightnessDisplay = document.getElementById('brightness-display');
    const confidenceSlider = document.getElementById('setting-confidence');
    const confidenceDisplay = document.getElementById('confidence-display');

    if (brightnessSlider && brightnessDisplay) {
        brightnessSlider.value = defaultBrightness;
        brightnessDisplay.textContent = defaultBrightness + '%';
        setScreenBrightness(defaultBrightness);
    }

    if (confidenceSlider && confidenceDisplay) {
        confidenceSlider.value = defaultConfidence;
        confidenceDisplay.textContent = defaultConfidence + '%';
    }

    showToast('Reset to defaults', 'info');
}

// ============================================================================
// WIFI MANAGEMENT
// ============================================================================

// WiFi state for connection handling
let wifiConnectingSsid = null;

/**
 * Get signal strength bars based on signal percentage
 * @param {number} signal - Signal strength 0-100
 * @returns {number} - Number of active bars (1-4)
 */
function getSignalBars(signal) {
    if (signal >= 70) return 4;      // Excellent
    if (signal >= 50) return 3;      // Good
    if (signal >= 30) return 2;      // Fair
    return 1;                         // Weak
}

/**
 * Generate signal bars HTML
 * @param {number} signal - Signal strength 0-100
 * @returns {string} - HTML for signal bars
 */
function renderSignalBars(signal) {
    const activeBars = getSignalBars(signal);
    const colorClass = activeBars >= 3 ? 'signal-strong' : (activeBars === 2 ? 'signal-medium' : 'signal-weak');

    let barsHtml = '';
    for (let i = 1; i <= 4; i++) {
        const isActive = i <= activeBars;
        barsHtml += `<span class="signal-bar bar-${i} ${isActive ? 'active' : ''}"></span>`;
    }

    return `<span class="signal-bars ${colorClass}" title="${signal}%">${barsHtml}</span>`;
}

/**
 * Load and display current WiFi connection status
 */
async function loadWifiStatus() {
    const statusText = document.getElementById('wifi-status-text');
    const disconnectBtn = document.getElementById('btn-wifi-disconnect');

    try {
        const response = await api.get('/wifi/status');

        if (response.connected && response.ssid) {
            const signal = response.signal || 0;
            statusText.innerHTML = `
                <span class="wifi-connected">
                    <i class="fa fa-wifi"></i> ${escapeHtml(response.ssid)}
                    ${renderSignalBars(signal)}
                </span>`;
            if (disconnectBtn) disconnectBtn.style.display = 'inline-block';
            updateStatus('wifi', true);
        } else {
            statusText.innerHTML = '<span class="wifi-disconnected"><i class="fa fa-wifi"></i> Not Connected</span>';
            if (disconnectBtn) disconnectBtn.style.display = 'none';
            updateStatus('wifi', false);
        }
    } catch (error) {
        console.error('Failed to load WiFi status:', error);
        statusText.innerHTML = '<span class="wifi-error"><i class="fa fa-exclamation-triangle"></i> Error</span>';
        if (disconnectBtn) disconnectBtn.style.display = 'none';
    }
}

/**
 * Scan for available WiFi networks
 */
async function scanWifiNetworks() {
    const listContainer = document.getElementById('wifi-networks-list');
    const scanBtn = document.getElementById('btn-scan-wifi');

    // Show the list container
    if (listContainer) listContainer.style.display = 'block';

    // Show loading state
    if (scanBtn) {
        scanBtn.disabled = true;
        scanBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Scanning...';
    }
    listContainer.innerHTML = '<div class="wifi-loading"><i class="fa fa-spinner fa-spin"></i> Scanning for networks...</div>';

    try {
        const response = await api.get('/wifi/scan');
        const networks = response.networks || [];

        if (networks.length === 0) {
            listContainer.innerHTML = '<div class="wifi-empty">No networks found</div>';
        } else {
            // Filter out empty ssids or the literal 'null' string
            const validNetworks = networks.filter(net => net.ssid && net.ssid.trim() !== '' && net.ssid !== 'null');

            if (validNetworks.length === 0) {
                listContainer.innerHTML = '<div class="wifi-empty">No valid networks found</div>';
            } else {
                listContainer.innerHTML = validNetworks.map((net, index) => {
                    const hasPassword = !!(net.security && net.security !== '' && net.security !== '--');
                    return `
                    <div class="wifi-network-item" data-index="${index}">
                        <div class="wifi-network-info">
                            <span class="wifi-network-name">${escapeHtml(net.ssid)}</span>
                            <span class="wifi-network-signal">
                                <i class="fa fa-signal"></i> ${net.signal}%
                                ${hasPassword ? '<i class="fa fa-lock"></i>' : ''}
                                ${net.saved ? '<i class="fa fa-bookmark" style="font-size: 0.8em; margin-left: 5px; color: #4db8ff;" title="Saved"></i>' : ''}
                            </span>
                        </div>
                    </div>
                `}).join('');

                // Attach click listeners safely without inline event handlers
                const items = listContainer.querySelectorAll('.wifi-network-item');
                items.forEach(item => {
                    item.addEventListener('click', function () {
                        const idx = parseInt(this.getAttribute('data-index'));
                        const net = validNetworks[idx];
                        if (net && net.ssid) {
                            const hasPwd = !!(net.security && net.security !== '' && net.security !== '--');
                            promptWifiConnect(net.ssid, hasPwd, !!net.saved);
                        }
                    });
                });
            }
        }
    } catch (error) {
        console.error('WiFi scan failed:', error);
        listContainer.innerHTML = '<div class="wifi-error">Scan failed. Try again.</div>';
        showToast('WiFi scan failed', 'error');
    } finally {
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Scan';
        }
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Prompt for WiFi connection (show password modal if secured and not saved)
 */
function promptWifiConnect(ssid, hasPassword, isSaved = false) {
    if (!ssid || ssid === 'null' || ssid === 'undefined') {
        showToast('Invalid network selected', 'error');
        return;
    }

    wifiConnectingSsid = ssid;

    if (hasPassword && !isSaved) {
        // Show password modal
        const modal = document.getElementById('wifi-password-modal');
        const ssidDisplay = document.getElementById('wifi-connect-ssid');
        const passwordInput = document.getElementById('wifi-password-input');

        if (ssidDisplay) ssidDisplay.textContent = ssid;
        if (passwordInput) passwordInput.value = '';
        if (modal) modal.style.display = 'flex';

        // Focus password input
        setTimeout(() => passwordInput?.focus(), 100);
    } else {
        // Connect directly without password or use saved nmcli credentials
        connectToWifi(ssid, '');
    }
}

/**
 * Submit WiFi password and connect
 */
async function submitWifiPassword() {
    const passwordInput = document.getElementById('wifi-password-input');
    const password = passwordInput?.value || '';

    if (!wifiConnectingSsid || wifiConnectingSsid === 'null') {
        showToast('No network selected', 'error');
        return;
    }

    closeWifiModal();
    await connectToWifi(wifiConnectingSsid, password);
}

/**
 * Close WiFi password modal
 */
function closeWifiModal() {
    const modal = document.getElementById('wifi-password-modal');
    if (modal) modal.style.display = 'none';
    wifiConnectingSsid = null;
}

/**
 * Connect to a WiFi network
 */
async function connectToWifi(ssid, password) {
    showToast(`Connecting to ${ssid}...`, 'info');

    try {
        const response = await api.post('/wifi/connect', { ssid, password });

        if (response.connected) {
            showToast(`Connected to ${ssid}!`, 'success');
            await loadWifiStatus();
        } else {
            showToast(response.error || 'Connection failed', 'error');
        }
    } catch (error) {
        console.error('WiFi connect failed:', error);
        showToast('Connection failed', 'error');
    }
}

/**
 * Disconnect from current WiFi network
 */
async function disconnectWifi() {
    showToast('Disconnecting...', 'info');

    try {
        const response = await api.post('/wifi/disconnect');

        if (!response.error) {
            showToast('Disconnected', 'success');
            await loadWifiStatus();
        } else {
            showToast(response.error || 'Disconnect failed', 'error');
        }
    } catch (error) {
        console.error('WiFi disconnect failed:', error);
        showToast('Disconnect failed', 'error');
    }
}

/**
 * Toggle saved networks visibility
 */
function toggleSavedNetworks() {
    const container = document.getElementById('wifi-saved-list');
    const toggleIcon = document.getElementById('saved-networks-toggle');

    if (container.style.display === 'none' || !container.style.display) {
        container.style.display = 'block';
        if (toggleIcon) toggleIcon.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
        loadSavedNetworks();
    } else {
        container.style.display = 'none';
        if (toggleIcon) toggleIcon.innerHTML = '<i class="fa-solid fa-chevron-down"></i>';
    }
}

/**
 * Load saved WiFi networks
 */
async function loadSavedNetworks() {
    const container = document.getElementById('wifi-saved-list');
    container.innerHTML = '<div class="wifi-loading"><i class="fa fa-spinner fa-spin"></i> Loading...</div>';

    try {
        const response = await api.get('/wifi/saved');
        const networks = response.networks || [];

        if (networks.length === 0) {
            container.innerHTML = '<div class="wifi-empty">No saved networks</div>';
        } else {
            container.innerHTML = networks.map(net => `
                <div class="wifi-saved-item">
                    <span class="wifi-saved-name">${escapeHtml(net.name)}</span>
                    <button class="btn-forget" onclick="forgetWifi('${escapeHtml(net.name)}')" title="Forget">
                        <i class="fa fa-trash"></i>
                    </button>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to load saved networks:', error);
        container.innerHTML = '<div class="wifi-error">Failed to load</div>';
    }
}

/**
 * Forget a saved WiFi network
 */
async function forgetWifi(name) {
    if (!confirm('Forget this network?')) return;

    try {
        const response = await api.post('/wifi/forget', { name });

        if (!response.error) {
            showToast('Network forgotten', 'success');
            await loadSavedNetworks();
        } else {
            showToast(response.error || 'Failed to forget', 'error');
        }
    } catch (error) {
        console.error('Failed to forget network:', error);
        showToast('Failed to forget network', 'error');
    }
}

// ============================================================================
// BLUETOOTH AUDIO MANAGEMENT
// ============================================================================

/**
 * Load and display current Bluetooth connection status
 */
async function loadBluetoothStatus() {
    const statusText = document.getElementById('bluetooth-status-text');
    const disconnectBtn = document.getElementById('btn-bluetooth-disconnect');
    const deviceRow = document.getElementById('bluetooth-device-row');
    const deviceName = document.getElementById('bluetooth-device-name');

    try {
        const response = await api.get('/bluetooth/status');

        if (!response.enabled) {
            statusText.innerHTML = '<span class="bluetooth-disabled"><i class="fa-brands fa-bluetooth"></i> Disabled in config</span>';
            if (disconnectBtn) disconnectBtn.style.display = 'none';
            if (deviceRow) deviceRow.style.display = 'none';
            return;
        }

        if (response.connected && response.device) {
            statusText.innerHTML = `
                <span class="bluetooth-connected">
                    <i class="fa-brands fa-bluetooth"></i> Connected
                </span>`;
            if (deviceName) deviceName.textContent = escapeHtml(response.device);
            if (deviceRow) deviceRow.style.display = 'flex';
            if (disconnectBtn) {
                disconnectBtn.style.display = 'inline-block';
                disconnectBtn.onclick = () => disconnectBluetooth(response.mac);
            }
        } else {
            statusText.innerHTML = '<span class="bluetooth-disconnected"><i class="fa-brands fa-bluetooth"></i> Ready</span>';
            if (deviceRow) deviceRow.style.display = 'none';
            if (disconnectBtn) disconnectBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to load Bluetooth status:', error);
        statusText.innerHTML = '<span class="bluetooth-error"><i class="fa fa-exclamation-triangle"></i> Error</span>';
        if (deviceRow) deviceRow.style.display = 'none';
        if (disconnectBtn) disconnectBtn.style.display = 'none';
    }
}

/**
 * Scan for available Bluetooth devices
 */
async function scanBluetoothDevices() {
    const listContainer = document.getElementById('bluetooth-devices-list');
    const scanBtn = document.getElementById('btn-scan-bluetooth');

    // Show the list container
    if (listContainer) listContainer.style.display = 'block';

    // Show loading state
    if (scanBtn) {
        scanBtn.disabled = true;
        scanBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Scanning...';
    }
    listContainer.innerHTML = '<div class="bluetooth-loading"><i class="fa fa-spinner fa-spin"></i> Scanning for audio devices... (takes ~5s)</div>';

    try {
        const response = await api.get('/bluetooth/scan');
        const devices = response.devices || [];

        if (devices.length === 0) {
            listContainer.innerHTML = '<div class="bluetooth-empty">No devices found</div>';
        } else {
            // Filter out unnamed devices to keep the UI clean, though MAC-only is okay if needed
            const validDevices = devices.filter(dev => dev.name && dev.name.trim() !== '');

            if (validDevices.length === 0) {
                listContainer.innerHTML = '<div class="bluetooth-empty">No named devices found</div>';
            } else {
                listContainer.innerHTML = validDevices.map(dev => `
                    <div class="bluetooth-device-item" onclick="connectToBluetooth('${dev.mac}', '${escapeHtml(dev.name)}')">
                        <div class="bluetooth-device-info">
                            <span class="bluetooth-device-name">${escapeHtml(dev.name)}</span>
                            <span class="bluetooth-device-mac">${dev.mac}</span>
                        </div>
                        ${dev.known ? '<span class="bluetooth-device-known"><i class="fa fa-check-circle"></i></span>' : ''}
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Bluetooth scan failed:', error);
        listContainer.innerHTML = '<div class="bluetooth-error">Scan failed. Is Bluetooth enabled?</div>';
        showToast('Bluetooth scan failed', 'error');
    } finally {
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Scan';
        }
    }
}

/**
 * Connect to a Bluetooth device
 */
async function connectToBluetooth(mac, name) {
    showToast(`Pairing & Connecting to ${name}...`, 'info');

    // Optional: add loading state to the clicked item
    document.body.style.cursor = 'wait';

    try {
        const response = await api.post('/bluetooth/connect', { mac: mac });

        if (response.success) {
            showToast(`Connected to ${name}! Audio routed.`, 'success');
            // Hide the list after successful connection
            const listContainer = document.getElementById('bluetooth-devices-list');
            if (listContainer) listContainer.style.display = 'none';

            await loadBluetoothStatus();
        } else {
            showToast(response.message || 'Connection failed', 'error');
        }
    } catch (error) {
        console.error('Bluetooth connect failed:', error);
        showToast('Connection failed. Make sure device is in pairing mode.', 'error');
    } finally {
        document.body.style.cursor = 'default';
    }
}

/**
 * Disconnect from current Bluetooth device
 */
async function disconnectBluetooth(mac) {
    showToast('Disconnecting Bluetooth...', 'info');

    try {
        const response = await api.post('/bluetooth/disconnect', { mac: mac });

        if (response.success) {
            showToast('Bluetooth disconnected', 'success');
            await loadBluetoothStatus();
        } else {
            showToast(response.message || 'Disconnect failed', 'error');
        }
    } catch (error) {
        console.error('Bluetooth disconnect failed:', error);
        showToast('Disconnect failed', 'error');
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

    // Listen for pairing events
    state.socket.on('device_paired', (data) => {
        console.log('Device paired:', data);
        showToast(`${data.device_name || 'Device'} paired!`, 'success');

        // Close the wizard modal if it's open
        closePairingWizard();

        if (state.currentPage === 'settings') loadPairingStatus();
    });

    state.socket.on('device_unpaired', () => {
        console.log('Device unpaired');
        if (state.currentPage === 'settings') loadPairingStatus();
    });

    // Listen for hotspot state changes (sync RPi ↔ mobile)
    state.socket.on('hotspot_started', (data) => {
        console.log('Hotspot started:', data);
        updateHotspotUI(true, data.ssid);
        showToast('Hotspot started', 'success');
    });

    state.socket.on('hotspot_stopped', () => {
        console.log('Hotspot stopped');
        updateHotspotUI(false);
        showToast('Hotspot stopped', 'info');
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
}

// ============================================================================
// SYSTEM STATUS
// ============================================================================

function updateStatus(component, isOnline) {
    state.status[component] = isOnline;

    const statusElement = document.getElementById(`status-${component}`);
    if (!statusElement) return;

    const dot = statusElement.querySelector('.status-dot');

    if (dot) {
        if (isOnline) {
            dot.className = 'status-dot dot online';
        } else {
            dot.className = 'status-dot dot offline';
        }
    }

    if (isOnline) {
        statusElement.classList.add('connected');
    } else {
        statusElement.classList.remove('connected');
    }
}

async function checkWiFiStatus() {
    // Check actual WiFi connection status via API
    try {
        const response = await api.get('/wifi/status');
        const isConnected = response.connected === true;
        const signal = response.signal || 0;

        updateStatus('wifi', isConnected);

        // Update home page signal bars and fallback icon
        const homeSignal = document.getElementById('home-wifi-signal');
        const homeFallback = document.getElementById('home-wifi-fallback');

        if (isConnected) {
            // Show signal bars, hide fallback icon
            if (homeSignal) {
                homeSignal.innerHTML = renderSignalBars(signal);
                homeSignal.style.display = '';
            }
            if (homeFallback) homeFallback.style.display = 'none';
        } else {
            // Hide signal bars, show fallback icon (dimmed)
            if (homeSignal) homeSignal.style.display = 'none';
            if (homeFallback) homeFallback.style.display = '';
        }

        return isConnected;
    } catch (error) {
        // If API fails, show fallback icon
        updateStatus('wifi', false);
        const homeSignal = document.getElementById('home-wifi-signal');
        const homeFallback = document.getElementById('home-wifi-fallback');
        if (homeSignal) homeSignal.style.display = 'none';
        if (homeFallback) homeFallback.style.display = '';
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
    document.getElementById('btn-reset-settings').addEventListener('click', resetToDefaults);

    // Brightness slider - real-time screen dimming
    const brightnessSlider = document.getElementById('setting-brightness');
    let brightnessTimeout = null;
    brightnessSlider.addEventListener('input', (e) => {
        const value = parseInt(e.target.value);
        document.getElementById('brightness-display').textContent = value + '%';

        // Apply screen brightness immediately via CSS overlay
        setScreenBrightness(value);

        // Debounce saving to config (don't need to save on every tiny change)
        if (brightnessTimeout) clearTimeout(brightnessTimeout);
        brightnessTimeout = setTimeout(async () => {
            try {
                await api.post('/display/brightness', { brightness: value });
            } catch (error) {
                console.error('Failed to save brightness:', error);
            }
        }, 500);
    });

    // Confidence slider update
    document.getElementById('setting-confidence').addEventListener('input', (e) => {
        const value = e.target.value;
        document.getElementById('confidence-display').textContent = value + '%';
    });

    // Connect WebSocket
    connectWebSocket();

    // Initial status check and load brightness
    checkSystemStatus();
    loadInitialBrightness();

    // Initialize touch scrolling for all scrollable containers
    initAllTouchScrolling();

    // Periodic status checks
    setInterval(checkSystemStatus, 5000);  // Check every 5 seconds

    // Start on home page
    switchPage('home');

    console.log('\u2713 Application ready!');
});

// QR code display logic for Hotspot modal (server-generated images)
function showHotspotQR() {
    const modal = document.getElementById('hotspot-qr-modal');
    if (!modal) return;
    modal.style.display = 'flex';

    // Clear previous QR codes
    document.getElementById('hotspot-wifi-qr').innerHTML = '';
    document.getElementById('hotspot-webapp-qr').innerHTML = '';
    document.getElementById('hotspot-ssid-info').textContent = '';
    document.getElementById('hotspot-password-info').textContent = '';

    // Fetch hotspot credentials for SSID/password display
    api.get('/hotspot/credentials').then(data => {
        document.getElementById('hotspot-ssid-info').textContent = `SSID: ${data.ssid}`;
        document.getElementById('hotspot-password-info').textContent = `Password: ${data.password}`;
    });

    // Set QR code images (served by backend, uses CSS sizing)
    renderQRCodeImage('hotspot-wifi-qr', '/api/hotspot/qr?type=wifi');
    renderQRCodeImage('hotspot-webapp-qr', '/api/hotspot/qr?type=webapp');

    // Default to WiFi tab
    switchHotspotQR('wifi');
}

/**
 * Switch between WiFi and Web App QR code tabs
 */
function switchHotspotQR(type) {
    const wifiQr = document.getElementById('hotspot-wifi-qr');
    const webappQr = document.getElementById('hotspot-webapp-qr');
    const tabs = document.querySelectorAll('.hotspot-qr-tab');

    if (type === 'wifi') {
        if (wifiQr) wifiQr.style.display = 'flex';
        if (webappQr) webappQr.style.display = 'none';
    } else {
        if (wifiQr) wifiQr.style.display = 'none';
        if (webappQr) webappQr.style.display = 'flex';
    }

    // Update tab active states
    tabs.forEach((tab, i) => {
        if ((type === 'wifi' && i === 0) || (type === 'webapp' && i === 1)) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
}

function closeHotspotQR() {
    const modal = document.getElementById('hotspot-qr-modal');
    if (modal) modal.style.display = 'none';
}

// Render QR code as <img> from backend (sizing handled by CSS .qr-image class)
function renderQRCodeImage(elementId, imgUrl) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = `<img src="${imgUrl}" alt="QR Code">`;
}

document.addEventListener('DOMContentLoaded', () => {
    // Modal close handler for QR modal
    const qrModal = document.getElementById('hotspot-qr-modal');
    if (qrModal) {
        const closeBtn = qrModal.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeHotspotQR);
        }
        qrModal.addEventListener('click', (e) => {
            if (e.target === qrModal) closeHotspotQR();
        });
    }
});
