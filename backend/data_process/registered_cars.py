"""Registered cars data operations - Date-based CSV storage"""
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.data_process._common import (
    REGISTERED_CAR_HEADERS, DATA_DIR, _generate_id, _read_csv, _write_csv, _ensure_dirs
)


def _get_registered_cars_csv_path(date: Optional[str] = None) -> Path:
    """Get path to registered cars CSV file for given date (format: dd-mm-yyyy)"""
    _ensure_dirs()
    
    if date:
        # Support both - and _ formats
        date_str = date.replace('_', '-')
    else:
        # Default to today in dd-mm-yyyy format
        date_str = datetime.now().strftime("%d-%m-%Y")
    
    return DATA_DIR / f"registered_cars_{date_str}.csv"


def get_registered_cars(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get registered cars from CSV file for given date (default: today)
    
    Auto-migration: If today's file doesn't exist, copies from previous day
    """
    csv_path = _get_registered_cars_csv_path(date)
    if not csv_path.exists():
        # If today's file doesn't exist, try to copy from previous day
        if not date:  # Only auto-migrate if requesting current date
            previous_date = _get_previous_registered_cars_date()
            if previous_date:
                old_cars = get_registered_cars(date=previous_date)
                # Update created_at to today's date
                today_str = datetime.now().strftime("%d-%m-%Y")
                for car in old_cars:
                    car['created_at'] = today_str
                # Save to today's file
                save_registered_cars(old_cars, date=None)
                return old_cars
        return []
    
    return _read_csv(csv_path)


def save_registered_cars(cars: List[Dict[str, Any]], date: Optional[str] = None):
    """Save registered cars, ensuring every item has a unique ID"""
    seen_ids = set()
    cleaned_cars = []
    
    for car in cars:
        current_id = str(car.get('id', '')).strip()
        
        # Determine if ID needs generation (missing or duplicate)
        if not current_id or current_id in seen_ids:
            new_id = _generate_id()
            # Paranoid check ensuring the generated ID isn't somehow already seen
            while new_id in seen_ids:
                new_id = _generate_id()
            car['id'] = new_id
        else:
            car['id'] = current_id
            
        seen_ids.add(car['id'])
        cleaned_cars.append(car)
    
    csv_path = _get_registered_cars_csv_path(date)
    _write_csv(csv_path, REGISTERED_CAR_HEADERS, cleaned_cars)


def import_registered_cars(new_cars: List[Dict[str, Any]], date: Optional[str] = None) -> Dict[str, Any]:
    """Import new registered cars data with smart merge logic
    
    Logic:
    1. Load existing data from the date's file
    2. Compare with new imported data:
       - If row exists in both (same plate_number), keep it with updated data
       - If row is new, add it
       - If row exists in old but not in new, delete it
    3. Update created_at to current date
    
    Returns: Dictionary with stats - added, updated, deleted counts
    """
    # Get existing cars
    existing_cars = get_registered_cars(date)
    
    # Create lookup by plate_number
    existing_by_plate = {car['plate_number']: car for car in existing_cars}
    new_by_plate = {car['plate_number']: car for car in new_cars}
    
    # Track changes
    added = []
    updated = []
    deleted = []
    final_cars = []
    
    current_date = date or datetime.now().strftime("%d-%m-%Y")
    
    # Process new cars
    for plate, new_car in new_by_plate.items():
        new_car['created_at'] = current_date  # Always update to current date
        
        if plate in existing_by_plate:
            # Keep existing ID, update data
            existing_car = existing_by_plate[plate]
            new_car['id'] = existing_car['id']
            
            # Check if actually updated
            if new_car != existing_car:
                updated.append(plate)
        else:
            # New car
            added.append(plate)
        
        final_cars.append(new_car)
    
    # Find deleted cars (in old but not in new)
    for plate in existing_by_plate:
        if plate not in new_by_plate:
            deleted.append(plate)
    
    # Save the final merged data
    save_registered_cars(final_cars, date)
    
    return {
        'added': len(added),
        'updated': len(updated),
        'deleted': len(deleted),
        'total': len(final_cars),
        'added_plates': added,
        'updated_plates': updated,
        'deleted_plates': deleted
    }


def get_available_registered_cars_dates() -> List[str]:
    """Get list of dates that have registered cars CSV files
    
    Returns: List of date strings in dd-mm-yyyy format, sorted newest first
    """
    _ensure_dirs()
    csv_files = list(DATA_DIR.glob("registered_cars_*.csv"))
    dates = []
    
    for f in csv_files:
        # Extract date from filename: registered_cars_dd-mm-yyyy.csv
        name = f.stem  # registered_cars_14-01-2026
        parts = name.split('_', 2)  # Split into max 3 parts
        if len(parts) >= 3 and parts[0] == 'registered' and parts[1] == 'cars':
            # The date part is everything after "registered_cars_"
            date_str = parts[2]  # dd-mm-yyyy
            dates.append(date_str)
    
    # Sort by date (newest first)
    try:
        dates.sort(key=lambda x: datetime.strptime(x, "%d-%m-%Y"), reverse=True)
    except:
        dates.sort(reverse=True)
    
    return dates


def _get_previous_registered_cars_date() -> Optional[str]:
    """Get the most recent registered cars file date before today"""
    dates = get_available_registered_cars_dates()
    if dates:
        return dates[0]  # Already sorted newest first
    return None
