#!/usr/bin/env python3
"""Unit tests for TTS persistence gating behavior."""

import os
import sys
import threading
import unittest
from queue import Queue
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from tts import TTSEngine  # noqa: E402


class DummyConfig:
    """Simple config stub used by tests."""

    def __init__(self):
        self.values = {
            "tts.enabled": True,
            "tts.voice": "en+f3",
            "tts.speech_rate": 160,
            "tts.volume": 1.0,
            "tts.cooldown_seconds": 10,
        }

    def get(self, key, default=None):
        return self.values.get(key, default)


class TTSPersistenceTests(unittest.TestCase):
    def _build_engine(self):
        """Build a TTSEngine instance without starting the subprocess worker."""
        engine = TTSEngine.__new__(TTSEngine)
        engine.config = DummyConfig()
        engine.enabled = True
        engine._engine_ready = True
        engine.voice = "en+f3"
        engine.speech_rate = 160
        engine.volume = 1.0
        engine.cooldown_seconds = 10
        engine._last_spoken = {}
        engine._queue = Queue()
        engine._on_speak_callback = None
        engine._mapping_lock = threading.Lock()
        engine._alerts_map = {"stop": "Stop sign ahead"}
        engine._priority_map = {"stop": 1}
        engine.active_profile = "default"
        engine._warned_unmapped_labels = set()

        engine._persistence_min_visible_ms = 120.0
        engine._persistence_min_consecutive = 3
        engine._persistence_reset_gap_seconds = 0.35
        engine._persistence_stale_seconds = 1.0
        engine._persistence_log_interval_seconds = 2.0
        engine._persistence_state = {}
        engine._persistence_log_last = {}

        return engine

    @staticmethod
    def _det(label="stop", confidence=0.95):
        return [{"class_name": label, "confidence": confidence, "bbox": [10, 10, 20, 20]}]

    def test_transient_detection_does_not_trigger_tts(self):
        engine = self._build_engine()

        with patch("tts.time.time", side_effect=[100.00, 100.04]):
            engine.process_detections(self._det())
            engine.process_detections(self._det())

        self.assertEqual(engine._queue.qsize(), 0)

    def test_sustained_detection_triggers_once_after_gate(self):
        engine = self._build_engine()

        with patch("tts.time.time", side_effect=[100.00, 100.06, 100.13]):
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections(self._det())

        self.assertEqual(engine._queue.qsize(), 1)
        self.assertEqual(engine._queue.get_nowait(), "Stop sign ahead")

    def test_disappearance_resets_consecutive_streak(self):
        engine = self._build_engine()

        with patch("tts.time.time", side_effect=[100.00, 100.06, 100.10, 100.16, 100.24, 100.31]):
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections([])
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections(self._det())

        self.assertEqual(engine._queue.qsize(), 1)

    def test_cooldown_still_blocks_repeat_after_valid_trigger(self):
        engine = self._build_engine()

        with patch("tts.time.time", side_effect=[100.00, 100.06, 100.13, 100.20, 100.27, 100.34]):
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections(self._det())
            engine.process_detections(self._det())

        self.assertEqual(engine._queue.qsize(), 1)


if __name__ == "__main__":
    unittest.main()
