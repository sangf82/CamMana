"""Camera configuration operations - CSV storage"""
from typing import Optional, List, Dict, Any
from backend.data_process._common import (
    CAMERA_HEADERS, _generate_id, _read_csv, _write_csv, _get_config_csv_path
)


def get_cameras_config() -> List[Dict[str, Any]]:
    """Get all camera configurations"""
    path = _get_config_csv_path("cameras.csv")
    from backend.data_process._common import _init_csv_if_needed
    _init_csv_if_needed(path, CAMERA_HEADERS)
    return _read_csv(path)


def save_cameras_config(cameras: List[Dict[str, Any]]):
    """Save cameras configuration list"""
    _write_csv(_get_config_csv_path("cameras.csv"), CAMERA_HEADERS, cameras)


def save_camera(data: Dict[str, Any]) -> bool:
    """Save or update a single camera configuration"""
    cameras = get_cameras_config()
    
    # Check if update or insert
    existing_idx = next((i for i, c in enumerate(cameras) if str(c['id']) == str(data['id'])), -1)
    
    if existing_idx >= 0:
        # UPDATE: Preserve existing fields, only update what's provided
        existing_cam = cameras[existing_idx]
        
        # Only update fields that are explicitly provided and not empty
        for key in ['name', 'ip', 'port', 'user', 'password', 'tag', 'username', 
                    'profile_token', 'stream_uri', 'resolution_width', 'resolution_height',
                    'detection_mode', 'location_id']:
            if key in data and data[key] is not None:
                existing_cam[key] = data[key]
        
        # These fields should NEVER be overwritten with empty values
        # Only update if the new value is non-empty
        for key in ['location', 'type', 'brand', 'cam_id']:
            if key in data and data[key]:
                existing_cam[key] = data[key]
        
        # Update status only if connecting (Online)
        if data.get('status'):
            existing_cam['status'] = data['status']
        
        cameras[existing_idx] = existing_cam
    else:
        # INSERT: Create new camera with defaults
        new_cam = {
            'id': data.get('id'),
            'name': data.get('name', 'Camera'),
            'ip': data.get('ip'),
            'port': data.get('port', 8899),
            'user': data.get('username', 'admin'),
            'password': data.get('password', ''),
            'location': data.get('location', ''),
            'location_id': data.get('location_id', ''),
            'type': data.get('type', ''),
            'status': data.get('status', 'Offline'),
            'tag': data.get('tag'),
            'username': data.get('username', 'admin'),
            'brand': data.get('brand', ''),
            'cam_id': data.get('cam_id', '')
        }
        
        # Auto-generate cam_id if missing
        if not new_cam['cam_id']:
            max_num = 0
            for c in cameras:
                cid = c.get('cam_id', '')
                if cid.startswith('CAM-'):
                    try:
                        num = int(cid.split('-')[1])
                        if num > max_num: max_num = num
                    except: pass
            new_cam['cam_id'] = f"CAM-{max_num + 1:02d}"
        
        cameras.append(new_cam)
        
    save_cameras_config(cameras)
    return True


def get_camera(camera_id: str) -> Optional[Dict[str, Any]]:
    """Get camera configuration by ID"""
    cameras = get_cameras_config()
    return next((c for c in cameras if c['id'] == camera_id), None)


def get_all_cameras() -> List[Dict[str, Any]]:
    """Get all cameras (alias for get_cameras_config)"""
    return get_cameras_config()


def get_cameras_by_tag(tag: str) -> List[Dict[str, Any]]:
    """Get cameras filtered by tag"""
    cameras = get_cameras_config()
    return [c for c in cameras if c.get('tag') == tag]


def delete_camera(camera_id: str) -> bool:
    """Delete camera by ID"""
    cameras = get_cameras_config()
    new_cameras = [c for c in cameras if c['id'] != camera_id]
    if len(cameras) != len(new_cameras):
        save_cameras_config(new_cameras)
        return True
    return False
