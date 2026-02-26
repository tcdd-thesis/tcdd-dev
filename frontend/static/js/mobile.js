/**
 * TCDD — Mobile (Paired Device) Application
 * Separate JS for the phone/tablet view.
 * No shutdown/reboot/close-app, no brightness, no hotspot, no pairing controls.
 * Adds: phone audio output via Web Speech Synthesis API.
 */

// ============================================================================
// STATE
// ============================================================================

const state = {
    socket: null,
    currentPage: 'home',
    fps: 0,
    detectionCount: 0,
    lastFrameTime: null,
    config: null,
    phoneAudioEnabled: false,
    originalConfidence: 50,
    status: {
        connection: false
    }
};

// ============================================================================
// API HELPER  (same pattern as app.js)
// ============================================================================

const api = {
    baseUrl: '/api',

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

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ============================================================================
// NAVIGATION
// ============================================================================

function goHome() {
    switchPage('home');
}

function switchPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById(`page-${pageName}`);
    if (page) page.classList.add('active');
    state.currentPage = pageName;

    if (pageName === 'logs') loadViolations();
    if (pageName === 'settings') loadSettings();
}

// ============================================================================
// LIVE FEED
// ============================================================================

function handleVideoFrame(data) {
    const canvas = document.getElementById('video-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const img = new Image();
    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);

        state.detectionCount = data.count || 0;
        const countEl = document.getElementById('detection-count');
        if (countEl) countEl.textContent = state.detectionCount;

        // Hide no-feed overlay
        const noFeed = document.getElementById('no-feed');
        if (noFeed) noFeed.style.display = 'none';
    };
    img.src = 'data:image/jpeg;base64,' + data.frame;

    // FPS calculation
    const now = Date.now();
    if (state.lastFrameTime) {
        const delta = now - state.lastFrameTime;
        state.fps = Math.round(1000 / delta);
        const fpsEl = document.getElementById('fps-value');
        if (fpsEl) fpsEl.textContent = state.fps;
    }
    state.lastFrameTime = now;
}

// ============================================================================
// SETTINGS
// ============================================================================

async function loadSettings() {
    try {
        const response = await api.get('/config');
        state.config = response.config || response;
        const cfg = state.config;

        // Confidence slider
        const confidence = cfg.detection?.confidence || 0.5;
        const slider = document.getElementById('setting-confidence');
        const display = document.getElementById('confidence-display');
        if (slider && display) {
            slider.value = Math.round(confidence * 100);
            display.textContent = Math.round(confidence * 100) + '%';
        }
        state.originalConfidence = Math.round(confidence * 100);

        // TTS info
        const ttsStatus = document.getElementById('tts-status');
        const ttsRate = document.getElementById('tts-rate');
        const ttsCooldown = document.getElementById('tts-cooldown');
        if (ttsStatus) ttsStatus.textContent = cfg.tts?.enabled !== false ? 'Enabled' : 'Disabled';
        if (ttsRate) ttsRate.textContent = (cfg.tts?.speech_rate || 160) + ' wpm';
        if (ttsCooldown) ttsCooldown.textContent = (cfg.tts?.cooldown_seconds || 10) + 's';

        // System info
        try {
            const status = await api.get('/status');
            const modelEl = document.getElementById('model-name');
            if (modelEl && status.model) {
                modelEl.textContent = status.model.split('/').pop();
            }
        } catch (e) { /* ignore */ }

    } catch (error) {
        console.error('Failed to load settings:', error);
        showToast('Failed to load settings', 'error');
    }
}

async function saveSettings() {
    try {
        const confidence = parseFloat(document.getElementById('setting-confidence').value) / 100;

        const config = {
            detection: { confidence: confidence }
        };

        showToast('Saving...', 'info');
        const response = await api.put('/config', config);
        state.config = response.config;
        state.originalConfidence = Math.round(confidence * 100);
        showToast('Settings saved!', 'success');
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('Save failed', 'error');
    }
}

// ============================================================================
// VIOLATIONS / LOGS
// ============================================================================

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
                    <small>Violations will appear here when detected</small>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
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
    card.className = `violation-card severity-${ev.severity || 'low'}`;
    card.style.cursor = 'pointer';

    const timestamp = new Date(ev.timestamp);
    const timeStr = timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const dateStr = timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    const violationType = (ev.violation_type || 'unknown').replace(/_/g, ' ');
    const confidence = Math.round((ev.confidence || 0) * 100);
    const location = ev.context?.road_name || ev.context?.camera_id || 'Unknown location';

    const violationIcon = getViolationIcon(ev.violation_type);
    const actionIcon = ev.driver_action === 'wrong' ? '<i class="fa-solid fa-xmark"></i>' :
        ev.driver_action === 'right' ? '<i class="fa-solid fa-check"></i>' :
            '<i class="fa-solid fa-question"></i>';
    const actionClass = ev.driver_action === 'wrong' ? 'action-wrong' :
        ev.driver_action === 'right' ? 'action-right' : 'action-unknown';

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
        </div>
    `;

    card.addEventListener('click', () => showViolationDetail(ev));
    return card;
}

function getViolationIcon(type) {
    const icons = {
        'overspeed': '<i class="fa-solid fa-gauge-high"></i>',
        'red_light': '<i class="fa-solid fa-circle" style="color:#e53935"></i>',
        'stop_sign': '<i class="fa-solid fa-hand"></i>',
        'wrong_way': '<i class="fa-solid fa-triangle-exclamation"></i>',
        'illegal_turn': '<i class="fa-solid fa-arrow-turn-up"></i>',
        'lane_departure': '<i class="fa-solid fa-arrows-left-right"></i>',
        'tailgating': '<i class="fa-solid fa-car-rear"></i>',
        'none': '<i class="fa-solid fa-check"></i>'
    };
    return icons[type] || '<i class="fa-solid fa-question"></i>';
}

function showViolationDetail(ev) {
    const modal = document.getElementById('violation-detail-modal');
    const content = document.getElementById('violation-detail-content');
    if (!modal || !content) return;

    const timestamp = new Date(ev.timestamp);
    const fullTimeStr = timestamp.toLocaleString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    });

    let html = `
        <div class="detail-section">
            <h4>Basic Information</h4>
            <div class="detail-grid">
                <div class="detail-item"><span class="detail-label">ID:</span><span class="detail-value">${ev.id || 'N/A'}</span></div>
                <div class="detail-item"><span class="detail-label">Timestamp:</span><span class="detail-value">${fullTimeStr}</span></div>
                <div class="detail-item"><span class="detail-label">Type:</span><span class="detail-value">${(ev.violation_type || 'unknown').replace(/_/g, ' ')}</span></div>
                <div class="detail-item"><span class="detail-label">Severity:</span><span class="detail-value">${ev.severity || 'low'}</span></div>
                <div class="detail-item"><span class="detail-label">Confidence:</span><span class="detail-value">${Math.round((ev.confidence || 0) * 100)}%</span></div>
                <div class="detail-item"><span class="detail-label">Action:</span><span class="detail-value">${ev.driver_action || 'unknown'}</span></div>
            </div>
        </div>
    `;

    if (ev.evidence?.sign_detected) {
        html += `
            <div class="detail-section">
                <h4>Evidence</h4>
                <div class="detail-grid">
                    <div class="detail-item"><span class="detail-label">Sign:</span><span class="detail-value">${ev.evidence.sign_detected.label}</span></div>
                    <div class="detail-item"><span class="detail-label">Sign Conf:</span><span class="detail-value">${Math.round((ev.evidence.sign_detected.conf || 0) * 100)}%</span></div>
                </div>
            </div>
        `;
    }

    content.innerHTML = html;
    modal.style.display = 'flex';
}

function closeViolationDetail() {
    const modal = document.getElementById('violation-detail-modal');
    if (modal) modal.style.display = 'none';
}

function clearViolationsDisplay() {
    const container = document.getElementById('violations-list');
    if (container) {
        container.innerHTML = `
            <div class="log-empty">
                <span class="icon"><i class="fa-solid fa-shield-halved"></i></span>
                <div>Display cleared</div>
                <small>Tap Refresh to reload</small>
            </div>
        `;
    }
}

// ============================================================================
// PHONE AUDIO — Web Speech Synthesis API
// ============================================================================

/**
 * Speak text using the browser's offline TTS engine.
 * Prefers a local (offline-capable) English voice.
 */
function speakAlert(text) {
    if (!('speechSynthesis' in window)) {
        console.warn('Web Speech Synthesis not supported');
        return;
    }

    // Cancel any currently speaking utterance to avoid queue pile-up
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Prefer a local (offline) English voice
    const voices = speechSynthesis.getVoices();
    const localVoice = voices.find(v => v.localService && v.lang.startsWith('en'));
    if (localVoice) {
        utterance.voice = localVoice;
    }

    speechSynthesis.speak(utterance);
}

// Pre-load voices (some browsers load them async)
if ('speechSynthesis' in window) {
    speechSynthesis.getVoices();
    speechSynthesis.addEventListener('voiceschanged', () => {
        speechSynthesis.getVoices();
    });
}

/**
 * Open the audio modal and sync state from backend.
 */
function openAudioModal() {
    const modal = document.getElementById('audio-modal');
    if (modal) modal.style.display = 'flex';

    // Sync current state
    api.get('/phone-audio/status')
        .then(data => {
            state.phoneAudioEnabled = data.enabled;
            updateAudioUI();
        })
        .catch(() => { /* use local state */ });
}

function closeAudioModal() {
    const modal = document.getElementById('audio-modal');
    if (modal) modal.style.display = 'none';
}

/**
 * Toggle phone audio on/off.
 */
async function togglePhoneAudio() {
    try {
        const newState = !state.phoneAudioEnabled;

        // iOS Safari requires a user-gesture to unlock Web Speech API.
        // Speak a silent/short utterance on the first enable to "unlock" it.
        if (newState && 'speechSynthesis' in window) {
            const unlock = new SpeechSynthesisUtterance('');
            unlock.volume = 0;
            speechSynthesis.speak(unlock);
        }

        const res = await api.post('/phone-audio/toggle', { enabled: newState });
        state.phoneAudioEnabled = res.enabled;
        updateAudioUI();

        if (state.phoneAudioEnabled) {
            showToast('Phone audio enabled — alerts will play here', 'success');
        } else {
            showToast('Phone audio disabled', 'info');
        }
    } catch (error) {
        console.error('Failed to toggle phone audio:', error);
        showToast('Failed to toggle audio', 'error');
    }
}

/**
 * Send a test alert to this phone.
 */
async function testPhoneAudio() {
    try {
        const btn = document.getElementById('btn-test-speaker');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';
        }

        // Speak locally as well (in case the socket event takes a moment)
        speakAlert('This is a test alert. Phone audio is working.');

        await api.post('/phone-audio/test');

        showToast('Test alert sent!', 'success');
        showAudioStatus('Speaker test successful', 'success');

        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Test Speaker';
        }
    } catch (error) {
        console.error('Failed to test phone audio:', error);
        showToast('Test failed', 'error');
        showAudioStatus('Speaker test failed', 'error');

        const btn = document.getElementById('btn-test-speaker');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Test Speaker';
        }
    }
}

/**
 * Update all audio-related UI elements to reflect current state.
 */
function updateAudioUI() {
    const toggleBtn = document.getElementById('btn-audio-toggle');
    const toggleLabel = document.getElementById('audio-toggle-label');
    const badge = document.getElementById('audio-badge');
    const indicator = document.querySelector('.phone-audio-indicator');

    if (toggleBtn) {
        toggleBtn.classList.toggle('active', state.phoneAudioEnabled);
    }
    if (toggleLabel) {
        toggleLabel.textContent = state.phoneAudioEnabled ? 'Audio Output Enabled' : 'Audio Output Disabled';
    }
    if (badge) {
        badge.style.display = state.phoneAudioEnabled ? 'inline-block' : 'none';
    }
    if (indicator) {
        indicator.style.display = state.phoneAudioEnabled ? 'inline-block' : 'none';
    }
}

function showAudioStatus(msg, type) {
    const el = document.getElementById('audio-status');
    if (!el) return;
    el.textContent = msg;
    el.className = `audio-status ${type}`;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
}

// ============================================================================
// WEBSOCKET
// ============================================================================

function connectWebSocket() {
    state.socket = io();

    state.socket.on('connect', () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
        showToast('Connected to server', 'success');

        // Authenticate with session token
        const token = localStorage.getItem('tcdd_session_token');
        if (token) {
            state.socket.emit('authenticate', { session_token: token });
        }
    });

    state.socket.on('auth_success', () => {
        console.log('WebSocket authenticated');
    });

    state.socket.on('auth_failed', (data) => {
        console.error('WebSocket auth failed:', data);
        showToast('Session expired. Please re-pair.', 'error');
    });

    state.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        showToast('Disconnected from server', 'warning');
    });

    state.socket.on('force_disconnect', (data) => {
        showToast('Disconnected: ' + (data.reason || 'Unknown'), 'warning');
        // Redirect to pair page after a moment
        setTimeout(() => { window.location.href = '/pair'; }, 2000);
    });

    // Video frames
    state.socket.on('video_frame', (data) => {
        if (state.currentPage === 'live') {
            handleVideoFrame(data);
        }
    });

    // TTS alerts from backend → speak on phone
    state.socket.on('tts_alert', (data) => {
        if (state.phoneAudioEnabled && data.text) {
            speakAlert(data.text);
            console.log(`TTS alert: [${data.label}] "${data.text}"`);
        }
    });

    // Phone audio state sync (e.g. if another request toggles it)
    state.socket.on('phone_audio_state', (data) => {
        state.phoneAudioEnabled = data.enabled;
        updateAudioUI();
    });

    // Config updates from server
    state.socket.on('config_updated', (data) => {
        state.config = data.config;
        if (state.currentPage === 'settings') {
            loadSettings();
        }
    });
}

function updateConnectionStatus(online) {
    state.status.connection = online;
    const el = document.getElementById('status-connection');
    if (!el) return;
    const dot = el.querySelector('.status-dot');
    if (dot) {
        dot.className = online ? 'status-dot online' : 'status-dot offline';
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing TCDD Mobile...');

    // Menu button navigation
    document.querySelectorAll('.menu-btn[data-page]').forEach(btn => {
        btn.addEventListener('click', () => {
            switchPage(btn.getAttribute('data-page'));
        });
    });

    // Settings save
    const saveBtn = document.getElementById('btn-save-settings');
    if (saveBtn) saveBtn.addEventListener('click', saveSettings);

    // Confidence slider live update
    const confidenceSlider = document.getElementById('setting-confidence');
    if (confidenceSlider) {
        confidenceSlider.addEventListener('input', (e) => {
            const display = document.getElementById('confidence-display');
            if (display) display.textContent = e.target.value + '%';
        });
    }

    // Modal close on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    });

    // Load phone audio state
    api.get('/phone-audio/status')
        .then(data => {
            state.phoneAudioEnabled = data.enabled;
            updateAudioUI();
        })
        .catch(() => { /* default: disabled */ });

    // Connect WebSocket
    connectWebSocket();

    // Start on home page
    switchPage('home');

    console.log('✓ Mobile app ready!');
});
