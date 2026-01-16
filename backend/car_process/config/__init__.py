"""
Configuration Package

Manages detection function configuration, location strategies, and camera type presets.
"""

from .function_config import (
    get_function,
    get_function_metadata,
    list_all_functions,
    validate_function_list,
    get_functions_by_parallel_group
)

from .location_config import (
    LocationTag,
    LocationStrategy,
    get_location_strategy,
    get_suggested_functions,
    get_capture_strategy,
    group_cameras_by_tag
)

from .camera_type_config import (
    CameraTypePreset,
    get_preset,
    list_presets,
    suggest_preset_for_location
)

__all__ = [
    # Function configuration
    'get_function',
    'get_function_metadata',
    'list_all_functions',
    'validate_function_list',
    'get_functions_by_parallel_group',
    
    # Location configuration
    'LocationTag',
    'LocationStrategy',
    'get_location_strategy',
    'get_suggested_functions',
    'get_capture_strategy',
    'group_cameras_by_tag',
    
    # Camera type presets
    'CameraTypePreset',
    'get_preset',
    'list_presets',
    'suggest_preset_for_location'
]
