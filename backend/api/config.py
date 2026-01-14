"""Configuration API endpoints (locations, types, registered cars)"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import data_process

config_router = APIRouter(prefix="/api/cameras", tags=["configuration"])

# Locations
@config_router.get("/locations")
async def get_locations():
    """Get all locations"""
    return data_process.get_locations()

@config_router.post("/locations")
async def save_locations(locations: List[Dict[str, Any]]):
    """Save locations"""
    print(f"Received locations: {locations}")
    
    # Save locations first to ensure IDs are generated if needed
    data_process.save_locations(locations)
    
    # Reload locations to get stable IDs/names map
    saved_locations = data_process.get_locations()
    
    # Map ID -> Name
    loc_id_to_name = {str(loc.get('id')): loc.get('name') for loc in saved_locations if loc.get('id')}
    # Map Name -> ID (for backfilling legacy cameras)
    loc_name_to_id = {loc.get('name'): str(loc.get('id')) for loc in saved_locations if loc.get('name')}
    
    # Sync Cameras
    all_cameras = data_process.get_cameras_config()
    updated = False
    
    for cam in all_cameras:
        cam_loc_id = str(cam.get('location_id', ''))
        cam_loc_name = cam.get('location', '')
        
        # Scenario 1: Camera has ID -> Sync Name from Location
        if cam_loc_id and cam_loc_id in loc_id_to_name:
            current_known_name = loc_id_to_name[cam_loc_id]
            if cam_loc_name != current_known_name:
                cam['location'] = current_known_name
                updated = True
                
        # Scenario 2: Camera has NO ID (or invalid) -> Backfill ID from Name
        elif cam_loc_name and cam_loc_name in loc_name_to_id:
            new_id = loc_name_to_id[cam_loc_name]
            if cam_loc_id != new_id:
                cam['location_id'] = new_id
                updated = True
                
    if updated:
        data_process.save_cameras_config(all_cameras)
        print("Synced cameras with new location configurations")

    return {"success": True}

# Camera Types
@config_router.get("/types")
async def get_cam_types():
    """Get all camera types"""
    return data_process.get_cam_types()

@config_router.post("/types")
async def save_cam_types(types: List[Dict[str, Any]]):
    """Save camera types"""
    print(f"Received types: {types}")
    data_process.save_cam_types(types)
    return {"success": True}

# Registered Cars
@config_router.get("/registered_cars")
async def get_registered_cars(date: Optional[str] = None):
    """Get registered cars for a specific date (format: dd-mm-yyyy)
    If no date provided, returns today's registered cars
    """
    return data_process.get_registered_cars(date=date)

@config_router.get("/registered_cars/dates")
async def get_registered_cars_dates():
    """Get list of all available registered cars dates"""
    try:
        dates = data_process.get_available_registered_cars_dates()
        return {"success": True, "dates": dates}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.post("/registered_cars")
async def save_registered_cars(cars: List[Dict[str, Any]], date: Optional[str] = None):
    """Save registered cars for a specific date (default: today)"""
    data_process.save_registered_cars(cars, date=date)
    return {"success": True}

@config_router.post("/registered_cars/import")
async def import_registered_cars(cars: List[Dict[str, Any]], date: Optional[str] = None):
    """Import registered cars with smart merge logic
    
    This endpoint:
    1. Compares new data with existing data for the date
    2. Keeps existing rows that match (same plate_number)
    3. Adds new rows
    4. Deletes rows that exist in old but not in new
    5. Updates created_at to current date
    
    Returns statistics about the import operation.
    """
    try:
        stats = data_process.import_registered_cars(cars, date=date)
        return {"success": True, **stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
