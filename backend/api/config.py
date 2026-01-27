"""Configuration API endpoints (Detection Configs)"""
from backend import data_process
from backend.data_process.location.logic import LocationLogic
from backend.api.user import get_current_user
from backend.schemas import User as UserSchema
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from backend.data_process.sync.proxy import is_client_mode, proxy_get, proxy_post
import logging

logger = logging.getLogger(__name__)

config_router = APIRouter(prefix="/api/cameras", tags=["configuration"])

# Location Tags and Detection Config
@config_router.get("/locations/grouped")
async def get_cameras_grouped_by_tag(user: UserSchema = Depends(get_current_user)):
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
async def get_tag_detection_config(tag: str, user: UserSchema = Depends(get_current_user)):
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
async def get_locations_alias(user: UserSchema = Depends(get_current_user)):
    """Alias for locations list to match frontend expectations. Proxies to Master when in Client mode."""
    try:
        # Proxy to master if in client mode
        if is_client_mode():
            logger.info("Client mode: Fetching locations from master (alias)")
            result = await proxy_get("/api/cameras/locations")
            if result is not None:
                if user.role == "admin" or user.allowed_gates == "*":
                    return result
                allowed = [g.strip() for g in user.allowed_gates.split(',')]
                return [l for l in result if l.get('name') in allowed]
        
        from backend.data_process.location.logic import LocationLogic
        all_locs = LocationLogic().get_locations()
        
        if user.role == "admin" or user.allowed_gates == "*":
            return all_locs
            
        allowed = [g.strip() for g in user.allowed_gates.split(',')]
        return [l for l in all_locs if l['name'] in allowed]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.post("/locations")
async def add_location_alias(loc: dict, user: UserSchema = Depends(get_current_user)):
    """Alias for adding location to match frontend expectations. Proxies to Master when in Client mode."""
    if user.role != 'admin':
        return JSONResponse(status_code=403, content={"detail": "Permission denied"})
    try:
        # Proxy to master if in client mode
        if is_client_mode():
            logger.info("Client mode: Adding location via master (alias)")
            result = await proxy_post("/api/cameras/locations", loc)
            if result is not None:
                return result
            return JSONResponse(status_code=503, content={"detail": "Cannot connect to master node"})
        
        from backend.data_process.location.logic import LocationLogic
        # Use logic directly
        return LocationLogic().add_location(loc)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

@config_router.get("/types")
async def get_types_alias(user: UserSchema = Depends(get_current_user)):
    """Alias for camera types list to match frontend expectations. Proxies to Master when in Client mode."""
    try:
        # Proxy to master if in client mode
        if is_client_mode():
            logger.info("Client mode: Fetching camera types from master (alias)")
            result = await proxy_get("/api/cameras/types")
            if result is not None:
                return result
        
        from backend.data_process.camera_type.logic import CameraTypeLogic
        return CameraTypeLogic().get_types()
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/saved")
async def get_saved_cameras_alias(user: UserSchema = Depends(get_current_user)):
    """Alias for saved cameras list to match frontend expectations. Proxies to Master when in Client mode."""
    try:
        # Proxy to master if in client mode
        if is_client_mode():
            logger.info("Client mode: Fetching saved cameras from master (alias)")
            result = await proxy_get("/api/cameras/saved")
            if result is not None:
                return result
        
        from backend.camera.logic import CameraLogic
        return CameraLogic().get_cameras()
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@config_router.get("/locations/tags/all/configs")
async def get_all_tag_configs(user: UserSchema = Depends(get_current_user)):
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

