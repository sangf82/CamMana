"""
Detection Functions Package

Each file contains a single detection function with standardized interface.
"""

from .car_detection import CarDetectionFunction, CarDetector
from .plate_detection import PlateDetectionFunction, detect_plate
from .color_detection import ColorDetectionFunction, detect_colors
from .wheel_detection import WheelDetectionFunction, count_wheels
from .box_detection import BoxDetectionFunction
from .volume_detection import VolumeDetectionFunction

__all__ = [
    # New class-based interface
    'CarDetectionFunction',
    'PlateDetectionFunction',
    'ColorDetectionFunction',
    'WheelDetectionFunction',
    'BoxDetectionFunction',
    'VolumeDetectionFunction',
    
    # Backward compatibility aliases
    'CarDetector',
    'detect_plate',
    'detect_colors',
    'count_wheels',
]
