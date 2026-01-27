"""
Camera State Management

Centralized in-memory state for active camera connections.
This replaces the old _shared.py in api/ folder.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException


# In-memory camera state (shared across modules)
cameras: Dict[str, Dict[str, Any]] = {}


def get_camera_state(camera_id: str) -> Dict[str, Any]:
    """Get camera state from in-memory storage."""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]


def set_camera_state(camera_id: str, state: Dict[str, Any]) -> None:
    """Set camera state in in-memory storage."""
    cameras[camera_id] = state


def remove_camera_state(camera_id: str) -> bool:
    """Remove camera state from in-memory storage."""
    if camera_id in cameras:
        del cameras[camera_id]
        return True
    return False


def get_all_camera_states() -> Dict[str, Dict[str, Any]]:
    """Get all camera states."""
    return cameras
