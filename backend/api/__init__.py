"""API Package - Modular REST endpoints

All API routers organized by feature.
Each module handles a specific domain of the application.
"""

from backend.api.cameras import camera_router
from backend.api.config import config_router
from backend.api.detection import detection_router
from backend.api.history import history_router
from backend.api.schedule import schedule_router
from backend.api.checkin import checkin_router

__all__ = [
    'camera_router',
    'config_router',
    'detection_router',
    'history_router',
    'schedule_router',
    'checkin_router'
]
