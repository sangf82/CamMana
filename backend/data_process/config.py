"""Configuration data operations (locations, camera types)"""
from typing import List, Dict, Any
from backend.data_process._common import (
    LOCATION_HEADERS, TYPE_HEADERS, _generate_id, _read_csv, _write_csv, _get_config_csv_path, _init_csv_if_needed
)


def get_locations() -> List[Dict[str, str]]:
    """Get all locations"""
    path = _get_config_csv_path("locations.csv")
    _init_csv_if_needed(path, LOCATION_HEADERS)
    return _read_csv(path)


def save_locations(locations: List[Dict[str, str]]):
    """Save locations, ensuring all have IDs"""
    # Ensure IDs
    for loc in locations:
        if not loc.get('id'):
            loc['id'] = _generate_id()
    _write_csv(_get_config_csv_path("locations.csv"), LOCATION_HEADERS, locations)


def get_cam_types() -> List[Dict[str, str]]:
    """Get all camera types"""
    path = _get_config_csv_path("camtypes.csv")
    _init_csv_if_needed(path, TYPE_HEADERS)
    return _read_csv(path)


def save_cam_types(types: List[Dict[str, str]]):
    """Save camera types, ensuring all have IDs"""
    # Ensure IDs
    for t in types:
        if not t.get('id'):
            t['id'] = _generate_id()
    _write_csv(_get_config_csv_path("camtypes.csv"), TYPE_HEADERS, types)
