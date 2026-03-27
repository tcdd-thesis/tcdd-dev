#!/usr/bin/env python3
"""
Text-to-Speech Alert Engine
Provides real-time spoken alerts for detected traffic control devices.
Uses espeak/espeak-ng directly via subprocess with a dedicated background
thread to avoid blocking the detection loop.

No Python TTS library needed — just the system ``espeak`` package.
"""

import logging
import json
import os
import shutil
import subprocess
import time
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)

# Check if espeak (or espeak-ng) is available on the system
_ESPEAK_BIN = shutil.which("espeak-ng") or shutil.which("espeak")
HAS_TTS = _ESPEAK_BIN is not None
if not HAS_TTS:
    logger.warning("Neither espeak-ng nor espeak found on PATH — TTS alerts will be disabled")


# =============================================================================
# TTS PROFILE REGISTRY SETTINGS
# =============================================================================

DEFAULT_PROFILES_FILE = "data/tts_profiles.json"
DEFAULT_PROFILES_TEMPLATE_FILE = "data/tts_profiles_template_json.txt"


def _strip_json_comments(text: str) -> str:
    """Strip // comments from JSON-with-comments text safely."""
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        in_string = False
        escape_next = False
        result = []
        i = 0

        while i < len(line):
            ch = line[i]
            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue
            if ch == "\\" and in_string:
                result.append(ch)
                escape_next = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                i += 1
                continue
            if not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            result.append(ch)
            i += 1

        stripped = "".join(result).rstrip()
        if stripped.strip():
            cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)

# Fallback priority for any unknown label
DEFAULT_PRIORITY = 5


class TTSEngine:
    """
    Threaded Text-to-Speech engine for real-time driver alerts.

    Uses ``espeak`` / ``espeak-ng`` via subprocess — no Python TTS library
    required.  Each speech request is executed as a short-lived subprocess
    on a dedicated background thread so the detection loop is never blocked.

    Features:
        - Dedicated background thread so speech never blocks detection.
        - Per-label cooldown to avoid repetitive announcements.
        - Priority system: when multiple labels are detected in one frame,
          only the highest-priority alert is spoken.
    """

    def __init__(self, config=None):
        """
        Initialize the TTS engine.

        Args:
            config: Config object. Reads keys under ``tts.*``.
        """
        self.config = config

        # Settings (with defaults)
        self.enabled = self._cfg("tts.enabled", True)
        self.voice = self._cfg("tts.voice", "en+f3")
        self.speech_rate = self._cfg("tts.speech_rate", 160)
        self.volume = self._cfg("tts.volume", 1.0)
        self.cooldown_seconds = self._cfg("tts.cooldown_seconds", 10)
        self.profiles_file = self._cfg("tts.profiles_file", DEFAULT_PROFILES_FILE)
        self.profiles_template_file = self._cfg(
            "tts.profiles_template_file",
            DEFAULT_PROFILES_TEMPLATE_FILE,
        )
        self.active_profile = self._cfg("tts.active_profile", "default")

        # Internal state
        self._last_spoken: dict[str, float] = {}
        self._queue: Queue = Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._engine_ready = False
        self._on_speak_callback = None  # Called with (text, label, priority) when alert fires

        self._on_error_callback = None   # Called with (message: str) when TTS fails fatally
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._mapping_lock = threading.Lock()
        self._alerts_map: dict[str, str] = {}
        self._priority_map: dict[str, int] = {}
        self._profile_source = "uninitialized"
        self._profile_load_error = ""
        self._warned_unmapped_labels = set()

        if not HAS_TTS:
            logger.warning("TTS engine disabled — espeak is not installed")
            self.enabled = False
            return

        if not self.enabled:
            logger.info("TTS engine disabled via configuration")
            return

        # Load profile-driven mappings before starting worker.
        self.reload_profile_config()

        # Start the background worker
        self._start_worker()

    # -----------------------------------------------------------------
    # Configuration helper
    # -----------------------------------------------------------------

    def _cfg(self, key: str, default):
        """Read a config value, falling back to *default* if config is absent."""
        if self.config:
            return self.config.get(key, default)
        return default

    def _ensure_profiles_file(self):
        """
        Ensure runtime TTS profile registry exists and is valid JSON.

        If the runtime file is missing or invalid, recreate it from
        ``tts.profiles_template_file``.
        """
        runtime_file = self._cfg("tts.profiles_file", DEFAULT_PROFILES_FILE)
        template_file = self._cfg(
            "tts.profiles_template_file",
            DEFAULT_PROFILES_TEMPLATE_FILE,
        )

        self.profiles_file = runtime_file
        self.profiles_template_file = template_file

        if not runtime_file:
            raise ValueError("tts.profiles_file is empty")
        if not template_file:
            raise ValueError("tts.profiles_template_file is empty")

        runtime_valid = False
        if os.path.exists(runtime_file):
            try:
                with open(runtime_file, "r", encoding="utf-8") as f:
                    json.load(f)
                runtime_valid = True
            except Exception as e:
                logger.warning(
                    "TTS runtime profile file is invalid (%s); regenerating from template",
                    e,
                )

        if runtime_valid:
            return

        if not os.path.exists(template_file):
            raise FileNotFoundError(
                f"TTS profile template not found: {template_file}"
            )

        with open(template_file, "r", encoding="utf-8") as f:
            template_text = f.read()

        cleaned_json = _strip_json_comments(template_text)
        registry = json.loads(cleaned_json)

        profiles = registry.get("profiles", {})
        if not isinstance(profiles, dict) or not profiles:
            raise ValueError("TTS profile template has no valid 'profiles' object")

        runtime_dir = os.path.dirname(runtime_file)
        if runtime_dir:
            os.makedirs(runtime_dir, exist_ok=True)

        with open(runtime_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            f.write("\n")

        logger.info(
            "TTS profile registry created from template: %s -> %s",
            template_file,
            runtime_file,
        )

    def _set_active_profile_maps(
        self,
        alerts_map: dict,
        priority_map: dict,
        profile_source: str,
        profile_name: str,
        load_error: str = "",
    ):
        """Atomically swap the active prompt/priority maps used by process_detections."""
        with self._mapping_lock:
            self._alerts_map = alerts_map
            self._priority_map = priority_map
            self._profile_source = profile_source
            self.active_profile = profile_name
            self._profile_load_error = load_error
            self._warned_unmapped_labels = set()

    def reload_profile_config(self):
        """
        Reload prompt/priority mappings from the configured profile registry.
        """
        profiles_file = self._cfg("tts.profiles_file", DEFAULT_PROFILES_FILE)
        template_file = self._cfg(
            "tts.profiles_template_file",
            DEFAULT_PROFILES_TEMPLATE_FILE,
        )
        profile_name = self._cfg("tts.active_profile", "default")
        self.profiles_file = profiles_file
        self.profiles_template_file = template_file

        try:
            self._ensure_profiles_file()

            with open(profiles_file, "r", encoding="utf-8") as f:
                registry = json.load(f)

            profiles = registry.get("profiles", {})
            if not isinstance(profiles, dict) or not profiles:
                raise ValueError("missing or invalid 'profiles' object")

            profile = profiles.get(profile_name)
            if not isinstance(profile, dict):
                raise ValueError(f"profile '{profile_name}' not found")

            prompts = profile.get("prompts", {})
            priorities = profile.get("priorities", {})

            if not isinstance(prompts, dict) or not prompts:
                raise ValueError(f"profile '{profile_name}' has no valid prompts map")
            if priorities and not isinstance(priorities, dict):
                raise ValueError(f"profile '{profile_name}' priorities must be an object")

            active_alerts = {}
            for key, value in prompts.items():
                k = str(key).strip()
                v = str(value).strip()
                if k and v:
                    active_alerts[k] = v

            active_priorities = {}
            for key, value in priorities.items():
                k = str(key).strip()
                if not k:
                    continue
                try:
                    active_priorities[k] = int(value)
                except (TypeError, ValueError):
                    logger.warning(
                        "TTS profile '%s': invalid priority for '%s': %r",
                        profile_name,
                        k,
                        value,
                    )

            if not active_alerts:
                raise ValueError(f"profile '{profile_name}' produced an empty prompts map")

            self._set_active_profile_maps(
                active_alerts,
                active_priorities,
                profile_source="registry",
                profile_name=profile_name,
            )
            logger.info(
                "TTS profile loaded: %s (%s prompts, %s priorities)",
                profile_name,
                len(active_alerts),
                len(active_priorities),
            )

        except Exception as e:
            load_error = str(e)
            logger.error("TTS profile registry load failed: %s", load_error)
            self._set_active_profile_maps(
                {},
                {},
                profile_source="error",
                profile_name=profile_name,
                load_error=load_error,
            )
            if self._on_error_callback:
                try:
                    self._on_error_callback(f"TTS profile load failed: {load_error}")
                except Exception as callback_error:
                    logger.error("TTS error callback exception: %s", callback_error)

    # -----------------------------------------------------------------
    # Background worker
    # -----------------------------------------------------------------

    def _start_worker(self):
        """Spin up the daemon thread that processes the speech queue."""
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="tts-worker")
        self._thread.start()
        logger.info("TTS background worker started")

    def _worker_loop(self):
        """
        Runs on its own thread.  Pulls messages from the queue and speaks
        them via ``espeak`` subprocess calls.
        """
        # Quick sanity check — make sure espeak actually works
        try:
            result = subprocess.run(
                [_ESPEAK_BIN, "--version"],
                capture_output=True, text=True, timeout=5
            )
            logger.info(f"TTS engine ready  —  {_ESPEAK_BIN}  |  "
                        f"voice={self.voice}, rate={self.speech_rate}, "
                        f"volume={self.volume}, cooldown={self.cooldown_seconds}s")
            logger.info(f"   espeak version: {result.stdout.strip()}")
            self._engine_ready = True
        except Exception as e:
            logger.error(f"espeak sanity check failed: {e}")
            self._engine_ready = False
            self._running = False
            return

        while self._running:
            try:
                message = self._queue.get(timeout=0.5)
                if message is None:
                    # Poison pill — shut down
                    break

                ok = self._speak_subprocess(message)
                if ok:
                    self._consecutive_failures = 0
                else:
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= self._max_consecutive_failures:
                        logger.error("TTS: %d consecutive failures — pausing for 60s before retry",
                                     self._consecutive_failures)
                        if self._on_error_callback:
                            try:
                                self._on_error_callback(
                                    f"TTS paused after {self._consecutive_failures} consecutive failures, retrying in 60s")
                            except Exception as e:
                                logger.error(f"TTS error callback exception: {e}")
                        # Sleep and retry instead of permanently dying
                        import time as _time
                        _time.sleep(60)
                        self._consecutive_failures = 0
                        logger.info("TTS: Resuming after cooldown")

            except Empty:
                continue
            except Exception as e:
                logger.error(f"TTS worker error: {e}")

        logger.info("TTS background worker stopped")

    def _speak_subprocess(self, text: str):
        """
        Speak *text* by invoking espeak as a subprocess.

        espeak flags used:
            -s <wpm>    speech rate in words-per-minute
            -a <0-200>  amplitude (volume); we map our 0.0-1.0 to 0-200
            -v en       English voice
        """
        # Map volume 0.0–1.0  →  espeak amplitude 0–200
        amplitude = int(max(0.0, min(1.0, self.volume)) * 200)

        # Re-read voice from config in case it was changed at runtime
        self.voice = self._cfg("tts.voice", "en+f3")

        cmd = [
            _ESPEAK_BIN,
            "-v", self.voice,
            "-s", str(int(self.speech_rate)),
            "-a", str(amplitude),
            "--", text          # '--' so text starting with '-' is safe
        ]

        try:
            result = subprocess.run(cmd, timeout=15, capture_output=True)
            if result.returncode != 0:
                logger.warning(f"TTS subprocess exited with code {result.returncode} for: {text!r}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.warning(f"TTS subprocess timed out for: {text!r}")
            return False
        except Exception as e:
            logger.error(f"TTS subprocess error: {e}")
            return False

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def process_detections(self, detections: list[dict]):
        """
        Accept a list of detections from a single frame and speak only
        the highest-priority alert (respecting cooldowns).

        Each detection dict must contain at least ``class_name`` (str).

        Args:
            detections: List of detection dicts from Detector.detect().
        """
        if not self.enabled or not self._engine_ready:
            return

        if not detections:
            return

        # Reload runtime settings from config each call (cheap dict lookups)
        self.enabled = self._cfg("tts.enabled", True)
        if not self.enabled:
            logger.warning("TTS: disabled via config after reload")
            return
        self.cooldown_seconds = self._cfg("tts.cooldown_seconds", 10)
        self.voice = self._cfg("tts.voice", "en+f3")
        self.speech_rate = self._cfg("tts.speech_rate", 160)
        self.volume = self._cfg("tts.volume", 1.0)

        with self._mapping_lock:
            alerts_map = self._alerts_map
            priority_map = self._priority_map

        if not alerts_map:
            return

        now = time.time()

        # Build candidate list: (priority, label)
        candidates = []
        for det in detections:
            label = det.get("class_name", "").strip()
            if not label:
                continue
            if label not in alerts_map:
                should_warn = False
                with self._mapping_lock:
                    if label not in self._warned_unmapped_labels:
                        self._warned_unmapped_labels.add(label)
                        should_warn = True
                if should_warn:
                    logger.warning(
                        "TTS: label '%s' not found in active profile '%s' — skipping",
                        label,
                        self.active_profile,
                    )
                continue
            # Cooldown check
            last_time = self._last_spoken.get(label, 0)
            if now - last_time < self.cooldown_seconds:
                continue
            priority = priority_map.get(label, DEFAULT_PRIORITY)
            candidates.append((priority, label))

        if not candidates:
            return

        # Pick highest priority (lowest number). Among ties choose first.
        candidates.sort(key=lambda c: c[0])
        _, best_label = candidates[0]

        message = alerts_map[best_label]
        self._last_spoken[best_label] = now

        # Enqueue for the worker thread
        self._queue.put(message)
        logger.debug(f"TTS queued: [{best_label}] \"{message}\"")

        # Fire the on_speak callback (used by phone audio relay)
        if self._on_speak_callback:
            try:
                priority = priority_map.get(best_label, DEFAULT_PRIORITY)
                self._on_speak_callback(message, best_label, priority)
            except Exception as e:
                logger.error(f"TTS on_speak callback error: {e}")

    def speak(self, text: str):
        """
        Directly speak arbitrary text (bypasses priority/cooldown).
        Useful for system announcements like startup confirmation.

        Args:
            text: The text to speak.
        """
        if not self.enabled or not self._engine_ready:
            return
        self._queue.put(text)

        # Fire the on_speak callback for phone audio relay
        if self._on_speak_callback:
            try:
                self._on_speak_callback(text, 'system', 0)
            except Exception as e:
                logger.error(f"TTS on_speak callback error: {e}")

    def set_on_speak_callback(self, callback):
        """
        Register a callback invoked whenever TTS wants to speak.
        The callback receives (text: str, label: str, priority: int).

        Args:
            callback: Function(text, label, priority) -> None, or None to clear.
        """
        self._on_speak_callback = callback
        logger.info(f"TTS on_speak callback {'set' if callback else 'cleared'}")

    def set_on_error_callback(self, callback):
        """
        Register a callback invoked when TTS fails fatally (consecutive errors).
        The callback receives (message: str).
        """
        self._on_error_callback = callback

    def stop(self):
        """Shut down the TTS worker thread gracefully."""
        if not self._running:
            return
        self._running = False
        # Send poison pill so the worker unblocks
        self._queue.put(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("TTS engine stopped")

    def is_ready(self) -> bool:
        """Return True if the TTS engine is initialised and running."""
        with self._mapping_lock:
            has_profile = bool(self._alerts_map)
        return self.enabled and self._engine_ready and self._running and has_profile

    def get_info(self) -> dict:
        """Return a status dict (useful for the /api/status endpoint)."""
        with self._mapping_lock:
            labels_mapped = len(self._alerts_map)

        return {
            "enabled": self.enabled,
            "ready": self.is_ready(),
            "speech_rate": self.speech_rate,
            "volume": self.volume,
            "cooldown_seconds": self.cooldown_seconds,
            "queue_size": self._queue.qsize(),
            "labels_mapped": labels_mapped,
            "active_profile": self.active_profile,
            "profiles_file": self.profiles_file,
            "profiles_template_file": self.profiles_template_file,
            "profile_source": self._profile_source,
            "profile_load_error": self._profile_load_error,
        }
