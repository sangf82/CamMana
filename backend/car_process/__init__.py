"""
Car Process Package

Unified detection system with modular functions, configuration,
and orchestration.

Structure:
- functions/: Detection functions (one per capability)
- config/: Configuration and strategy management
- core/: Orchestration and service layer

This package consolidates backend/detection and backend/detect_car
into a single, well-organized structure.
"""

# Core orchestrator
from .core import (
    get_orchestrator,
    DetectionOrchestrator,
    get_detection_service,
    DetectionService
)

# Configuration
from .config import (
    get_function,
    get_function_metadata,
    list_all_functions,
    LocationTag,
    get_location_strategy,
    get_preset,
    list_presets
)

# Functions (for direct access if needed)
from .functions import (
    CarDetectionFunction,
    PlateDetectionFunction,
    ColorDetectionFunction,
    WheelDetectionFunction,
    BoxDetectionFunction,
    VolumeDetectionFunction
)

# Backward compatibility aliases
from .functions import (
    CarDetector,
    detect_plate,
    detect_colors,
    count_wheels
)

__all__ = [
    # Core
    'get_orchestrator',
    'DetectionOrchestrator',
    'get_detection_service',
    'DetectionService',
    
    # Configuration
    'get_function',
    'get_function_metadata',
    'list_all_functions',
    'LocationTag',
    'get_location_strategy',
    'get_preset',
    'list_presets',
    
    # Functions
    'CarDetectionFunction',
    'PlateDetectionFunction',
    'ColorDetectionFunction',
    'WheelDetectionFunction',
    'BoxDetectionFunction',
    'VolumeDetectionFunction',
    
    # Backward compatibility
    'CarDetector',
    'detect_plate',
    'detect_colors',
    'count_wheels'
]
