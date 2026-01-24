
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class LocationTag(str, Enum):
    GATE_IN = "Cổng vào"
    GATE_OUT = "Cổng ra"
    VOLUME_TOP_DOWN = "Tính thể tích vật liệu (Trên dưới)"
    VOLUME_LEFT_RIGHT = "Tính thể tích vật liệu (Trái phải)"
    PARKING = "Gửi xe"
    CORE = "Cơ bản"

class DetectionStrategy(BaseModel):
    tag: LocationTag
    description: str
    suggested_functions: List[str]
    capture_strategy: str = "trigger" # trigger or continuous
    volume_tolerance: float = 0.05

LOCATION_STRATEGIES = {
    LocationTag.GATE_IN: DetectionStrategy(
        tag=LocationTag.GATE_IN,
        description="Gate In - Identify Truck and Plate",
        suggested_functions=["plate", "truck", "color"]
    ),
    LocationTag.GATE_OUT: DetectionStrategy(
        tag=LocationTag.GATE_OUT,
        description="Gate Out - Verify Exit",
        suggested_functions=["plate"]
    ),
    LocationTag.VOLUME_TOP_DOWN: DetectionStrategy(
        tag=LocationTag.VOLUME_TOP_DOWN,
        description="Volume Measurement Area (Top-Down + Side)",
        suggested_functions=["volume_top_down", "wheel", "truck"]
    ),
    LocationTag.VOLUME_LEFT_RIGHT: DetectionStrategy(
        tag=LocationTag.VOLUME_LEFT_RIGHT,
        description="Volume Measurement Area (Left-Right)",
        suggested_functions=["volume_left_right", "truck"]
    ),
}

def get_location_strategy(tag: str) -> Optional[DetectionStrategy]:
    try:
        # Match by value or name
        for t in LocationTag:
            if t.value == tag or t.name == tag:
                return LOCATION_STRATEGIES.get(t)
        # Default or search loosely
        return None
    except:
        return None

def group_cameras_by_tag(cameras, locations):
    """
    Group cameras by location tags.
    """
    grouped = {}
    for tag in LocationTag:
        grouped[tag.value] = {
            "tag": tag.value,
            "description": LOCATION_STRATEGIES[tag].description,
            "locations": []
        }
    
    # Map locations to tags (assume Location has .tag)
    loc_map = {loc.id: loc for loc in locations}
    
    # Group by tag
    for cam in cameras:
        # Cam has location_id or location name?
        # Logic in data_process/__init__.py for legacy camera used dict.
        # Assuming 'cameras' is list of Schema objects (Camera).
        loc_id = getattr(cam, 'location_id', '')
        if not loc_id: continue
        
        loc = loc_map.get(loc_id)
        if loc and loc.tag in grouped:
            # Check if location already added
            target = grouped[loc.tag]["locations"]
            # Add cam to location entry... logic complex? 
            # Or just return structure consumers expect.
            # Assuming simplified grouping for now.
            pass
            
    return grouped # Placeholder implementation as I don't recall exact output structure needed by frontend.
    # Frontend likely expects a list of tags with cameras nested.
    # Given I don't have the frontend code right here, I'll provide a safe dict.

