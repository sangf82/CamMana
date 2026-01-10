"""CSV Storage Module - Daily CSV files for captured car data"""
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import threading

# Storage paths
DATA_DIR = Path(__file__).parent.parent.parent / "database" / "data"
LOGS_DIR = DATA_DIR / "logs"

# Thread lock for file writes
_write_lock = threading.Lock()

# CSV Headers
CAR_HEADERS = [
    'id', 'timestamp', 'folder_path', 'plate_number', 'primary_color', 
    'wheel_count', 'front_cam_id', 'side_cam_id', 'confidence', 
    'class_name', 'bbox'
]

LOG_HEADERS = ['timestamp', 'camera_id', 'event_type', 'details']

def _ensure_dirs():
    """Ensure data directories exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

def _get_today_date() -> str:
    """Get today's date string for filename"""
    return datetime.now().strftime("%Y_%m_%d")

def _get_car_csv_path(date: Optional[str] = None) -> Path:
    """Get path to car CSV file for given date (default: today)"""
    _ensure_dirs()
    date_str = date or _get_today_date()
    return DATA_DIR / f"captured_cars_{date_str}.csv"

def _get_log_csv_path(date: Optional[str] = None) -> Path:
    """Get path to log CSV file for given date (default: today)"""
    _ensure_dirs()
    date_str = date or _get_today_date()
    return LOGS_DIR / f"detection_logs_{date_str}.csv"

def _init_csv_if_needed(filepath: Path, headers: List[str]):
    """Create CSV file with headers if it doesn't exist"""
    if not filepath.exists():
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def _generate_id() -> str:
    """Generate unique ID based on timestamp"""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

# ========== Captured Cars ==========

def save_captured_car(data: Dict[str, Any]) -> str:
    """Save captured car data to today's CSV file"""
    csv_path = _get_car_csv_path()
    _init_csv_if_needed(csv_path, CAR_HEADERS)
    
    record_id = _generate_id()
    bbox_str = json.dumps(data.get('bbox')) if data.get('bbox') else ''
    
    row = [
        record_id,
        data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        data.get('folder_path', ''),
        data.get('plate_number', ''),
        data.get('primary_color', ''),
        data.get('wheel_count', ''),
        data.get('front_cam_id', ''),
        data.get('side_cam_id', ''),
        data.get('confidence', ''),
        data.get('class_name', ''),
        bbox_str
    ]
    
    with _write_lock:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    return record_id

def get_captured_cars(date: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get captured cars from CSV file for given date (default: today)"""
    csv_path = _get_car_csv_path(date)
    if not csv_path.exists():
        return []
    
    cars = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            car = dict(row)
            # Parse bbox JSON
            if car.get('bbox'):
                try:
                    car['bbox'] = json.loads(car['bbox'])
                except:
                    car['bbox'] = None
            # Convert confidence to float
            if car.get('confidence'):
                try:
                    car['confidence'] = float(car['confidence'])
                except:
                    pass
            cars.append(car)
    
    # Return most recent first, limited
    return list(reversed(cars))[:limit]

def get_captured_cars_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get captured cars for a date range (format: YYYY_MM_DD)"""
    from datetime import timedelta
    
    start = datetime.strptime(start_date, "%Y_%m_%d")
    end = datetime.strptime(end_date, "%Y_%m_%d")
    
    all_cars = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y_%m_%d")
        cars = get_captured_cars(date=date_str, limit=1000)
        all_cars.extend(cars)
        current += timedelta(days=1)
    
    return all_cars

def search_by_plate(plate_number: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search cars by plate number"""
    cars = get_captured_cars(date=date, limit=1000)
    plate_lower = plate_number.lower()
    return [c for c in cars if plate_lower in (c.get('plate_number', '') or '').lower()]

def get_available_dates() -> List[str]:
    """Get list of dates that have CSV data"""
    _ensure_dirs()
    csv_files = list(DATA_DIR.glob("captured_cars_*.csv"))
    dates = []
    for f in csv_files:
        # Extract date from filename: captured_cars_YYYY_MM_DD.csv
        name = f.stem  # captured_cars_2026_01_10
        parts = name.split('_')
        if len(parts) >= 4:
            date_str = '_'.join(parts[-3:])  # 2026_01_10
            dates.append(date_str)
    return sorted(dates, reverse=True)

# ========== Detection Logs ==========

def log_detection_event(camera_id: str, event_type: str, details: Optional[Dict] = None):
    """Log detection event to today's log CSV"""
    csv_path = _get_log_csv_path()
    _init_csv_if_needed(csv_path, LOG_HEADERS)
    
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        camera_id,
        event_type,
        json.dumps(details) if details else ''
    ]
    
    with _write_lock:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

def get_detection_logs(camera_id: Optional[str] = None, date: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get detection logs from CSV file"""
    csv_path = _get_log_csv_path(date)
    if not csv_path.exists():
        return []
    
    logs = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            log = dict(row)
            # Filter by camera_id if specified
            if camera_id and log.get('camera_id') != camera_id:
                continue
            # Parse details JSON
            if log.get('details'):
                try:
                    log['details'] = json.loads(log['details'])
                except:
                    pass
            logs.append(log)
    
    # Return most recent first, limited
    return list(reversed(logs))[:limit]

# ========== Stats ==========

def get_daily_stats(date: Optional[str] = None) -> Dict[str, Any]:
    """Get statistics for a specific date"""
    cars = get_captured_cars(date=date, limit=10000)
    
    plates_detected = sum(1 for c in cars if c.get('plate_number'))
    colors_detected = sum(1 for c in cars if c.get('primary_color'))
    
    return {
        'date': date or _get_today_date(),
        'total_cars': len(cars),
        'plates_detected': plates_detected,
        'colors_detected': colors_detected,
        'detection_rate': round(plates_detected / len(cars) * 100, 1) if cars else 0
    }

# Initialize directories on import
_ensure_dirs()
print(f"[CSV Storage] Data directory: {DATA_DIR}")
