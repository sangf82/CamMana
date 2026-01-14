"""Data Processing Package - Modular CSV Storage

This package provides data storage operations organized by feature.
All CSV operations are thread-safe and use date-based file naming where appropriate.
"""

# Cameras
from backend.data_process.cameras import (
    get_cameras_config, save_cameras_config, save_camera,
    get_camera, get_all_cameras, get_cameras_by_tag, delete_camera
)

# Registered Cars
from backend.data_process.registered_cars import (
    get_registered_cars, save_registered_cars, import_registered_cars,
    get_available_registered_cars_dates
)

# History
from backend.data_process.history import (
    get_history_data, save_history_record, save_history_data,
    get_history_date_range, get_available_history_dates
)

# Captured Cars & Logs
from backend.data_process.captured_cars import (
    save_captured_car, get_captured_cars, get_captured_cars_range,
    search_by_plate, get_available_dates, get_daily_stats,
    log_detection_event, get_detection_logs
)

# Configuration
from backend.data_process.config import (
    get_locations, save_locations, get_cam_types, save_cam_types
)

# Report (placeholder)
from backend.data_process import report

__all__ = [
    # Cameras
    'get_cameras_config', 'save_cameras_config', 'save_camera',
    'get_camera', 'get_all_cameras', 'get_cameras_by_tag', 'delete_camera',
    
   # Registered Cars
    'get_registered_cars', 'save_registered_cars', 'import_registered_cars',
    'get_available_registered_cars_dates',
    
    # History
    'get_history_data', 'save_history_record', 'save_history_data',
    'get_history_date_range', 'get_available_history_dates',
    
    # Captured Cars & Logs
    'save_captured_car', 'get_captured_cars', 'get_captured_cars_range',
    'search_by_plate', 'get_available_dates', 'get_daily_stats',
    'log_detection_event', 'get_detection_logs',
    
    # Configuration
    'get_locations', 'save_locations', 'get_cam_types', 'save_cam_types',
    
    # Report module
    'report'
]
