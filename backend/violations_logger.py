import json
import os
from datetime import datetime
from threading import Lock


class ViolationsLogger:
    """JSON Lines logger for violation events.

    Each violation event is stored as a single JSON object per line in a .jsonl file.
    """

    def __init__(self, log_dir: str = 'data/logs', prefix: str = 'violations'):
        self.log_dir = log_dir
        self.prefix = prefix
        self.lock = Lock()
        self.file = None
        self.filepath = None
        self._open_log_file()

    def _open_log_file(self):
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.prefix}_{timestamp}.jsonl"
        self.filepath = os.path.join(self.log_dir, filename)
        self.file = open(self.filepath, 'a', encoding='utf-8')

    def log(self, event: dict):
        """Append a violation event (dict) as a JSON line."""
        with self.lock:
            self.file.write(json.dumps(event, ensure_ascii=False) + "\n")
            self.file.flush()

    def tail(self, limit: int = 100):
        """Return the last N events from all violations files in the log directory."""
        events = []
        
        # Get all violations files sorted by modification time (newest first)
        try:
            violations_files = []
            if os.path.exists(self.log_dir):
                for filename in os.listdir(self.log_dir):
                    if filename.startswith(self.prefix) and filename.endswith('.jsonl'):
                        filepath = os.path.join(self.log_dir, filename)
                        violations_files.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time, newest first
            violations_files.sort(key=lambda x: x[1], reverse=True)
            
            # Read from files until we have enough events
            for filepath, _ in violations_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line in reversed(lines):  # Read in reverse to get newest first
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            events.append(json.loads(line))
                            if len(events) >= limit:
                                return events
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    continue
            
            return events
        except Exception as e:
            return []

    def close(self):
        with self.lock:
            if self.file:
                self.file.close()
                self.file = None
