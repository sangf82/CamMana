"""Configuration API endpoints (locations, types, registered cars)"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import data_process
from backend.schemas import Location, CameraType, RegisteredCar

config_router = APIRouter(prefix="/api/cameras", tags=["configuration"])

def sync_locations_to_cameras():
    """Helper to ensure all cameras have matching names and tags from locations.csv"""
    locations = data_process.get_locations()
    loc_map = {str(loc.id): loc for loc in locations if loc.id}
    loc_name_to_id = {loc.name: str(loc.id) for loc in locations if loc.name}
    
    all_cameras = data_process.get_cameras_config()
    updated = False
    
    for cam in all_cameras:
        cid = str(cam.location_id or '')
        cname = cam.location or ''
        
        if cid and cid in loc_map:
            loc = loc_map[cid]
            if cname != loc.name:
                cam.location = loc.name
                updated = True
            if cam.tag != loc.tag:
                cam.tag = loc.tag
                updated = True
        elif cname and cname in loc_name_to_id:
            nid = loc_name_to_id[cname]
            cam.location_id = nid
            cam.tag = loc_map[nid].tag
            updated = True
            
    if updated:
        data_process.save_cameras_config(all_cameras)
        print(f"[config_sync] Updated cameras to match location schema")

def sync_types_to_cameras():
    """Helper to ensure all cameras have matching type names from camtypes.csv"""
    pass

# Initial sync on module load
try:
    sync_locations_to_cameras()
    sync_types_to_cameras()
except Exception as e:
    print(f"[config_sync] Initial sync failed: {e}")

# Locations
@config_router.get("/locations", response_model=List[Location])
async def get_locations():
    """Get all locations"""
    return data_process.get_locations()

@config_router.post("/locations")
async def save_locations(locations: List[Location]):
    """Save locations and sync with cameras"""
    print(f"Received locations: {locations}")
    
    # Save locations first to ensure IDs are generated if needed
    data_process.save_locations(locations)
    
    # Reload locations
    saved_locations = data_process.get_locations()
    
    # Map ID -> {name, tag}
    loc_map = {str(loc.id): loc for loc in saved_locations if loc.id}
    loc_name_to_id = {loc.name: str(loc.id) for loc in saved_locations if loc.name}
    
    # Sync Cameras
    all_cameras = data_process.get_cameras_config()
    updated = False
    
    for cam in all_cameras:
        cam_loc_id = str(cam.location_id or '')
        cam_loc_name = cam.location or ''
        
        if cam_loc_id and cam_loc_id in loc_map:
            loc_data = loc_map[cam_loc_id]
            
            if cam_loc_name != loc_data.name:
                cam.location = loc_data.name
                updated = True
            
            if cam.tag != loc_data.tag:
                cam.tag = loc_data.tag
                updated = True
                
        elif cam_loc_name and cam_loc_name in loc_name_to_id:
            new_id = loc_name_to_id[cam_loc_name]
            loc_data = loc_map[new_id]
            
            if cam_loc_id != new_id:
                cam.location_id = new_id
                updated = True
            
            if cam.tag != loc_data.tag:
                cam.tag = loc_data.tag
                updated = True
                
        else:
            if cam_loc_id or cam_loc_name:
                cam.location = ""
                cam.location_id = ""
                updated = True
                
    if updated:
        data_process.save_cameras_config(all_cameras)
        print("Synced cameras with new location configurations")
    
    return {"success": True}

# Camera Types
@config_router.get("/types", response_model=List[CameraType])
async def get_cam_types():
    """Get all camera types"""
    return data_process.get_cam_types()

@config_router.post("/types")
async def save_cam_types(types: List[CameraType]):
    """Save camera types and sync changes if names updated"""
    print(f"Received types: {types}")
    
    old_types = data_process.get_cam_types()
    old_map = {str(t.id): t.name for t in old_types if t.id}
    
    data_process.save_cam_types(types)
    new_types = data_process.get_cam_types()
    
    all_cameras = data_process.get_cameras_config()
    updated = False
    
    for t in new_types:
        tid = str(t.id)
        new_name = t.name
        old_name = old_map.get(tid)
        
        if old_name and new_name and old_name != new_name:
            for cam in all_cameras:
                if cam.type == old_name:
                    cam.type = new_name
                    updated = True
                    
    if updated:
        data_process.save_cameras_config(all_cameras)
        print("Synced camera types after rename")
        
    return {"success": True}

# Registered Cars
@config_router.get("/registered_cars", response_model=List[RegisteredCar])
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
async def save_registered_cars(cars: List[RegisteredCar], date: Optional[str] = None):
    """Save registered cars for a specific date (default: today)"""
    data_process.save_registered_cars(cars, date=date)
    return {"success": True}

@config_router.post("/registered_cars/import")
async def import_registered_cars(cars: List[Dict[str, Any]], date: Optional[str] = None):
    """Import registered cars with smart merge logic"""
    try:
        stats = data_process.import_registered_cars(cars, date=date)
        return {"success": True, **stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

# Location Tags and Detection Config
@config_router.get("/locations/grouped")
async def get_cameras_grouped_by_tag():
    """Get cameras grouped by their location tags"""
    try:
        from backend.car_process.config import group_cameras_by_tag
        cameras = data_process.get_cameras_config()
        locations = data_process.get_locations()
        
        grouped = group_cameras_by_tag(cameras, locations)
        return {"success": True, "data": grouped}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/locations/tags/{tag}/config")
async def get_tag_detection_config(tag: str):
    """Get detection configuration for a specific location tag"""
    try:
        from backend.car_process.config import get_location_strategy
        config = get_location_strategy(tag)
        return {
            "success": True,
            "tag": tag,
            "description": config.description,
            "suggested_functions": config.suggested_functions,
            "capture_strategy": config.capture_strategy,
            "volume_tolerance": config.volume_tolerance
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/locations/tags/all/configs")
async def get_all_tag_configs():
    """Get detection configurations for all location tags"""
    try:
        from backend.car_process.config import LOCATION_STRATEGIES, LocationTag
        
        configs = {}
        for tag in LocationTag:
            if tag in LOCATION_STRATEGIES:
                config = LOCATION_STRATEGIES[tag]
                configs[tag.value] = {
                    "description": config.description,
                    "suggested_functions": config.suggested_functions,
                    "capture_strategy": config.capture_strategy,
                    "volume_tolerance": config.volume_tolerance
                }
        
        return {"success": True, "configs": configs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
