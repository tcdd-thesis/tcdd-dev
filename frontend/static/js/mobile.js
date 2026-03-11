/**
 * TCDD — Mobile (Paired Device) Application
 * Separate JS for the phone/tablet view.
 * No shutdown/reboot/close-app, no brightness, no hotspot, no pairing controls.
 * Adds: phone audio output via Web Speech Synthesis API.
 */

// ============================================================================
// UTILITY: Button loading state
// ============================================================================

function setBtnLoading(btnOrId, loading, loadingLabel) {
    const btn = typeof btnOrId === 'string' ? document.getElementById(btnOrId) : btnOrId;
    if (!btn) return;
    if (loading) {
        btn._origHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ' + (loadingLabel || '');
    } else {
        btn.disabled = false;
        if (btn._origHTML !== undefined) btn.innerHTML = btn._origHTML;
    }
}

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
    originalSettings: {
        confidence: 50,
        ttsRate: 160,
        ttsCooldown: 10,
        ttsVolume: 100
    },
    status: {
        connection: false
    },
    // WebSocket reconnection state tracking
    _wsWasConnected: false,
    _wsReconnectToastShown: false,
    _wsConnectionState: 'disconnected',  // 'connected' | 'reconnecting' | 'disconnected'
    // Settings undo state
    _previousConfig: null,
    _undoTimer: null,
    // Camera health state
    _cameraStale: false,
    _lastServerFrameTime: 0
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

    // Visual alert for detections
    if (data.detections && data.detections.length) {
        showDetectionAlert(data.detections);
    }
}

// ============================================================================
// VISUAL DETECTION ALERTS
// ============================================================================

const ALERT_TIERS = {
    stop: 1, traffic_light_red: 1, traffic_light_red_no_left_turn: 1,
    traffic_light_red_no_right_turn: 1, traffic_light_red_right_turn: 1,
    traffic_light_red_left_turn: 1, Stop: 1, 'Red Light': 1,
    traffic_light_yellow: 2, yield: 2, pedestrian_crossing: 2,
    pwd_crossing: 2, yield_to_pedestrian: 2,
    speed_limit_50kph: 3, speed_limit_60kph: 3, speed_limit_80kph: 3,
    no_uturn: 3, no_left_turn: 3, no_right_turn: 3, no_turn_on_red: 3,
    no_left_turn_on_red: 3, no_right_turn_on_red: 3, no_parking: 3,
    do_not_block_intersection: 3, curve_right: 3, curve_left: 3
};

const _alertCooldowns = {};
const ALERT_COOLDOWN_MS = 5000;

function showDetectionAlert(detections) {
    const now = Date.now();
    let bestTier = 99, bestLabel = '';
    for (const det of detections) {
        const label = det.class_name;
        const tier = ALERT_TIERS[label];
        if (!tier || tier > 3) continue;
        if (_alertCooldowns[label] && now - _alertCooldowns[label] < ALERT_COOLDOWN_MS) continue;
        if (tier < bestTier) { bestTier = tier; bestLabel = label; }
    }
    if (!bestLabel) return;

    _alertCooldowns[bestLabel] = now;

    const container = document.querySelector('.video-container');
    if (!container) return;

    const old = container.querySelector('.detection-alert');
    if (old) old.remove();

    const tierClass = bestTier === 1 ? 'alert-critical' : bestTier === 2 ? 'alert-warning' : 'alert-info';
    const alertEl = document.createElement('div');
    alertEl.className = `detection-alert ${tierClass}`;
    alertEl.textContent = bestLabel.replace(/_/g, ' ');
    container.appendChild(alertEl);

    setTimeout(() => alertEl.remove(), 3000);
}

function setCameraWarning(show, message) {
    const noFeed = document.getElementById('no-feed');
    if (!noFeed) return;
    if (show) {
        noFeed.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>' +
            '<span>' + (message || 'Camera not responding') + '</span>';
        noFeed.classList.add('camera-warning');
        noFeed.style.display = 'flex';
    } else {
        noFeed.classList.remove('camera-warning');
        noFeed.style.display = 'none';
        noFeed.innerHTML = '<i class="fa-solid fa-video-slash"></i><span>Waiting for feed...</span>';
    }
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
        const confSlider = document.getElementById('setting-confidence');
        const confDisplay = document.getElementById('confidence-display');
        if (confSlider && confDisplay) {
            confSlider.value = Math.round(confidence * 100);
            confDisplay.textContent = Math.round(confidence * 100) + '%';
        }
        state.originalSettings.confidence = Math.round(confidence * 100);

        // TTS Enabled status
        const ttsStatus = document.getElementById('tts-status');
        if (ttsStatus) ttsStatus.textContent = cfg.tts?.enabled !== false ? 'Enabled' : 'Disabled';

        // TTS Speech Rate slider
        const speechRate = cfg.tts?.speech_rate || 160;
        const rateSlider = document.getElementById('setting-tts-rate');
        const rateDisplay = document.getElementById('tts-rate-display');
        if (rateSlider && rateDisplay) {
            rateSlider.value = speechRate;
            rateDisplay.textContent = speechRate + ' wpm';
        }
        state.originalSettings.ttsRate = speechRate;

        // TTS Cooldown slider
        const cooldown = cfg.tts?.cooldown_seconds || 10;
        const cdSlider = document.getElementById('setting-tts-cooldown');
        const cdDisplay = document.getElementById('tts-cooldown-display');
        if (cdSlider && cdDisplay) {
            cdSlider.value = cooldown;
            cdDisplay.textContent = cooldown + 's';
        }
        state.originalSettings.ttsCooldown = cooldown;

        // TTS Volume slider
        const volume = cfg.tts?.volume ?? 1.0;
        const volSlider = document.getElementById('setting-tts-volume');
        const volDisplay = document.getElementById('tts-volume-display');
        if (volSlider && volDisplay) {
            volSlider.value = Math.round(volume * 100);
            volDisplay.textContent = Math.round(volume * 100) + '%';
        }
        state.originalSettings.ttsVolume = Math.round(volume * 100);

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
    const btn = document.getElementById('btn-save-settings');
    setBtnLoading(btn, true, 'Saving...');
    try {
        const confidence = parseFloat(document.getElementById('setting-confidence').value) / 100;
        const speechRate = parseInt(document.getElementById('setting-tts-rate').value);
        const cooldown = parseInt(document.getElementById('setting-tts-cooldown').value);
        const volume = parseFloat(document.getElementById('setting-tts-volume').value) / 100;

        const config = {
            detection: { confidence: confidence },
            tts: {
                speech_rate: speechRate,
                cooldown_seconds: cooldown,
                volume: parseFloat(volume.toFixed(2))
            }
        };

        // Store previous config for undo
        const prevConfig = {
            detection: { confidence: state.originalSettings.confidence / 100 },
            tts: {
                speech_rate: state.originalSettings.ttsRate,
                cooldown_seconds: state.originalSettings.ttsCooldown,
                volume: state.originalSettings.ttsVolume / 100
            }
        };

        const response = await api.put('/config', config);
        state.config = response.config;

        // Update original settings after successful save
        state.originalSettings.confidence = Math.round(confidence * 100);
        state.originalSettings.ttsRate = speechRate;
        state.originalSettings.ttsCooldown = cooldown;
        state.originalSettings.ttsVolume = Math.round(volume * 100);

        showUndoToast(prevConfig);
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast('Save failed', 'error');
    } finally {
        setBtnLoading(btn, false);
    }
}

function showUndoToast(prevConfig) {
    if (state._undoTimer) clearTimeout(state._undoTimer);
    state._previousConfig = prevConfig;

    const container = document.getElementById('toast-container');
    container.querySelectorAll('.toast-undo').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = 'toast success toast-undo';
    toast.innerHTML = 'Settings saved! <button class="toast-undo-btn" onclick="undoSettings()">Undo</button>';
    container.appendChild(toast);

    state._undoTimer = setTimeout(() => {
        toast.remove();
        state._previousConfig = null;
        state._undoTimer = null;
    }, 10000);
}

async function undoSettings() {
    if (!state._previousConfig) return;
    if (state._undoTimer) clearTimeout(state._undoTimer);

    const prev = state._previousConfig;
    state._previousConfig = null;

    document.querySelectorAll('.toast-undo').forEach(t => t.remove());

    try {
        await api.put('/config', prev);
        state.originalSettings.confidence = Math.round(prev.detection.confidence * 100);
        state.originalSettings.ttsRate = prev.tts.speech_rate;
        state.originalSettings.ttsCooldown = prev.tts.cooldown_seconds;
        state.originalSettings.ttsVolume = Math.round(prev.tts.volume * 100);

        if (state.currentPage === 'settings') loadSettings();
        showToast('Settings reverted', 'info');
    } catch (error) {
        console.error('Undo failed:', error);
        showToast('Undo failed', 'error');
    }
}

/**
 * Reset all settings sliders to their last-saved values.
 */
function resetSettings() {
    const o = state.originalSettings;

    const confSlider = document.getElementById('setting-confidence');
    const confDisplay = document.getElementById('confidence-display');
    if (confSlider) confSlider.value = o.confidence;
    if (confDisplay) confDisplay.textContent = o.confidence + '%';

    const rateSlider = document.getElementById('setting-tts-rate');
    const rateDisplay = document.getElementById('tts-rate-display');
    if (rateSlider) rateSlider.value = o.ttsRate;
    if (rateDisplay) rateDisplay.textContent = o.ttsRate + ' wpm';

    const cdSlider = document.getElementById('setting-tts-cooldown');
    const cdDisplay = document.getElementById('tts-cooldown-display');
    if (cdSlider) cdSlider.value = o.ttsCooldown;
    if (cdDisplay) cdDisplay.textContent = o.ttsCooldown + 's';

    const volSlider = document.getElementById('setting-tts-volume');
    const volDisplay = document.getElementById('tts-volume-display');
    if (volSlider) volSlider.value = o.ttsVolume;
    if (volDisplay) volDisplay.textContent = o.ttsVolume + '%';

    showToast('Settings reset', 'info');
}

function hasMobileSettingsChanged() {
    const o = state.originalSettings;
    const conf = document.getElementById('setting-confidence');
    const rate = document.getElementById('setting-tts-rate');
    const cd = document.getElementById('setting-tts-cooldown');
    const vol = document.getElementById('setting-tts-volume');
    return (conf && parseInt(conf.value) !== o.confidence) ||
        (rate && parseInt(rate.value) !== o.ttsRate) ||
        (cd && parseInt(cd.value) !== o.ttsCooldown) ||
        (vol && parseInt(vol.value) !== o.ttsVolume);
}

/**
 * Unpair this mobile device from the TCDD system.
 */
async function mobileUnpair() {
    if (!confirm('Unpair this device? You will need to pair again to reconnect.')) return;
    const btn = document.getElementById('btn-mobile-unpair');
    setBtnLoading(btn, true, 'Unpairing...');
    try {
        await api.post('/pair/unpair');
        localStorage.removeItem('tcdd_session_token');
        showToast('Device unpaired. Redirecting...', 'success');
        setTimeout(() => { window.location.href = '/pair'; }, 1500);
    } catch (error) {
        console.error('Failed to unpair:', error);
        showToast('Unpair failed', 'error');
        setBtnLoading(btn, false);
    }
}

// ============================================================================
// VIOLATIONS / LOGS
// ============================================================================

async function loadViolations() {
    const btn = document.getElementById('btn-refresh-logs');
    setBtnLoading(btn, true, 'Loading...');
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
    } finally {
        setBtnLoading(btn, false);
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
    state.socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 10000,
        randomizationFactor: 0.5
    });

    state.socket.on('connect', () => {
        console.log('WebSocket connected');
        updateConnectionStatus('connected');

        // Only show "Reconnected" toast if this was a reconnect, not initial connect
        if (state._wsWasConnected) {
            showToast('Reconnected to server', 'success');
        } else {
            showToast('Connected to server', 'success');
        }
        state._wsWasConnected = true;
        state._wsReconnectToastShown = false;

        // Authenticate with session token (also re-authenticates on reconnect)
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

    state.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);

        // If server intentionally disconnected us (force_disconnect follows), show red
        // Otherwise Socket.IO will auto-reconnect, show amber
        if (reason === 'io server disconnect') {
            updateConnectionStatus('disconnected');
        } else {
            updateConnectionStatus('reconnecting');
        }
    });

    state.socket.io.on('reconnect_attempt', (attempt) => {
        console.log(`WebSocket reconnect attempt ${attempt}`);
        updateConnectionStatus('reconnecting');

        // Show reconnecting toast once (not on every attempt)
        if (!state._wsReconnectToastShown) {
            showToast('Connection lost. Reconnecting...', 'warning');
            state._wsReconnectToastShown = true;
        }
    });

    state.socket.io.on('reconnect_failed', () => {
        console.error('WebSocket reconnect failed after all attempts');
        updateConnectionStatus('disconnected');
        showToast('Unable to reconnect. Please reload the page.', 'error');
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
        // Track last frame arrival for client-side stale detection
        state._lastServerFrameTime = Date.now();
        if (state._cameraStale) {
            state._cameraStale = false;
            setCameraWarning(false);
        }
    });

    state.socket.on('system_warning', (data) => {
        if (data.type === 'camera_stale') {
            state._cameraStale = true;
            setCameraWarning(true, data.message);
        } else if (data.type === 'camera_recovered') {
            state._cameraStale = false;
            setCameraWarning(false);
        } else if (data.type === 'tts_error') {
            showToast('Voice alerts disabled: ' + data.message, 'error');
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
        // Protect unsaved changes on settings page
        if (state.currentPage === 'settings' && hasMobileSettingsChanged()) {
            showToast('Config changed externally. Save or discard your changes.', 'info');
            return;
        }
        state.config = data.config;
        if (state.currentPage === 'settings') {
            loadSettings();
        }
    });
}

/**
 * Update the connection status indicator to one of three states:
 * 'connected' (green), 'reconnecting' (amber), 'disconnected' (red)
 */
function updateConnectionStatus(status) {
    state._wsConnectionState = status;
    state.status.connection = (status === 'connected');
    const el = document.getElementById('status-connection');
    if (!el) return;
    const dot = el.querySelector('.status-dot');
    if (dot) {
        dot.className = 'status-dot ' + status;
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

    // Settings save & reset
    const saveBtn = document.getElementById('btn-save-settings');
    if (saveBtn) saveBtn.addEventListener('click', saveSettings);

    const resetBtn = document.getElementById('btn-reset-settings');
    if (resetBtn) resetBtn.addEventListener('click', resetSettings);

    // Confidence slider live update
    const confidenceSlider = document.getElementById('setting-confidence');
    if (confidenceSlider) {
        confidenceSlider.addEventListener('input', (e) => {
            const display = document.getElementById('confidence-display');
            if (display) display.textContent = e.target.value + '%';
        });
    }

    // TTS Speech Rate slider live update
    const rateSlider = document.getElementById('setting-tts-rate');
    if (rateSlider) {
        rateSlider.addEventListener('input', (e) => {
            const display = document.getElementById('tts-rate-display');
            if (display) display.textContent = e.target.value + ' wpm';
        });
    }

    // TTS Cooldown slider live update
    const cdSlider = document.getElementById('setting-tts-cooldown');
    if (cdSlider) {
        cdSlider.addEventListener('input', (e) => {
            const display = document.getElementById('tts-cooldown-display');
            if (display) display.textContent = e.target.value + 's';
        });
    }

    // TTS Volume slider live update
    const volSlider = document.getElementById('setting-tts-volume');
    if (volSlider) {
        volSlider.addEventListener('input', (e) => {
            const display = document.getElementById('tts-volume-display');
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
