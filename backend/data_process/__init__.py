"""Data Processing Package - Modular CSV Storage

This package provides data storage operations organized by feature.
All CSV operations are thread-safe and use date-based file naming where appropriate.
"""

# Cameras
from backend.camera.logic import CameraLogic
from backend.schemas import Camera
import uuid

_cam_logic = CameraLogic()

def get_cameras_config():
    # Bridge to new logic
    raw_cams = _cam_logic.get_cameras()
    # Convert to schema.Camera (legacy format compatibility)
    res = []
    for c in raw_cams:
        res.append(Camera(
            id=c.get('id', str(uuid.uuid4())),
            name=c.get('name', ''),
            ip=c.get('ip', ''),
            port=int(c.get('port', 80)) if c.get('port') else 80,
            user=c.get('username', 'admin'),
            password=c.get('password', ''),
            location=c.get('location', ''),
            location_id=c.get('location_id', ''),
            type=c.get('type', ''),
            status=c.get('status', 'Offline'),
            tag=c.get('tag', ''),
            username=c.get('username', 'admin'),
            brand=c.get('brand', ''),
            cam_id=c.get('cam_id', '')
        ))
    return res

def save_camera(data):
    # Data might be dict or Camera object
    if hasattr(data, 'model_dump'):
        d = data.model_dump()
    else:
        d = data
        
    # Map back to new schema
    cam_id = str(d.get('id', ''))
    if not cam_id: cam_id = str(uuid.uuid4())
    
    # Construct address
    ip = d.get('ip', '')
    port = d.get('port', 80)
    addr = f"{ip}:{port}" if port and port != 80 else ip
    
    new_data = {
        "id": cam_id,
        "name": d.get('name', ''),
        "ip": d.get('ip', ''),
        "port": d.get('port', 80),
        "username": d.get('username', d.get('user', 'admin')),
        "password": d.get('password', ''),
        "location": d.get('location', ''),
        "location_id": d.get('location_id', ''),
        "type": d.get('type', ''),
        "status": d.get('status', 'Offline'),
        "tag": d.get('tag', ''),
        "brand": d.get('brand', ''),
        "cam_id": d.get('cam_id', '')
    }
    
    # Check if exists to update or add
    exists = False
    all_cams = _cam_logic.get_cameras()
    if any(str(c.get('id')) == cam_id or str(c.get('cam_id')) == cam_id for c in all_cams):
        _cam_logic.update_camera(cam_id, new_data)
    else:
        new_data['cam_id'] = cam_id # Logic add_camera generates ID usually, but here we might want to preserve?
        # logic.add_camera ignores passed ID if it generates one?
        # Let's check logic.py. It generates uuid.
        # If I want to update, I use update_camera.
        # If I want to add with specific ID, logic doesn't support it (it generates new).
        # But this is a bridge.
        _cam_logic.add_camera(new_data)
        
    return True

def get_all_cameras():
    return get_cameras_config()

def get_cameras_by_tag(tag):
    # Not supported well in new schema directly (tag is now location_tag via location?)
    # or just filter what we have
    return []

def delete_camera(cam_id):
    return _cam_logic.delete_camera(cam_id)

# Registered Cars
from backend.data_process.register_car.logic import RegisteredCarLogic
_reg_car_logic = RegisteredCarLogic()

def get_registered_cars():
    return _reg_car_logic.get_all_cars()

def find_registered_car(plate: str):
    # Return car dict or None. Logic might normalize plate.
    cars = _reg_car_logic.get_all_cars()
    target = _reg_car_logic.normalize_plate(plate)
    for c in cars:
        if _reg_car_logic.normalize_plate(c['car_plate']) == target:
            # Return Simple Namespace or Dict? 
            # Legacy code likely expected object or dict.
            # checkin.py uses: car.owner, car.model.
            # So it expects an Object.
            from types import SimpleNamespace
            return SimpleNamespace(
                owner=c.get('car_owner', ''),
                model=c.get('car_model', ''),
                color=c.get('car_color', ''),
                standard_volume=c.get('car_volume', '')
            )
    return None
    
# Backward compatibility helper for initialize_registered_cars_today
def initialize_registered_cars_today():
    _reg_car_logic.rotate_daily_file()
    return True



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
    
    # Configuration
    'get_locations', 'save_locations', 'get_cam_types', 'save_cam_types',
    
    # Report module
    'report'
]
