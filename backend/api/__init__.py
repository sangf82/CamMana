"""API Package - Modular REST endpoints

All API routers organized by feature.
Each module handles a specific domain of the application.
"""

from backend.api.config import config_router
from backend.api.schedule import schedule_router
from backend.api.checkin import checkin_router
from backend.api.checkout import checkout_router

__all__ = [
    'config_router',
    'schedule_router',
    'checkin_router',
    'checkout_router'
]
