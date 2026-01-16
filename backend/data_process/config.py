"""Configuration data operations (locations, camera types)"""
from typing import List, Dict, Any
from backend.schemas import Location, CameraType
from backend.data_process._common import (
    LOCATION_HEADERS, TYPE_HEADERS, _generate_id, _read_csv, _write_csv, _get_config_csv_path, _init_csv_if_needed
)


def get_locations() -> List[Location]:
    """Get all locations"""
    path = _get_config_csv_path("locations.csv")
    _init_csv_if_needed(path, LOCATION_HEADERS)
    data = _read_csv(path)
    # Ensure default tag if missing? Logic was in api/config.py or helper?
    # Schema requires 'tag'. CSV matches schema?
    # Common CSV read returns Dict.
    # Convert to Location.
    # If CSV has missing fields, Pydantic might complain.
    # Let's add default fallback for tag if needed?
    # Location model: id, name, tag.
    cleaned_data = []
    for item in data:
        if 'tag' not in item or not item['tag']:
            item['tag'] = 'Cơ bản' # Default fallback
        cleaned_data.append(Location(**item))
    return cleaned_data


def save_locations(locations: List[Location]):
    """Save locations, ensuring all have IDs"""
    # Ensure IDs
    cleaned = []
    for loc in locations:
        if not loc.id:
            loc.id = _generate_id()
        if not loc.tag: # Default tag
             loc.tag = 'Cơ bản'
        cleaned.append(loc.model_dump())
            
    _write_csv(_get_config_csv_path("locations.csv"), LOCATION_HEADERS, cleaned)


def get_cam_types() -> List[CameraType]:
    """Get all camera types"""
    path = _get_config_csv_path("camtypes.csv")
    _init_csv_if_needed(path, TYPE_HEADERS)
    data = _read_csv(path)
    return [CameraType(**item) for item in data]


def save_cam_types(types: List[CameraType]):
    """Save camera types, ensuring all have IDs"""
    # Ensure IDs
    cleaned = []
    for t in types:
        if not t.id:
            t.id = _generate_id()
        cleaned.append(t.model_dump())
            
    _write_csv(_get_config_csv_path("camtypes.csv"), TYPE_HEADERS, cleaned)
