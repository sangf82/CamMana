"""Configuration API endpoints (Detection Configs)"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend import data_process
from backend.data_process.location.logic import LocationLogic

config_router = APIRouter(prefix="/api/cameras", tags=["configuration"])

# Location Tags and Detection Config
@config_router.get("/locations/grouped")
async def get_cameras_grouped_by_tag():
    """Get cameras grouped by their location tags"""
    try:
        from backend.workflow.config import group_cameras_by_tag
        cameras = data_process.get_cameras_config()
        # Use new LocationLogic
        location_logic = LocationLogic()
        
        locations_data = location_logic.get_locations()
        class SimpleLocation:
            def __init__(self, d):
                self.id = d.get('id')
                self.name = d.get('name')
                self.tag = d.get('tag')
        
        locations_objs = [SimpleLocation(d) for d in locations_data]
        
        grouped = group_cameras_by_tag(cameras, locations_objs)
        return {"success": True, "data": grouped}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/locations/tags/{tag}/config")
async def get_tag_detection_config(tag: str):
    """Get detection configuration for a specific location tag"""
    try:
        from backend.workflow.config import get_location_strategy
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

@config_router.get("/locations")
async def get_locations_alias():
    """Alias for locations list to match frontend expectations"""
    try:
        from backend.data_process.location.logic import LocationLogic
        return LocationLogic().get_locations()
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.post("/locations")
async def add_location_alias(loc: dict):
    """Alias for adding location to match frontend expectations"""
    try:
        from backend.data_process.location.logic import LocationLogic
        # Use logic directly
        return LocationLogic().add_location(loc)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

@config_router.get("/types")
async def get_types_alias():
    """Alias for camera types list to match frontend expectations"""
    try:
        from backend.data_process.camera_type.logic import CameraTypeLogic
        return CameraTypeLogic().get_types()
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/saved")
async def get_saved_cameras_alias():
    """Alias for saved cameras list to match frontend expectations"""
    try:
        from backend.camera.logic import CameraLogic
        return CameraLogic().get_cameras()
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/locations/tags/all/configs")
async def get_all_tag_configs():
    """Get detection configurations for all location tags"""
    try:
        from backend.workflow.config import LOCATION_STRATEGIES, LocationTag
        
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
