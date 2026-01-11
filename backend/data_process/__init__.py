# Data Processing Package
# db.py handles camera configuration (SQLite)
# csv_storage.py handles captured car data (daily CSV files)

from backend.data_process.db import (
    init_db, save_camera, get_camera, get_all_cameras,
    get_cameras_by_tag, delete_camera, update_camera_detection_mode
)

from backend.data_process.csv_storage import (
    save_captured_car, get_captured_cars, search_by_plate,
    log_detection_event, get_detection_logs, get_available_dates,
    get_daily_stats, get_captured_cars_range
)

# Export csv_storage module directly
from backend.data_process import csv_storage

__all__ = [
    # DB (cameras only)
    'init_db', 'save_camera', 'get_camera', 'get_all_cameras',
    'get_cameras_by_tag', 'delete_camera', 'update_camera_detection_mode',
    # CSV Storage (captured cars & logs)
    'save_captured_car', 'get_captured_cars', 'search_by_plate',
    'log_detection_event', 'get_detection_logs', 'get_available_dates',
    'get_daily_stats', 'get_captured_cars_range',
    'csv_storage'
]
