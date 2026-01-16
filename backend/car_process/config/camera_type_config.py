"""
Predefined Camera Type Configurations

Common camera type presets that users can select from.
Users can also create custom types with their own function selections.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CameraTypePreset:
    """Predefined camera type configuration"""
    id: str
    name: str
    functions: List[str]
    description: str
    use_case: str
    is_custom: bool = False


# Predefined Camera Type Presets
CAMERA_TYPE_PRESETS: Dict[str, CameraTypePreset] = {
    "check_in_scanner": CameraTypePreset(
        id="check_in_scanner",
        name="Check-in Scanner",
        functions=["car_detect", "plate_detect", "color_detect", "wheel_detect"],
        description="Full vehicle analysis for entry gates",
        use_case="Entry gates, check-in stations"
    ),
    
    "check_out_scanner": CameraTypePreset(
        id="check_out_scanner",
        name="Check-out Scanner",
        functions=["car_detect", "plate_detect", "color_detect"],
        description="Quick verification for exit gates",
        use_case="Exit gates, check-out stations"
    ),
    
    "plate_only": CameraTypePreset(
        id="plate_only",
        name="Plate-Only Scanner",
        functions=["car_detect", "plate_detect"],
        description="Fast license plate recognition",
        use_case="Parking lots, toll gates, quick access"
    ),
    
    "volume_scanner": CameraTypePreset(
        id="volume_scanner",
        name="Volume Scanner",
        functions=["car_detect", "box_detect", "volume_detect", "plate_detect"],
        description="Material volume measurement for trucks",
        use_case="Loading zones, weigh stations"
    ),
    
    "basic_monitor": CameraTypePreset(
        id="basic_monitor",
        name="Basic Monitor",
        functions=["car_detect"],
        description="Simple vehicle detection and counting",
        use_case="Traffic monitoring, vehicle counting"
    ),
    
    "full_analysis": CameraTypePreset(
        id="full_analysis",
        name="Complete Vehicle Analysis",
        functions=["car_detect", "plate_detect", "color_detect", "wheel_detect", "box_detect"],
        description="Comprehensive vehicle information extraction",
        use_case="Inspection stations, detailed logging"
    ),
    
    # Special preset for custom configurations
    "custom": CameraTypePreset(
        id="custom",
        name="Custom Configuration",
        functions=[],  # User selects functions in UI
        description="Fully customizable function selection",
        use_case="Any custom use case",
        is_custom=True
    )
}


def get_preset(preset_id: str) -> CameraTypePreset:
    """
    Get a camera type preset by ID.
    
    Args:
        preset_id: Preset identifier
        
    Returns:
        CameraTypePreset, defaults to basic_monitor if not found
    """
    return CAMERA_TYPE_PRESETS.get(preset_id, CAMERA_TYPE_PRESETS["basic_monitor"])


def list_presets(include_custom: bool = True) -> List[CameraTypePreset]:
    """
    List all available presets.
    
    Args:
        include_custom: Whether to include the custom preset
        
    Returns:
        List of CameraTypePreset objects
    """
    presets = list(CAMERA_TYPE_PRESETS.values())
    
    if not include_custom:
        presets = [p for p in presets if not p.is_custom]
    
    return presets


def preset_to_camera_type_dict(preset: CameraTypePreset) -> Dict:
    """
    Convert preset to camera type dictionary format for database.
    
    Args:
        preset: CameraTypePreset object
        
    Returns:
        Dictionary with 'name' and 'functions' keys
    """
    return {
        "id": preset.id,
        "name": preset.name,
        "functions": ";".join(preset.functions),
        "description": preset.description
    }


def camera_type_from_preset_id(preset_id: str) -> Dict:
    """
    Get camera type dictionary from preset ID.
    
    Args:
        preset_id: Preset identifier
        
    Returns:
        Camera type dictionary
    """
    preset = get_preset(preset_id)
    return preset_to_camera_type_dict(preset)


def suggest_preset_for_location(location_tag: str) -> Optional[CameraTypePreset]:
    """
    Suggest a camera type preset based on location tag.
    
    Args:
        location_tag: Location tag (e.g., "Cổng vào")
        
    Returns:
        Recommended CameraTypePreset or None
    """
    # Map location tags to recommended presets
    location_to_preset = {
        "Cổng vào": "check_in_scanner",
        "Cổng ra": "check_out_scanner",
        "Đo thể tích": "volume_scanner",
        "Cơ bản": "basic_monitor"
    }
    
    preset_id = location_to_preset.get(location_tag)
    if preset_id:
        return get_preset(preset_id)
    
    return None


# Export all
__all__ = [
    'CameraTypePreset',
    'CAMERA_TYPE_PRESETS',
    'get_preset',
    'list_presets',
    'preset_to_camera_type_dict',
    'camera_type_from_preset_id',
    'suggest_preset_for_location'
]
