# QoL (Quality of Life) Improvement Plan

**Version**: Draft v1.0  
**Date**: 2026-03-11  
**Status**: REVIEW - Awaiting developer approval before implementation

---

## 1. System Usability Assessment Summary

After a full codebase audit, the following categories of issues were identified:

| Category | Count | Severity |
|----------|-------|----------|
| UX friction / missing feedback | 8 | Medium-High |
| Silent failures / no recovery | 5 | High |
| Config validation gaps | 4 | High |
| Security hardening | 3 | Medium |
| Performance inefficiencies | 3 | Medium |
| Missing operational safeguards | 4 | Medium |

---

## 2. Proposed QoL Features (Prioritized)

### Phase 1 - Stability and Resilience (Foundation)
> These fix silent failures and ensure the system stays functional under adverse conditions.

**QoL-1: WebSocket Auto-Reconnect** ✅ DONE
- Problem: If WiFi drops or server restarts, the frontend (both touchscreen and mobile) goes dead. User must manually reload the page.
- Solution: Implemented exponential backoff reconnection in both `app.js` and `mobile.js` with 3-state visual status indicator (green/amber/red). Re-authenticates mobile sessions on reconnect.
- Files changed: `app.js`, `mobile.js`, `style.css`, `mobile.css`, `index.html`, `mobile.html`

**QoL-2: Config Value Validation** [DESCOPED]
- Original scope was full backend validation (min/max/type rules). The UI sliders already constrain ranges, and config values like model path are not user-facing.
- Reduced to: (a) Default brightness changed from 50 to 55. (b) Suppressed self-echo toast spam when brightness slider triggers config_updated broadcast.
- Status: IMPLEMENTED (reduced scope)

**QoL-3: Camera/Detector Health Monitoring** ✅ DONE
- Problem: If the camera disconnects or the detector crashes mid-operation, the system continues running but detection silently stops. User sees a frozen or black feed with no error indication.
- Solution: Added `_last_frame_time` (monotonic) in camera capture thread. Stream loop checks every 2s; if stale >3s emits `system_warning` with type `camera_stale`. Frontend shows pulsing amber warning overlay on the video feed. Recovery event (`camera_recovered`) auto-clears the overlay.
- Files changed: `main.py`, `app.js`, `mobile.js`, `style.css`, `mobile.css`, `index.html`, `mobile.html`

**QoL-4: Graceful Error Recovery for TTS** ✅ DONE
- Problem: If `espeak` crashes or is unavailable, the TTS worker thread dies silently. No more voice alerts for the rest of the session.
- Solution: Added retry tracking in `_worker_loop`. `_speak_subprocess` now returns success/failure. After 3 consecutive failures, TTS auto-disables and fires `_on_error_callback` → main.py emits `system_warning` (type `tts_error`) → frontends show error toast.
- Files changed: `tts.py`, `main.py`, `app.js`, `mobile.js`

---

### Phase 2 - User Experience Polish (Feedback and Responsiveness)

**QoL-5: Operation Progress Indicators** ✅ DONE
- Problem: Several operations (WiFi scan, Bluetooth scan, hotspot start, pairing) take 5-15 seconds with no progress feedback. Users don't know if the action is working or stuck.
- Solution: Add loading spinners/progress bars for all long-running operations. Disable the trigger button during the operation to prevent double-clicks. Show elapsed time for operations >5 seconds.
- Scope: `app.js`, `mobile.js`, `style.css`, `mobile.css`, `index.html`, `mobile.html`
- Risk: Low. Pure UI changes.
- Test: Trigger each operation; verify spinner appears and button is disabled until completion.

**QoL-6: Settings Save Confirmation and Undo** ✅ DONE
- Problem: When settings are saved, there's minimal feedback. If a bad config is saved, there's no easy way to revert. Additionally, incoming WebSocket config updates can conflict with unsaved changes on the Settings page.
- Solution: (a) Show a clear "Settings saved" toast with a 10-second "Undo" button that restores the previous config. (b) Lock the Settings page from incoming config pushes while the user has unsaved changes (show a "Config changed externally, reload?" prompt instead).
- Scope: `app.js`, `mobile.js`, `config.py` (backup retrieval endpoint), `main.py`
- Risk: Medium. Undo requires storing the previous config state. External change detection adds complexity.
- Test: Save settings, verify toast + undo; change config externally while Settings page open, verify prompt.

**QoL-7: Visual Alert Indicators for Detections** ✅ DONE
- Problem: TTS alerts are audio-only. In noisy environments (open windows, loud music), the driver may miss critical alerts. There is no visual complement on-screen.
- Solution: Add a brief screen-edge flash or banner for critical detections (stop signs, red lights, speed limits). Color-coded by priority: red = critical, amber = warning, blue = informational. Auto-dismiss after 3 seconds.
- Scope: `app.js`, `mobile.js`, `style.css`, `mobile.css`, `index.html`, `mobile.html`
- Risk: Low. Must not obstruct the video feed. Flash should be subtle (border glow, not full-screen).
- Test: Trigger mock detections at each priority level; verify correct color and timing.

**QoL-8: Improved System Control Button Safety** ✅ DONE
- Problem: Shutdown, reboot, and close-app buttons are on the home screen and are easy to accidentally press while driving. A single tap + confirm is not enough safeguard.
- Solution: Move destructive actions into a dedicated "System" sub-menu (requires an extra tap to reach). Add a 3-second hold-to-confirm for shutdown/reboot (instead of tap + modal). Keep close-app as a tap + confirm since it's less destructive.
- Scope: `index.html`, `app.js`, `style.css`
- Risk: Low. UI reorganization only.
- Test: Verify buttons are no longer on the home screen; verify hold-to-confirm works on touchscreen.

---

### Phase 3 - Operational Robustness (Resilience and Monitoring)

**QoL-9: Startup Self-Check**
- Problem: The system starts without verifying critical prerequisites (model file exists, camera accessible, disk space available, required packages installed). Failures surface as cryptic runtime errors.
- Solution: Add a startup self-check routine that validates: (a) model file exists and is readable, (b) camera can be opened, (c) disk space >100MB, (d) config.json is valid JSON with required keys. Report results via a startup status page or log summary. Emit `startup_status` WebSocket event.
- Scope: `main.py`, new utility function
- Risk: Low. Read-only checks at startup. Must not block startup for too long (<5 seconds total).
- Test: Remove model file; verify clear error message. Fill disk; verify warning.

**QoL-10: Log Rotation and Disk Space Management**
- Problem: Metrics CSV and violations JSONL files accumulate indefinitely. On an SD card with limited space, this can eventually fill the disk and crash the system.
- Solution: Add automatic log rotation: keep last 7 days of logs, compress older files, delete files older than 30 days. Add a disk space check that warns when <500MB free and stops logging when <100MB free.
- Scope: `metrics_logger.py`, `violations_logger.py`, new `log_maintenance.py` utility
- Risk: Low. File management only. Must be careful not to delete in-progress log files.
- Test: Create old log files; verify rotation and compression. Mock low disk; verify warning.

**QoL-11: Systemd Watchdog and Auto-Restart**
- Problem: If the Python application crashes, systemd does not know and does not restart it. The system sits dead until someone notices.
- Solution: Add `Restart=on-failure` and `RestartSec=5` to the systemd service. Optionally add `WatchdogSec=30` with a periodic heartbeat from the Python app (using `sd_notify`).
- Scope: `systemd/tcdd.service`, `main.py` (heartbeat)
- Risk: Low. Standard systemd practice. Must ensure crash loops don't cause infinite restarts (use `StartLimitBurst`).
- Test: Kill the Python process; verify systemd restarts it within 10 seconds.

---

### Phase 4 - Security Hardening (Optional but Recommended)

**QoL-12: Pairing Token Hardening**
- Problem: 8-character tokens with no expiration and no rate limiting are vulnerable to brute force (especially since the hotspot is an open network).
- Solution: (a) Add token expiration (5 minutes after generation). (b) Add rate limiting on `/api/pair/validate` (max 5 attempts per minute per IP, then 60-second lockout). (c) Increase token length to 12 characters.
- Scope: `pairing.py`, `main.py`
- Risk: Medium. Must not lock out legitimate users. Expiration timer needs to be communicated clearly in the UI.
- Test: Verify expired token is rejected. Verify rate limiting kicks in after 5 failed attempts.

**QoL-13: API Input Sanitization**
- Problem: API endpoints (especially `PUT /api/config`) accept arbitrary JSON without sanitization. This could lead to injection of unexpected config keys or oversized payloads.
- Solution: Whitelist allowed config keys. Reject unknown keys. Limit payload size to 10KB. Validate all string values for length and character set.
- Scope: `main.py`, `config.py`
- Risk: Low-Medium. Must ensure all legitimate config keys are whitelisted.
- Test: Send malformed payloads; verify 400 responses with clear error messages.

---

### Phase 5 - Visual Polish (Optional)

**QoL-14: Light Mode Toggle**
- Problem: The system only has a dark theme. In bright daylight conditions, a light theme may improve visibility on the 2.8" screen.
- Solution: Add a theme toggle (dark/light) to the settings page. Implement via CSS variable overrides on `:root[data-theme="light"]`. Persist preference in config. Both `style.css` and `mobile.css` already use CSS variables extensively, making this a straightforward variable swap.
- Scope: `style.css`, `mobile.css`, `app.js`, `mobile.js`, `index.html`, `mobile.html`, `config.json`
- Risk: Low. Pure CSS variable swaps. No structural changes needed.
- Test: Toggle theme; verify all pages render correctly in both modes. Verify preference persists across reloads.

---

## 3. Implementation Order and Dependencies

```
Phase 1 (Foundation)          Phase 2 (UX Polish)           Phase 3 (Ops)              Phase 4 (Security)
========================      ========================      ========================   ========================
QoL-1: WS Auto-Reconnect     QoL-5: Progress Indicators    QoL-9: Startup Self-Check  QoL-12: Token Hardening
QoL-2: Config Validation      QoL-6: Save Confirm + Undo    QoL-10: Log Rotation       QoL-13: API Sanitization
QoL-3: Health Monitoring      QoL-7: Visual Alerts           QoL-11: Systemd Watchdog
QoL-4: TTS Error Recovery     QoL-8: Button Safety
```

**Dependencies:**
- QoL-2 (Config Validation) should come before QoL-6 (Save Confirm) since validation is needed for proper save feedback.
- QoL-1 (WS Reconnect) should come before QoL-3 (Health Monitoring) since health events are delivered via WebSocket.
- QoL-5 (Progress Indicators) is independent and can be done in parallel with Phase 1.
- Phase 4 items are independent and can be done anytime.

---

## 4. What Will NOT Be Changed

To maintain simplicity and avoid scope creep:
- No database integration (file-based logging is sufficient for this use case)
- No multi-device pairing (single device is the intended design)
- No landscape/tablet UI (out of scope for 2.8" touchscreen)
- No OTA update mechanism (deploy via git pull + service restart)
- No custom model training pipeline
- No changes to detection logic or model format support

---

## 5. Estimated Config Changes

The following config keys may be added (to be reflected in `config-template-json.txt`):
- `system.startup_checks` (boolean, default: true) - Enable/disable startup self-check
- `logging.max_age_days` (integer, default: 30) - Max age for log files before deletion
- `logging.max_total_mb` (integer, default: 500) - Max total log size before rotation
- `pairing.token_expiry_seconds` (integer, default: 300) - Token validity duration
- `pairing.max_attempts_per_minute` (integer, default: 5) - Rate limit for token validation

Config version bump: `0.2.0-b202602270810` -> `0.3.0-bYYYYMMDDHHMM` (after all phases complete, or per-phase bumps)

---

## 6. Questions for Developer Review

Before proceeding with implementation, please clarify:

1. **Priority override**: Do you want to reorder any phases or promote/demote specific QoL items?
2. **Phase 4 (Security)**: Is token hardening a priority for your thesis, or is the current model acceptable for demonstration purposes?
3. **Visual alerts (QoL-7)**: Do you prefer a screen-edge glow, a top banner, or a different visual indicator? The system is for a small 2.8" screen, so space is limited.
4. **Hold-to-confirm (QoL-8)**: Is a 3-second hold appropriate for the touchscreen, or would you prefer a different confirmation method (e.g., swipe-to-confirm)?
5. **Systemd watchdog (QoL-11)**: Does your RPi setup use `sd_notify` compatible systemd? (Most RPi OS versions do, but worth confirming.)
6. **Log retention (QoL-10)**: Is 30 days retention with compression acceptable, or do you need all logs preserved for thesis data collection?
7. **Any features you specifically want that are NOT listed above?**
8. **Testing environment**: Can you test WebSocket reconnection locally (e.g., by restarting the Flask server on your dev machine), or does this need to be tested on the RPi only?

---

## 7. Precautions

- **Backup config.json** before any config schema changes. The migration system handles this, but a manual backup is recommended.
- **Phase 1 changes** touch core infrastructure (config, main loop, WebSocket). These should be tested thoroughly before deploying to the RPi.
- **Systemd changes (QoL-11)** require `sudo` access on the RPi. Test the service file syntax with `systemd-analyze verify` before enabling.
- **Rate limiting (QoL-12)** could lock out a legitimate user if they mistype the token. The lockout duration (60 seconds) should be short enough to avoid frustration.
- **Log rotation (QoL-10)** will delete old files. If you need historical data for your thesis, archive the `data/logs/` directory before enabling rotation.
