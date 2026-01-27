"""
Background Configuration API - Background image management endpoints

Provides endpoints for:
- View background images for volume_top_down cameras
- Manual capture trigger
- Update interval configuration
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system-config", tags=["Background Config"])


# ============================================================================
# MODELS
# ============================================================================

class BackgroundInfo(BaseModel):
    """Background image information."""
    camera_id: str
    camera_name: str
    filename: str
    path: str
    timestamp: Optional[str] = None
    size_kb: Optional[float] = None


class BackgroundSettings(BaseModel):
    """Background capture settings."""
    update_interval_hours: int = 1  # 1, 2, 4, or 24
    scheduler_enabled: bool = True
    last_update: Optional[str] = None


class VolumeTopDownCamera(BaseModel):
    """Camera with volume_top_down function."""
    id: str
    name: str
    location: Optional[str] = None
    has_background: bool = False


# ============================================================================
# CONFIG FILE HELPERS
# ============================================================================

CONFIG_FILE = settings.data_root / "system_config.json"


def load_background_config() -> dict:
    """Load background configuration from system config file."""
    import json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("background", {})
        except Exception as e:
            logger.error(f"Failed to load background config: {e}")
    return {
        "update_interval_hours": 1,
        "scheduler_enabled": True,
        "last_update": None
    }


def save_background_config(bg_config: dict) -> bool:
    """Save background configuration to system config file."""
    import json
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config
        full_config = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                full_config = json.load(f)
        
        # Update background section
        full_config["background"] = bg_config
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save background config: {e}")
        return False


def get_cameras_with_functions() -> list:
    """Get all cameras enriched with functions from camera types."""
    from backend.camera.logic import CameraLogic
    from backend.data_process.camera_type.logic import CameraTypeLogic
    
    camera_logic = CameraLogic()
    types_logic = CameraTypeLogic()
    
    cameras = camera_logic.get_cameras()
    types_map = {t['name']: t.get('functions', '') for t in types_logic.get_types()}
    
    # Enrich cameras with functions
    for cam in cameras:
        cam_type = cam.get('type', '')
        functions_str = types_map.get(cam_type, '')
        cam['functions'] = functions_str
    
    return cameras


# ============================================================================
# BACKGROUND ENDPOINTS
# ============================================================================

@router.get("/backgrounds", response_model=List[BackgroundInfo])
async def get_backgrounds():
    """
    Get list of all background images for volume_top_down cameras.
    Only shows backgrounds for cameras with volume_top_down function.
    """
    backgrounds = []
    bg_dir = settings.backgrounds_dir
    
    if not bg_dir.exists():
        return backgrounds
    
    # Get all cameras with functions enriched from camera types
    cameras = get_cameras_with_functions()
    
    # Build map: sanitized_name -> (cam_id, cam_name)
    topdown_cameras = {}
    for cam in cameras:
        functions_str = cam.get("functions", "")
        functions = functions_str.split(";") if isinstance(functions_str, str) else functions_str
        if "volume_top_down" in functions:
            cam_id = str(cam.get("id") or cam.get("cam_id") or "")
            cam_name = cam.get("name", f"Camera {cam_id}")
            # Sanitize name to match filename format
            safe_name = cam_name.replace(" ", "_").replace("/", "-")
            topdown_cameras[safe_name] = {"id": cam_id, "name": cam_name}
    
    # Find backgrounds with new format: background_{cam_name}_{timestamp}.jpg
    for bg_file in sorted(bg_dir.glob("background_*.jpg"), reverse=True):
        # Parse filename: background_{cam_name}_{dd-mm-yyyy_hh-mm-ss}.jpg
        stem = bg_file.stem  # background_Cam_3_28-01-2026_10-30-45
        parts = stem.split("_")
        if len(parts) >= 4:
            # Extract camera name (between "background_" and timestamp)
            # Format: background_CamName_dd-mm-yyyy_hh-mm-ss
            # Find where timestamp starts (dd-mm-yyyy pattern)
            timestamp_idx = -1
            for i, part in enumerate(parts):
                if len(part) == 10 and part[2] == '-' and part[5] == '-':
                    # This looks like dd-mm-yyyy
                    timestamp_idx = i
                    break
            
            if timestamp_idx > 1:
                cam_name_parts = parts[1:timestamp_idx]
                safe_name = "_".join(cam_name_parts)
                timestamp = "_".join(parts[timestamp_idx:])
                
                # Only include if camera has volume_top_down
                if safe_name in topdown_cameras:
                    cam_info = topdown_cameras[safe_name]
                    
                    # Check if we already have a newer bg for this camera
                    existing = next((b for b in backgrounds if b.camera_id == cam_info["id"]), None)
                    if existing:
                        continue  # Skip older backgrounds
                    
                    try:
                        stat = bg_file.stat()
                        size_kb = round(stat.st_size / 1024, 2)
                    except:
                        size_kb = None
                    
                    backgrounds.append(BackgroundInfo(
                        camera_id=cam_info["id"],
                        camera_name=cam_info["name"],
                        filename=bg_file.name,
                        path=f"/api/system-config/backgrounds/{bg_file.name}",
                        timestamp=timestamp,
                        size_kb=size_kb
                    ))
    
    return backgrounds


@router.get("/backgrounds/cameras", response_model=List[VolumeTopDownCamera])
async def get_volume_topdown_cameras():
    """Get list of all cameras with volume_top_down function."""
    # Get all cameras with functions enriched from camera types
    cameras = get_cameras_with_functions()
    
    # Check which cameras have backgrounds (new format: background_{cam_name}_*.jpg)
    bg_dir = settings.backgrounds_dir
    existing_bg_names = set()
    if bg_dir.exists():
        for bg_file in bg_dir.glob("background_*.jpg"):
            # Parse to extract camera name
            stem = bg_file.stem
            parts = stem.split("_")
            if len(parts) >= 4:
                # Find timestamp start
                for i, part in enumerate(parts):
                    if len(part) == 10 and part[2] == '-' and part[5] == '-':
                        cam_name = "_".join(parts[1:i])
                        existing_bg_names.add(cam_name)
                        break
    
    result = []
    for cam in cameras:
        functions_str = cam.get("functions", "")
        functions = functions_str.split(";") if isinstance(functions_str, str) else functions_str
        if "volume_top_down" in functions:
            cam_id = str(cam.get("id") or cam.get("cam_id") or "")
            cam_name = cam.get("name", f"Camera {cam_id}")
            safe_name = cam_name.replace(" ", "_").replace("/", "-")
            result.append(VolumeTopDownCamera(
                id=cam_id,
                name=cam_name,
                location=cam.get("location"),
                has_background=safe_name in existing_bg_names
            ))
    
    return result


@router.get("/backgrounds/{filename}")
async def get_background_image(filename: str):
    """Serve a background image file."""
    bg_path = settings.backgrounds_dir / filename
    if not bg_path.exists():
        raise HTTPException(status_code=404, detail="Background not found")
    
    return FileResponse(bg_path, media_type="image/jpeg")


@router.get("/backgrounds/settings", response_model=BackgroundSettings)
async def get_background_settings():
    """Get background capture settings."""
    bg_config = load_background_config()
    return BackgroundSettings(
        update_interval_hours=bg_config.get("update_interval_hours", 1),
        scheduler_enabled=bg_config.get("scheduler_enabled", True),
        last_update=bg_config.get("last_update")
    )


@router.post("/backgrounds/settings")
async def update_background_settings(
    update_interval_hours: int = Query(1, description="Update interval: 1, 2, 4, or 24 hours"),
    scheduler_enabled: bool = Query(True, description="Enable auto scheduler")
):
    """Update background capture settings."""
    # Validate interval
    valid_intervals = [1, 2, 4, 24]
    if update_interval_hours not in valid_intervals:
        raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {valid_intervals}")
    
    bg_config = load_background_config()
    bg_config["update_interval_hours"] = update_interval_hours
    bg_config["scheduler_enabled"] = scheduler_enabled
    
    if not save_background_config(bg_config):
        raise HTTPException(status_code=500, detail="Failed to save config")
    
    # Restart scheduler with new interval
    from backend.model_process.utils.background import background_manager
    background_manager.update_scheduler_interval(update_interval_hours)
    
    return {"success": True, "message": f"Settings updated. Interval: {update_interval_hours}h"}


@router.post("/backgrounds/capture")
async def manual_capture_backgrounds():
    """Manually trigger background capture for all volume_top_down cameras."""
    from backend.model_process.utils.background import background_manager
    
    try:
        result = await background_manager.update_all_backgrounds()
        
        # Update last_update timestamp
        bg_config = load_background_config()
        bg_config["last_update"] = datetime.now().isoformat()
        save_background_config(bg_config)
        
        return {
            "success": True,
            "checked": result.get("checked", 0),
            "updated": result.get("updated", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", 0)
        }
    except Exception as e:
        logger.error(f"Manual background capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
