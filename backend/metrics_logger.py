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
        self.writer.writerow([
            'timestamp', 'frame', 'fps', 'detections', 'inference_time_ms', 'encode_time_ms', 'total_detections'
        ])
        self.file.flush()

    def log(self, frame, fps, detections, inference_time_ms, encode_time_ms, total_detections):
        with self.lock:
            self.frame_count += 1
            if self.frame_count % self.interval == 0:
                self.writer.writerow([
                    datetime.now().isoformat(),
                    frame,
                    fps,
                    detections,
                    f"{inference_time_ms:.2f}",
                    f"{encode_time_ms:.2f}",
                    total_detections
                ])
                self.file.flush()

    def close(self):
        with self.lock:
            if self.file:
                self.file.close()
                self.file = None
