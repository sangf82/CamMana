"""Camera configuration operations - CSV storage"""
from typing import Optional, List, Dict, Any, Union
from backend.schemas import Camera, CameraUpdate
from backend.data_process._common import (
    CAMERA_HEADERS, _generate_id, _read_csv, _write_csv, _get_config_csv_path, _init_csv_if_needed
)


def get_cameras_config() -> List[Camera]:
    """Get all camera configurations as Pydantic models"""
    path = _get_config_csv_path("cameras.csv")
    _init_csv_if_needed(path, CAMERA_HEADERS)
    data = _read_csv(path)
    return [Camera(**item) for item in data]


def save_cameras_config(cameras: List[Camera]):
    """Save cameras configuration list"""
    # Convert Pydantic models to dicts for CSV writing
    data = [cam.model_dump() for cam in cameras]
    _write_csv(_get_config_csv_path("cameras.csv"), CAMERA_HEADERS, data)


def save_camera(data: Union[Dict[str, Any], Camera]) -> bool:
    """Save or update a single camera configuration"""
    # Normalize input to Dict for processing logic (easier for merging)
    # OR better: use Pydantic model for internal logic
    
    if isinstance(data, Camera):
        cam_dict = data.model_dump()
    else:
        cam_dict = data
    
    cameras = get_cameras_config()
    existing_idx = next((i for i, c in enumerate(cameras) if str(c.id) == str(cam_dict.get('id'))), -1)
    
    if existing_idx >= 0:
        # UPDATE
        existing_cam = cameras[existing_idx]
        existing_dict = existing_cam.model_dump()
        
        # Merge logic
        update_keys = ['name', 'ip', 'port', 'user', 'password', 'tag', 'username', 
                      'profile_token', 'stream_uri', 'resolution_width', 'resolution_height',
                      'detection_mode', 'location_id']
        
        for key in update_keys:
            if key in cam_dict and cam_dict[key] is not None:
                existing_dict[key] = cam_dict[key]
                
        # Conditional updates
        for key in ['location', 'type', 'brand', 'cam_id']:
            if key in cam_dict and cam_dict[key]:
                existing_dict[key] = cam_dict[key]
                
        if cam_dict.get('status'):
            existing_dict['status'] = cam_dict['status']
            
        cameras[existing_idx] = Camera(**existing_dict)
    else:
        # INSERT
        # Ensure ID
        if not cam_dict.get('id'):
            # Should be handled by caller usually, but fallback
            import uuid
            cam_dict['id'] = str(uuid.uuid4())
            
        # Auto-generate cam_id
        if not cam_dict.get('cam_id'):
            max_num = 0
            for c in cameras:
                if c.cam_id and c.cam_id.startswith('CAM-'):
                    try:
                        num = int(c.cam_id.split('-')[1])
                        if num > max_num: max_num = num
                    except: pass
            cam_dict['cam_id'] = f"CAM-{max_num + 1:02d}"
            
        # Create new object (validates against schema)
        # Fill defaults handled by schema? Need to ensure required fields
        new_cam = Camera(**cam_dict)
        cameras.append(new_cam)
        
    save_cameras_config(cameras)
    return True


def get_camera(camera_id: str) -> Optional[Camera]:
    """Get camera configuration by ID"""
    cameras = get_cameras_config()
    return next((c for c in cameras if str(c.id) == camera_id), None)


def get_all_cameras() -> List[Camera]:
    """Get all cameras (alias for get_cameras_config)"""
    return get_cameras_config()


def get_cameras_by_tag(tag: str) -> List[Camera]:
    """Get cameras filtered by tag"""
    cameras = get_cameras_config()
    return [c for c in cameras if c.tag == tag]


def delete_camera(camera_id: str) -> bool:
    """Delete camera by ID"""
    cameras = get_cameras_config()
    new_cameras = [c for c in cameras if str(c.id) != camera_id]
    if len(cameras) != len(new_cameras):
        save_cameras_config(new_cameras)
        return True
    return False
