"""History data operations - Date-based CSV storage"""
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from backend.data_process._common import (
    HISTORY_HEADERS, DATA_DIR, _read_csv, _write_csv, _ensure_dirs, _write_lock
)
import csv


def _get_history_csv_path(date: Optional[str] = None) -> Path:
    """Get path to history CSV file for given date (format: dd/mm/yyyy or dd_mm_yyyy)"""
    _ensure_dirs()
    
    if date:
        # Support both / and _ formats
        date_str = date.replace('/', '_')
    else:
        # Default to today in dd_mm_yyyy format
        date_str = datetime.now().strftime("%d_%m_%Y")
    
    return DATA_DIR / f"history_{date_str}.csv"


def get_history_data(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get history data from CSV file for given date (default: today)"""
    csv_path = _get_history_csv_path(date)
    if not csv_path.exists():
        return []
    
    return _read_csv(csv_path)


def save_history_record(record: Dict[str, Any], date: Optional[str] = None):
    """Save a single history record to the appropriate CSV file"""
    csv_path = _get_history_csv_path(date)
    from backend.data_process._common import _init_csv_if_needed
    _init_csv_if_needed(csv_path, HISTORY_HEADERS)
    
    # Ensure all required fields are present
    row_data = {
        'plate': record.get('plate', ''),
        'location': record.get('location', ''),
        'time_in': record.get('time_in', ''),
        'time_out': record.get('time_out', '---'),
        'vol_std': record.get('vol_std', ''),
        'vol_measured': record.get('vol_measured', ''),
        'status': record.get('status', ''),
        'verify': record.get('verify', ''),
        'note': record.get('note', '')
    }
    
    with _write_lock:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_HEADERS)
            writer.writerow(row_data)


def save_history_data(records: List[Dict[str, Any]], date: Optional[str] = None):
    """Save multiple history records, replacing the entire file"""
    csv_path = _get_history_csv_path(date)
    _write_csv(csv_path, HISTORY_HEADERS, records)


def get_history_date_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get history data for a date range (format: dd/mm/yyyy)"""
    # Parse dates (dd/mm/yyyy format)
    start = datetime.strptime(start_date, "%d/%m/%Y")
    end = datetime.strptime(end_date, "%d/%m/%Y")
    
    all_records = []
    current = start
    while current <= end:
        date_str = current.strftime("%d_%m_%Y")
        records = get_history_data(date=date_str)
        all_records.extend(records)
        current += timedelta(days=1)
    
    return all_records


def get_available_history_dates() -> List[str]:
    """Get list of dates that have history CSV files
    
    Returns: List of date strings in dd/mm/yyyy format, sorted newest first
    """
    _ensure_dirs()
    csv_files = list(DATA_DIR.glob("history_*.csv"))
    dates = []
    
    for f in csv_files:
        # Extract date from filename: history_dd_mm_yyyy.csv
        name = f.stem  # history_16_01_2026
        parts = name.split('_')
        if len(parts) >= 4 and parts[0] == 'history':
            # Reconstruct date string
            date_str = f"{parts[1]}/{parts[2]}/{parts[3]}"  # dd/mm/yyyy
            dates.append(date_str)
    
    # Sort by date (newest first)
    try:
        dates.sort(key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
    except:
        dates.sort(reverse=True)
    
    return dates
