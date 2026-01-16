"""
Location-Based Detection Strategies

Defines detection strategies for different location tags.
Migrated from backend/detection/detection_config.py
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class LocationTag(str, Enum):
    """Predefined location tags for camera grouping"""
    CHECK_IN = "Cổng vào"
    CHECK_OUT = "Cổng ra"
    VOLUME_ESTIMATE = "Đo thể tích"
    GENERAL = "Cơ bản"


@dataclass
class LocationStrategy:
    """Detection strategy for a location type"""
    tag: LocationTag
    description: str
    suggested_functions: List[str]  # Suggested function IDs
    capture_strategy: str
    volume_tolerance: Optional[float] = None


# Location-based detection strategies
LOCATION_STRATEGIES: Dict[LocationTag, LocationStrategy] = {
    LocationTag.CHECK_IN: LocationStrategy(
        tag=LocationTag.CHECK_IN,
        description="Entry gate - detect incoming vehicles",
        suggested_functions=["car_detect", "plate_detect", "color_detect", "wheel_detect"],
        capture_strategy="continuous"
    ),
    
    LocationTag.CHECK_OUT: LocationStrategy(
        tag=LocationTag.CHECK_OUT,
        description="Exit gate - detect outgoing vehicles",
        suggested_functions=["car_detect", "plate_detect", "color_detect"],
        capture_strategy="verify_and_match"
    ),
    
    LocationTag.VOLUME_ESTIMATE: LocationStrategy(
        tag=LocationTag.VOLUME_ESTIMATE,
        description="Volume measurement station - calculate truck load volume",
        suggested_functions=["car_detect", "box_detect", "volume_detect", "plate_detect"],
        capture_strategy="multi_angle",
        volume_tolerance=0.05
    ),
    
    LocationTag.GENERAL: LocationStrategy(
        tag=LocationTag.GENERAL,
        description="General purpose camera location",
        suggested_functions=["car_detect", "plate_detect"],
        capture_strategy="on_motion"
    )
}


def get_location_strategy(tag: str) -> LocationStrategy:
    """
    Get detection strategy for a location tag.
    
    Args:
        tag: Location tag string (e.g., "Cổng vào")
        
    Returns:
        LocationStrategy for the tag, defaults to GENERAL if not found
    """
    try:
        location_tag = LocationTag(tag)
        return LOCATION_STRATEGIES[location_tag]
    except (ValueError, KeyError):
        return LOCATION_STRATEGIES[LocationTag.GENERAL]


def get_suggested_functions(location_tag: str) -> List[str]:
    """
    Get suggested function list for a location tag.
    
    Args:
        location_tag: Location tag string
        
    Returns:
        List of suggested function IDs
    """
    strategy = get_location_strategy(location_tag)
    return strategy.suggested_functions


def get_capture_strategy(location_tag: str) -> str:
    """
    Get capture strategy for a location tag.
    
    Args:
        location_tag: Location tag string
        
    Returns:
        Capture strategy name
    """
    strategy = get_location_strategy(location_tag)
    return strategy.capture_strategy


def get_volume_tolerance(location_tag: str) -> Optional[float]:
    """
    Get volume tolerance for volume-estimate locations.
    
    Args:
        location_tag: Location tag string
        
    Returns:
        Volume tolerance as decimal (e.g., 0.05 for ±5%) or None
    """
    strategy = get_location_strategy(location_tag)
    return strategy.volume_tolerance


def group_cameras_by_tag(cameras: List, locations: List) -> Dict[str, List]:
    """
    Group cameras by their location tags.
    
    Args:
        cameras: List of camera objects or dicts
        locations: List of location objects or dicts
        
    Returns:
        Dictionary mapping location tags to lists of cameras
    """
    # Helper to get attribute or key
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    # Build location_id -> tag mapping
    loc_tag_map = {
        str(get_val(loc, 'id')): get_val(loc, 'tag', LocationTag.GENERAL.value) 
        for loc in locations
    }
    
    # Group cameras by tag
    grouped = {}
    for camera in cameras:
        loc_id = str(get_val(camera, 'location_id', ''))
        tag = loc_tag_map.get(loc_id, LocationTag.GENERAL.value)
        
        if tag not in grouped:
            grouped[tag] = []
        grouped[tag].append(camera)
    
    return grouped


# Export all
__all__ = [
    'LocationTag',
    'LocationStrategy',
    'LOCATION_STRATEGIES',
    'get_location_strategy',
    'get_suggested_functions',
    'get_capture_strategy',
    'get_volume_tolerance',
    'group_cameras_by_tag'
]
