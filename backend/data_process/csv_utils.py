"""Common utilities and constants for CSV data storage"""
import csv
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend import config

# Storage paths - Updated structure
DATA_DIR = config.DATA_DIR
LOGS_DIR = config.LOGS_DIR

# Thread lock for file writes
_write_lock = threading.RLock()

# CSV Headers - All data types
CAMERA_HEADERS = ['id', 'name', 'ip', 'onvif_port', 'rtsp_port', 'transport_mode', 'channel_id', 'stream_type', 'username', 'password', 'location', 'type', 'status', 'brand', 'location_id']

REGISTERED_CAR_HEADERS = ['id', 'plate_number', 'owner', 'model', 'color', 'notes', 'created_at', 'box_dimensions', 'standard_volume']

HISTORY_HEADERS = ['id', 'plate', 'location', 'time_in', 'time_out', 'vol_std', 'vol_measured', 'status', 'verify', 'note', 'folder_path']

CAR_HEADERS = ['id', 'timestamp', 'folder_path', 'plate_number', 'primary_color', 'wheel_count', 'front_cam_id', 'side_cam_id', 'confidence', 'class_name', 'bbox']

LOG_HEADERS = ['timestamp', 'camera_name', 'event_type', 'details']

LOCATION_HEADERS = ['id', 'name', 'tag']

TYPE_HEADERS = ['id', 'name', 'functions']


# Helper functions
def _ensure_dirs():
    """Ensure data directories exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _get_today_date() -> str:
    """Get today's date string for filename (YYYY_MM_DD format)"""
    return datetime.now().strftime("%Y_%m_%d")


def _generate_id() -> str:
    """Generate unique ID based on timestamp"""
    import uuid
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    """Generic CSV reader"""
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, headers: List[str], data: List[Dict[str, Any]]):
    """Generic CSV writer with thread safety"""
    with _write_lock:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)


def _init_csv_if_needed(filepath: Path, headers: List[str]):
    """Create CSV file with headers if it doesn't exist"""
    if not filepath.exists():
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)


def _get_config_csv_path(filename: str) -> Path:
    """Get path to config CSV files"""
    _ensure_dirs()
    return DATA_DIR / filename


# Initialize directories on import
_ensure_dirs()
print(f"[cam_mana] Data directory: {DATA_DIR}")
