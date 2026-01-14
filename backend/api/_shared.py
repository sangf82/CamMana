"""Shared models and camera state for API routers"""
import uuid
from typing import Optional, Union, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel

# Request Models
class CameraConnectRequest(BaseModel):
    ip: str
    port: int = 8899
    user: str = "admin"
    password: str = ""
    name: str = "Camera"
    tag: Optional[str] = None
    detection_mode: str = "disabled"

class PTZMoveRequest(BaseModel):
    speed: float = 0.5

class UpdateDetectionModeRequest(BaseModel):
    detection_mode: str

class UpdateCameraTagRequest(BaseModel):
    tag: Optional[str]

class ConfigItem(BaseModel):
    id: Union[int, str]
    name: str

# In-memory camera state (shared across routers)
cameras = {}

def get_camera_state(camera_id: str):
    """Get camera state from in-memory storage"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]
