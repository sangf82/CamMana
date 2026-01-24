"""Captured cars storage and detection logs"""
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from backend.schemas import CapturedCar, LogRecord
from backend.data_process._common import (
    CAR_HEADERS, LOG_HEADERS, DATA_DIR, LOGS_DIR, _generate_id, _read_csv, 
    _get_today_date, _ensure_dirs, _write_lock, _init_csv_if_needed
)
import shutil

CAR_HISTORY_DIR = Path("database/car_history")
EXPIRATION_HOURS = 48


def _get_car_csv_path(date: Optional[str] = None) -> Path:
    """Get path to car CSV file for given date (default: today)"""
    _ensure_dirs()
    date_str = date or _get_today_date()
    # Support underscore format used internally
    return DATA_DIR / f"captured_cars_{date_str}.csv"


def _get_log_csv_path(date: Optional[str] = None) -> Path:
    """Get path to log CSV file for given date (default: today)"""
    _ensure_dirs()
    date_str = date or _get_today_date()
    return LOGS_DIR / f"detection_logs_{date_str}.csv"


def save_captured_car(data: Union[Dict[str, Any], CapturedCar]) -> str:
    """Save captured car data to today's CSV file"""
    csv_path = _get_car_csv_path()
    _init_csv_if_needed(csv_path, CAR_HEADERS)
    
    # Handle both Dict and Pydantic input
    if isinstance(data, CapturedCar):
        car_dict = data.model_dump()
    else:
        car_dict = data

    record_id = _generate_id()
    
    # Ensure ID in the return/object? 
    # Logic in API might expect ID back.
    
    # Handle bbox serialization
    bbox_val = car_dict.get('bbox')
    bbox_str = json.dumps(bbox_val) if bbox_val else ''
    
    row = [
        record_id,
        car_dict.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        car_dict.get('folder_path', ''),
        car_dict.get('plate_number', ''),
        car_dict.get('primary_color', ''),
        car_dict.get('wheel_count', ''),
        car_dict.get('front_cam_id', ''),
        car_dict.get('side_cam_id', ''),
        car_dict.get('confidence', ''),
        car_dict.get('class_name', ''),
        bbox_str
    ]
    
    with _write_lock:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    return record_id


def get_captured_cars(date: Optional[str] = None, limit: int = 50) -> List[CapturedCar]:
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
            cars.append(CapturedCar(**car))
    
    # Return most recent first, limited
    return list(reversed(cars))[:limit]


def get_captured_cars_range(start_date: str, end_date: str) -> List[CapturedCar]:
    """Get captured cars for a date range (format: YYYY_MM_DD)"""
    try:
        start = datetime.strptime(start_date, "%Y_%m_%d")
        end = datetime.strptime(end_date, "%Y_%m_%d")
    except ValueError:
        return []
    
    all_cars = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y_%m_%d")
        cars = get_captured_cars(date=date_str, limit=1000)
        all_cars.extend(cars)
        current += timedelta(days=1)
    
    return all_cars


def search_by_plate(plate_number: str, date: Optional[str] = None) -> List[CapturedCar]:
    """Search cars by plate number"""
    cars = get_captured_cars(date=date, limit=1000)
    plate_lower = plate_number.lower()
    return [c for c in cars if plate_lower in (c.plate_number or '').lower()]


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


def get_daily_stats(date: Optional[str] = None) -> Dict[str, Any]:
    """Get statistics for a specific date"""
    cars = get_captured_cars(date=date, limit=10000)
    
    plates_detected = sum(1 for c in cars if c.plate_number)
    colors_detected = sum(1 for c in cars if c.primary_color)
    
    return {
        'date': date or _get_today_date(),
        'total_cars': len(cars),
        'plates_detected': plates_detected,
        'colors_detected': colors_detected,
        'detection_rate': round(plates_detected / len(cars) * 100, 1) if cars else 0
    }


# Detection Logs
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


def get_detection_logs(camera_id: Optional[str] = None, date: Optional[str] = None, limit: int = 100) -> List[LogRecord]:
    """Get detection logs from CSV file"""
    csv_path = _get_log_csv_path(date)
    if not csv_path.exists():
        return []
    
    logs = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            log_dict = dict(row)
            # Filter by camera_id if specified
            if camera_id and log_dict.get('camera_id') != camera_id:
                continue
            # Parse details JSON
            if log_dict.get('details'):
                try:
                    log_dict['details'] = json.loads(log_dict['details'])
                except:
                    pass
            logs.append(LogRecord(**log_dict))
    
    # Return most recent first, limited
    return list(reversed(logs))[:limit]


def cleanup_expired_car_history_folders() -> int:
    """Remove car history folders older than 48 hours.
    
    Returns: Number of folders deleted
    """
    if not CAR_HISTORY_DIR.exists():
        return 0
        
    folders = list(CAR_HISTORY_DIR.iterdir())
    now = datetime.now()
    deleted_count = 0
    
    for f in folders:
        if not f.is_dir():
            continue
            
        name = f.name  # dd-mm-yyyy
        try:
            # Try parsing multiple formats if needed, but currently it's dd-mm-yyyy
            folder_date = datetime.strptime(name, "%d-%m-%Y")
            age = now - folder_date
            
            # Use strict > 48 hours check
            if age > timedelta(hours=EXPIRATION_HOURS):
                shutil.rmtree(f)
                deleted_count += 1
                print(f"[cleanup] Deleted expired car history folder: {name}")
        except ValueError:
            pass  # Skip folders that don't match date format
            
    return deleted_count

