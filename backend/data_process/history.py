"""History data operations - Date-based CSV storage

File lifecycle:
- Each day generates a new empty file with headers only
- Files expire after 48 hours and are automatically cleaned up
- New day file is created empty, ready for incoming camera/AI data
"""
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from backend.schemas import HistoryRecord
from backend.data_process._common import (
    HISTORY_HEADERS, DATA_DIR, _read_csv, _write_csv, _ensure_dirs, _write_lock, _init_csv_if_needed
)
import csv

# Files older than this will be cleaned up
EXPIRATION_HOURS = 48


def _get_history_csv_path(date: Optional[str] = None) -> Path:
    """Get path to history CSV file for given date (format: dd/mm/yyyy or dd_mm_yyyy)"""
    _ensure_dirs()
    
    if date:
        # Support both / and _ formats (and - from filenames?)
        date_str = date.replace('/', '_').replace('-', '_')
    else:
        # Default to today in dd_mm_yyyy format
        date_str = datetime.now().strftime("%d_%m_%Y")
    
    return DATA_DIR / f"history_{date_str}.csv"


def get_history_data(date: Optional[str] = None) -> List[HistoryRecord]:
    """Get history data from CSV file for given date (default: today)"""
    csv_path = _get_history_csv_path(date)
    if not csv_path.exists():
        return []
    
    data = _read_csv(csv_path)
    return [HistoryRecord(**item) for item in data]


def save_history_record(record: Union[HistoryRecord, Dict], date: Optional[str] = None):
    """Save a single history record to the appropriate CSV file"""
    csv_path = _get_history_csv_path(date)
    _init_csv_if_needed(csv_path, HISTORY_HEADERS)
    
    if isinstance(record, HistoryRecord):
        data = record.model_dump()
    else:
        data = record
    
    # Ensure all required fields are present (Pydantic does this, but Dict safety here)
    row_data = {
        'plate': data.get('plate', ''),
        'location': data.get('location', ''),
        'time_in': data.get('time_in', ''),
        'time_out': data.get('time_out', '---'),
        'vol_std': data.get('vol_std', ''),
        'vol_measured': data.get('vol_measured', ''),
        'status': data.get('status', ''),
        'verify': data.get('verify', ''),
        'note': data.get('note', '')
    }
    
    with _write_lock:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HISTORY_HEADERS)
            writer.writerow(row_data)


def save_history_data(records: List[HistoryRecord], date: Optional[str] = None):
    """Save multiple history records, replacing the entire file"""
    csv_path = _get_history_csv_path(date)
    data = [r.model_dump() for r in records]
    _write_csv(csv_path, HISTORY_HEADERS, data)


def update_history_record(
    plate: str, 
    time_in: str, 
    updates: Dict[str, Any],
    date: Optional[str] = None
) -> bool:
    """Update an existing history record by plate and time_in.
    Returns True if record was found and updated, False otherwise.
    """
    csv_path = _get_history_csv_path(date)
    if not csv_path.exists():
        return False
    
    with _write_lock:
        # Read all records
        records = _read_csv(csv_path)
        
        # Find and update the matching record
        updated = False
        for record in records:
            if record.get('plate') == plate and record.get('time_in') == time_in:
                record.update(updates)
                updated = True
                break
        
        if updated:
            # Write back all records
            _write_csv(csv_path, HISTORY_HEADERS, records)
        
        return updated


def get_history_date_range(start_date: str, end_date: str) -> List[HistoryRecord]:
    """Get history data for a date range (format: dd/mm/yyyy)"""
    # Parse dates (dd/mm/yyyy format)
    try:
        start = datetime.strptime(start_date, "%d/%m/%Y")
        end = datetime.strptime(end_date, "%d/%m/%Y")
    except ValueError:
        # Fallback formats?
        return []
    
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


def cleanup_expired_files() -> int:
    """Remove history CSV files older than 48 hours.
    
    Returns: Number of files deleted
    """
    _ensure_dirs()
    csv_files = list(DATA_DIR.glob("history_*.csv"))
    now = datetime.now()
    deleted_count = 0
    
    for f in csv_files:
        name = f.stem  # history_dd_mm_yyyy
        parts = name.split('_')
        if len(parts) >= 4 and parts[0] == 'history':
            try:
                date_str = f"{parts[1]}-{parts[2]}-{parts[3]}"  # dd-mm-yyyy for parsing
                file_date = datetime.strptime(date_str, "%d-%m-%Y")
                age = now - file_date
                if age > timedelta(hours=EXPIRATION_HOURS):
                    f.unlink()
                    deleted_count += 1
            except ValueError:
                pass  # Skip files with invalid date format
    
    return deleted_count


def initialize_today_file() -> bool:
    """Initialize today's history file if it doesn't exist.
    
    Behavior:
    - If today's file exists, do nothing
    - If today's file doesn't exist, create empty file with headers only
    - History files start empty and are filled by camera/AI process
    
    Returns: True if a new file was created
    """
    today_str = datetime.now().strftime("%d_%m_%Y")
    csv_path = _get_history_csv_path(today_str)
    
    if csv_path.exists():
        return False  # Already exists
    
    # Clean up expired files first
    cleanup_expired_files()
    
    # Create new empty file with headers only (no data rows)
    _init_csv_if_needed(csv_path, HISTORY_HEADERS)
    
    return True

