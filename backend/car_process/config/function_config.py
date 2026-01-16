"""
Function Configuration Registry

Central registry for all detection functions, their metadata, and mappings.
This file manages the discovery and instantiation of detection functions.
"""

from typing import Dict, List, Type, Any, Optional
import importlib

# Lazy import to avoid circular dependencies
def _get_function_classes():
    """Lazy import all function classes"""
    from backend.car_process.functions import (
        CarDetectionFunction,
        PlateDetectionFunction,
        ColorDetectionFunction,
        WheelDetectionFunction,
        BoxDetectionFunction,
        VolumeDetectionFunction
    )
    
    return {
        "car_detect": CarDetectionFunction,
        "plate_detect": PlateDetectionFunction,
        "color_detect": ColorDetectionFunction,
        "wheel_detect": WheelDetectionFunction,
        "box_detect": BoxDetectionFunction,
        "volume_detect": VolumeDetectionFunction,
    }


# Function Registry - Maps function_id to implementation class
FUNCTION_REGISTRY: Optional[Dict[str, Type]] = None

def get_function_registry() -> Dict[str, Type]:
    """Get function registry (lazy loaded)"""
    global FUNCTION_REGISTRY
    if FUNCTION_REGISTRY is None:
        FUNCTION_REGISTRY = _get_function_classes()
    return FUNCTION_REGISTRY


# Function Metadata Cache
_FUNCTION_METADATA_CACHE: Optional[Dict[str, Dict[str, Any]]] = None

def get_all_function_metadata() -> Dict[str, Dict[str, Any]]:
    """Get metadata for all functions (cached)"""
    global _FUNCTION_METADATA_CACHE
    
    if _FUNCTION_METADATA_CACHE is None:
        registry = get_function_registry()
        _FUNCTION_METADATA_CACHE = {}
        
        for func_id, func_class in registry.items():
            try:
                instance = func_class()
                _FUNCTION_METADATA_CACHE[func_id] = instance.get_metadata()
            except Exception as e:
                print(f"[FunctionConfig] Error loading metadata for {func_id}: {e}")
                _FUNCTION_METADATA_CACHE[func_id] = {
                    "id": func_id,
                    "name": func_id.replace('_', ' ').title(),
                    "error": str(e)
                }
    
    return _FUNCTION_METADATA_CACHE


def get_function(function_id: str):
    """
    Get function instance by ID.
    
    Args:
        function_id: Function identifier (e.g., "car_detect")
        
    Returns:
        Function instance
        
    Raises:
        ValueError: If function_id is unknown
    """
    registry = get_function_registry()
    
    if function_id not in registry:
        raise ValueError(
            f"Unknown function: {function_id}. "
            f"Available: {list(registry.keys())}"
        )
    
    return registry[function_id]()


def get_function_metadata(function_id: str) -> Dict[str, Any]:
    """
    Get metadata for a specific function.
    
    Args:
        function_id: Function identifier
        
    Returns:
        Metadata dictionary with keys: id, name, description, input_source, parallel_group
    """
    all_metadata = get_all_function_metadata()
    return all_metadata.get(function_id, {
        "id": function_id,
        "name": "Unknown",
        "error": "Function not found"
    })


def list_all_functions() -> List[Dict[str, Any]]:
    """
    List all available functions with their metadata.
    
    Returns:
        List of metadata dictionaries
    """
    metadata = get_all_function_metadata()
    return list(metadata.values())


def validate_function_list(function_ids: List[str]) -> tuple[bool, List[str]]:
    """
    Check if all function IDs are valid.
    
    Args:
        function_ids: List of function IDs to validate
        
    Returns:
        (is_valid, invalid_ids)
    """
    registry = get_function_registry()
    invalid = [fid for fid in function_ids if fid not in registry]
    return (len(invalid) == 0, invalid)


def get_functions_by_parallel_group(function_ids: List[str]) -> Dict[int, List[str]]:
    """
    Group function IDs by their parallel execution group.
    
    Args:
        function_ids: List of function IDs
        
    Returns:
        Dict mapping parallel_group number to list of function IDs
    """
    grouped = {}
    metadata = get_all_function_metadata()
    
    for func_id in function_ids:
        meta = metadata.get(func_id, {})
        group = meta.get('parallel_group', 1)
        
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(func_id)
    
    return grouped


def get_functions_requiring_source(source: str) -> List[str]:
    """
    Get all functions that require a specific input source.
    
    Args:
        source: Input source ('front_cam' or 'side_cam')
        
    Returns:
        List of function IDs requiring this source
    """
    metadata = get_all_function_metadata()
    return [
        func_id 
        for func_id, meta in metadata.items()
        if meta.get('input_source') == source
    ]


# Convenience exports
__all__ = [
    'get_function',
    'get_function_metadata',
    'list_all_functions',
    'validate_function_list',
    'get_functions_by_parallel_group',
    'get_functions_requiring_source',
    'get_function_registry',
    'get_all_function_metadata'
]
