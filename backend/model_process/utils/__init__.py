"""Model Process Utilities

Image processing utilities for AI model operations.
"""

from backend.model_process.utils.background import (
    BackgroundManager,
    background_manager,
    get_background_for_camera,
    capture_background_if_empty,
)

__all__ = [
    'BackgroundManager',
    'background_manager', 
    'get_background_for_camera',
    'capture_background_if_empty',
]
