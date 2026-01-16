"""Shared models and camera state for API routers"""
from fastapi import HTTPException
from backend.schemas import (
    CameraConnectRequest, PTZMoveRequest,
    UpdateDetectionModeRequest, UpdateCameraTagRequest,
    Camera
)

# In-memory camera state (shared across routers)
cameras = {}

def get_camera_state(camera_id: str):
    """Get camera state from in-memory storage"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]
