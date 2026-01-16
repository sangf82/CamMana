"""
Core Processing Package

Orchestration and service management for detection workflows.
"""

from .orchestrator import DetectionOrchestrator, get_orchestrator
from .detection_service import DetectionService, get_detection_service
from .checkin_service import CheckInService, CheckInResult, get_checkin_service

__all__ = [
    'DetectionOrchestrator',
    'get_orchestrator',
    'DetectionService',
    'get_detection_service',
    'CheckInService',
    'CheckInResult',
    'get_checkin_service'
]

