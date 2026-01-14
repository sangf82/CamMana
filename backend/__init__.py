"""Backend Package - Camera Management System"""

# Import detection service
from backend.detect_car import DetectionService, get_detection_service

__all__ = ['DetectionService', 'get_detection_service']
