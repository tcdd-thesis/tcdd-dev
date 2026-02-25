#!/usr/bin/env python3
"""
Text-to-Speech Alert Engine
Provides real-time spoken alerts for detected traffic control devices.
Uses espeak/espeak-ng directly via subprocess with a dedicated background
thread to avoid blocking the detection loop.

No Python TTS library needed — just the system ``espeak`` package.
"""

import logging
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
# ALERT MAPPING — Instructional style messages for each detection label
# =============================================================================

TRAFFIC_ALERTS = {
    # --- Critical (Tier 1) ---
    "stop":                              "Stop sign ahead. Prepare to stop.",
    "traffic_light_red":                 "Red light ahead. Please stop.",
    "traffic_light_red_no_left_turn":    "Red light ahead. No left turn allowed.",
    "traffic_light_red_no_right_turn":   "Red light ahead. No right turn allowed.",
    "traffic_light_red_right_turn":      "Red light, right turn signal. Proceed with caution.",
    "traffic_light_red_left_turn":       "Red light, left turn signal. Proceed with caution.",

    # --- High (Tier 2) ---
    "traffic_light_yellow":              "Yellow light ahead. Prepare to stop.",
    "yield":                             "Yield sign ahead. Slow down and give way.",
    "pedestrian_crossing":               "Pedestrian crossing ahead. Slow down.",
    "pwd_crossing":                      "PWD crossing ahead. Slow down and give way.",
    "yield_to_pedestrian":               "Yield to pedestrians ahead.",

    # --- Medium (Tier 3) ---
    "speed_limit_50kph":                 "Speed limit fifty kilometers per hour.",
    "speed_limit_60kph":                 "Speed limit sixty kilometers per hour.",
    "speed_limit_80kph":                 "Speed limit eighty kilometers per hour.",
    "no_uturn":                          "No U-turn allowed.",
    "no_left_turn":                      "No left turn allowed.",
    "no_right_turn":                     "No right turn allowed.",
    "no_turn_on_red":                    "No turn on red.",
    "no_left_turn_on_red":               "No left turn on red.",
    "no_right_turn_on_red":              "No right turn on red.",
    "no_parking":                        "No parking zone.",
    "do_not_block_intersection":         "Do not block the intersection.",
    "curve_right":                       "Curve to the right ahead.",
    "curve_left":                        "Curve to the left ahead.",

    # --- Low / Informational (Tier 4) ---
    "traffic_light_green":               "Green light. You may proceed.",
    "traffic_light_green_no_right_turn": "Green light. No right turn allowed.",
    "traffic_light_green_no_left_turn":  "Green light. No left turn allowed.",
    "traffic_light_green_right_turn":    "Green light, right turn signal.",
    "traffic_light_green_left_turn":     "Green light, left turn signal.",
    "no_lights":                         "No traffic lights ahead.",
    "bike_lane":                         "Bike lane ahead. Watch for cyclists.",
    "loading_unloading_zone":            "Loading and unloading zone.",
    "one_way_left":                      "One way street to the left.",
    "one_way_right":                     "One way street to the right.",
    "one_way":                           "One way street ahead.",
    "two_way":                           "Two way traffic ahead.",
    "keep_right":                        "Keep right.",
    "keep_left":                         "Keep left.",
    "road_split":                        "Road split ahead.",

    # =================================================================
    # OLD MODEL LABELS  (remove this section when switching to the
    # latest model that uses the labels above)
    # =================================================================
    "Stop":                              "Stop sign ahead. Prepare to stop.",
    "Red Light":                         "Red light ahead. Please stop.",
    "Green Light":                       "Green light. You may proceed.",
    "Speed Limit 10":                    "Speed limit ten kilometers per hour.",
    "Speed Limit 20":                    "Speed limit twenty kilometers per hour.",
    "Speed Limit 30":                    "Speed limit thirty kilometers per hour.",
    "Speed Limit 40":                    "Speed limit forty kilometers per hour.",
    "Speed Limit 50":                    "Speed limit fifty kilometers per hour.",
    "Speed Limit 60":                    "Speed limit sixty kilometers per hour.",
    "Speed Limit 70":                    "Speed limit seventy kilometers per hour.",
    "Speed Limit 80":                    "Speed limit eighty kilometers per hour.",
    "Speed Limit 90":                    "Speed limit ninety kilometers per hour.",
    "Speed Limit 100":                   "Speed limit one hundred kilometers per hour.",
    "Speed Limit 110":                   "Speed limit one hundred ten kilometers per hour.",
    "Speed Limit 120":                   "Speed limit one hundred twenty kilometers per hour.",
}

# =============================================================================
# PRIORITY TIERS — Lower number = higher priority
# =============================================================================

PRIORITY_TIERS = {
    # Tier 1 — Critical: must stop / immediate danger
    "stop":                              1,
    "traffic_light_red":                 1,
    "traffic_light_red_no_left_turn":    1,
    "traffic_light_red_no_right_turn":   1,
    "traffic_light_red_right_turn":      1,
    "traffic_light_red_left_turn":       1,

    # Tier 2 — High: caution / yield
    "traffic_light_yellow":              2,
    "yield":                             2,
    "pedestrian_crossing":               2,
    "pwd_crossing":                      2,
    "yield_to_pedestrian":               2,

    # Tier 3 — Medium: regulatory signs
    "speed_limit_50kph":                 3,
    "speed_limit_60kph":                 3,
    "speed_limit_80kph":                 3,
    "no_uturn":                          3,
    "no_left_turn":                      3,
    "no_right_turn":                     3,
    "no_turn_on_red":                    3,
    "no_left_turn_on_red":               3,
    "no_right_turn_on_red":              3,
    "no_parking":                        3,
    "do_not_block_intersection":         3,
    "curve_right":                       3,
    "curve_left":                        3,

    # Tier 4 — Low / Informational
    "traffic_light_green":               4,
    "traffic_light_green_no_right_turn": 4,
    "traffic_light_green_no_left_turn":  4,
    "traffic_light_green_right_turn":    4,
    "traffic_light_green_left_turn":     4,
    "no_lights":                         4,
    "bike_lane":                         4,
    "loading_unloading_zone":            4,
    "one_way_left":                      4,
    "one_way_right":                     4,
    "one_way":                           4,
    "two_way":                           4,
    "keep_right":                        4,
    "keep_left":                         4,
    "road_split":                        4,

    # =================================================================
    # OLD MODEL LABELS  (remove this section when switching to the
    # latest model that uses the labels above)
    # =================================================================
    "Stop":                              1,   # Critical
    "Red Light":                         1,   # Critical
    "Green Light":                       4,   # Informational
    "Speed Limit 10":                    3,   # Regulatory
    "Speed Limit 20":                    3,
    "Speed Limit 30":                    3,
    "Speed Limit 40":                    3,
    "Speed Limit 50":                    3,
    "Speed Limit 60":                    3,
    "Speed Limit 70":                    3,
    "Speed Limit 80":                    3,
    "Speed Limit 90":                    3,
    "Speed Limit 100":                   3,
    "Speed Limit 110":                   3,
    "Speed Limit 120":                   3,
}

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
        self.speech_rate = self._cfg("tts.speech_rate", 160)
        self.volume = self._cfg("tts.volume", 1.0)
        self.cooldown_seconds = self._cfg("tts.cooldown_seconds", 10)

        # Internal state
        self._last_spoken: dict[str, float] = {}
        self._queue: Queue = Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._engine_ready = False

        if not HAS_TTS:
            logger.warning("TTS engine disabled — espeak is not installed")
            self.enabled = False
            return

        if not self.enabled:
            logger.info("TTS engine disabled via configuration")
            return

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
            logger.info(f"✅ TTS engine ready  —  {_ESPEAK_BIN}  |  "
                        f"rate={self.speech_rate}, volume={self.volume}, "
                        f"cooldown={self.cooldown_seconds}s")
            logger.info(f"   espeak version: {result.stdout.strip()}")
            self._engine_ready = True
        except Exception as e:
            logger.error(f"❌ espeak sanity check failed: {e}")
            self._engine_ready = False
            self._running = False
            return

        while self._running:
            try:
                message = self._queue.get(timeout=0.5)
                if message is None:
                    # Poison pill — shut down
                    break

                self._speak_subprocess(message)

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

        cmd = [
            _ESPEAK_BIN,
            "-v", "en",
            "-s", str(int(self.speech_rate)),
            "-a", str(amplitude),
            "--", text          # '--' so text starting with '-' is safe
        ]

        try:
            subprocess.run(cmd, timeout=15, capture_output=True)
        except subprocess.TimeoutExpired:
            logger.warning(f"TTS subprocess timed out for: {text!r}")
        except Exception as e:
            logger.error(f"TTS subprocess error: {e}")

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
        self.speech_rate = self._cfg("tts.speech_rate", 160)
        self.volume = self._cfg("tts.volume", 1.0)

        now = time.time()

        # Build candidate list: (priority, label)
        candidates = []
        for det in detections:
            label = det.get("class_name", "").strip()
            if not label:
                continue
            if label not in TRAFFIC_ALERTS:
                logger.warning(f"TTS: label '{label}' not found in TRAFFIC_ALERTS — skipping")
                continue
            # Cooldown check
            last_time = self._last_spoken.get(label, 0)
            if now - last_time < self.cooldown_seconds:
                continue
            priority = PRIORITY_TIERS.get(label, DEFAULT_PRIORITY)
            candidates.append((priority, label))

        if not candidates:
            return

        # Pick highest priority (lowest number). Among ties choose first.
        candidates.sort(key=lambda c: c[0])
        _, best_label = candidates[0]

        message = TRAFFIC_ALERTS[best_label]
        self._last_spoken[best_label] = now

        # Enqueue for the worker thread
        self._queue.put(message)
        logger.debug(f"🔊 TTS queued: [{best_label}] \"{message}\"")

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
        return self.enabled and self._engine_ready and self._running

    def get_info(self) -> dict:
        """Return a status dict (useful for the /api/status endpoint)."""
        return {
            "enabled": self.enabled,
            "ready": self.is_ready(),
            "speech_rate": self.speech_rate,
            "volume": self.volume,
            "cooldown_seconds": self.cooldown_seconds,
            "queue_size": self._queue.qsize(),
            "labels_mapped": len(TRAFFIC_ALERTS),
        }
