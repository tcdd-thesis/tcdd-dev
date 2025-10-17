import csv
import os
from datetime import datetime
from threading import Lock

class MetricsLogger:
    def __init__(self, log_dir='data/logs', prefix='metrics', interval=1):
        self.log_dir = log_dir
        self.prefix = prefix
        self.interval = interval
        self.lock = Lock()
        self.file = None
        self.writer = None
        self.frame_count = 0
        self._open_log_file()

    def _open_log_file(self):
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.prefix}_{timestamp}.csv"
        self.filepath = os.path.join(self.log_dir, filename)
        self.file = open(self.filepath, 'w', newline='')
        self.writer = csv.writer(self.file)
        # Match C++ header order
        self.writer.writerow([
            'timestamp',
            'fps',
            'inference_time_ms',
            'detections_count',
            'cpu_usage_percent',
            'ram_usage_mb',
            'camera_frame_time_ms',
            'jpeg_encode_time_ms',
            'total_detections',
            'dropped_frames',
            'queue_size'
        ])
        self.file.flush()

    def log(self, *, timestamp_iso: str, fps: float, inference_time_ms: float,
            detections_count: int, cpu_usage_percent: float, ram_usage_mb: float,
            camera_frame_time_ms: float, jpeg_encode_time_ms: float,
            total_detections: int, dropped_frames: int, queue_size: int):
        with self.lock:
            self.frame_count += 1
            if self.frame_count % self.interval == 0:
                self.writer.writerow([
                    timestamp_iso,
                    f"{fps:.2f}",
                    f"{inference_time_ms:.2f}",
                    detections_count,
                    f"{cpu_usage_percent:.2f}",
                    f"{ram_usage_mb:.2f}",
                    f"{camera_frame_time_ms:.2f}",
                    f"{jpeg_encode_time_ms:.2f}",
                    total_detections,
                    dropped_frames,
                    queue_size
                ])
                self.file.flush()

    def close(self):
        with self.lock:
            if self.file:
                self.file.close()
                self.file = None
