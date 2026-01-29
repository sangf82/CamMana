import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from backend.config import DATA_DIR
from backend.data_process.csv_utils import LOG_HEADERS

logger = logging.getLogger(__name__)

class LoggerLogic:
    HEADERS = LOG_HEADERS
    FILE_NAME_PREFIX = "logs_"

    def __init__(self):
        self.logs_dir = DATA_DIR / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_file(self) -> Path:
        date_str = datetime.now().strftime("%d-%m-%Y")
        return self.logs_dir / f"{self.FILE_NAME_PREFIX}{date_str}.csv"

    def _ensure_file(self, file_path: Path):
        if not file_path.exists():
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writeheader()

    def log_event(self, camera_id_or_name: str, event_type: str, details: str):
        """Log an event to the CSV log file."""
        file_path = self._get_current_file()
        self._ensure_file(file_path)
        
        # Try to resolve camera_id to camera_name if it looks like an ID
        camera_display = camera_id_or_name
        try:
            from backend.camera.logic import CameraLogic
            logic = CameraLogic()
            camera = logic.get_camera_by_id(camera_id_or_name)
            if camera:
                camera_display = camera.get('name', camera_id_or_name)
        except Exception as e:
            # Fallback to provided string if lookup fails
            pass

        row = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'camera_name': camera_display, # Now stores name
            'event_type': event_type,
            'details': details
        }
        
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writerow(row)
        except Exception as e:
            logger.error(f"Failed to write to CSV log: {e}")

    def get_logs(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logs for a specific date (default: today)."""
        if not date_str:
            date_str = datetime.now().strftime("%d-%m-%Y")
        
        file_path = self.logs_dir / f"{self.FILE_NAME_PREFIX}{date_str}.csv"
        if not file_path.exists():
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                logs = list(csv.DictReader(f))
                # Backward compatibility: normalize key to camera_name
                for log in logs:
                    if 'camera_id' in log and 'camera_name' not in log:
                        log['camera_name'] = log['camera_id']
                return logs
        except Exception as e:
            logger.error(f"Failed to read CSV log: {e}")
            return []

# Singleton instance
logger_logic = LoggerLogic()
