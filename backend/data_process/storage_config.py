"""
System Configuration API - Data Expiry Settings

Provides endpoints for:
- Data expiry settings (register car, history, report cleanup)
- Manual cleanup trigger
"""

import logging
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system-config", tags=["System Config"])


# ============================================================================
# MODELS
# ============================================================================

class DataExpirySettings(BaseModel):
    """Data expiry settings."""
    registered_cars_days: int = 2
    history_days: int = 2
    reports_days: int = 2
    car_history_days: int = 2
    auto_cleanup_enabled: bool = True


# ============================================================================
# CONFIG FILE HELPERS
# ============================================================================

CONFIG_FILE = settings.data_root / "system_config.json"


def load_system_config() -> dict:
    """Load system configuration from file."""
    import json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load system config: {e}")
    return {
        "background": {
            "update_interval_hours": 1,
            "scheduler_enabled": True,
            "last_update": None
        },
        "data_expiry": {
            "registered_cars_days": 2,
            "history_days": 2,
            "reports_days": 2,
            "auto_cleanup_enabled": True
        }
    }


def save_system_config(config: dict) -> bool:
    """Save system configuration to file."""
    import json
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save system config: {e}")
        return False


def load_expiry_config() -> dict:
    """Load data expiry configuration."""
    config = load_system_config()
    return config.get("data_expiry", {
        "registered_cars_days": 2,
        "history_days": 2,
        "reports_days": 2,
        "auto_cleanup_enabled": True
    })


def save_expiry_config(expiry_config: dict) -> bool:
    """Save data expiry configuration."""
    config = load_system_config()
    config["data_expiry"] = expiry_config
    return save_system_config(config)


# ============================================================================
# DATA EXPIRY ENDPOINTS
# ============================================================================

@router.get("/data-expiry", response_model=DataExpirySettings)
async def get_data_expiry_settings():
    """Get data expiry settings."""
    expiry_config = load_expiry_config()
    return DataExpirySettings(
        registered_cars_days=expiry_config.get("registered_cars_days", 2),
        history_days=expiry_config.get("history_days", 2),
        reports_days=expiry_config.get("reports_days", 2),
        car_history_days=expiry_config.get("car_history_days", 2),
        auto_cleanup_enabled=expiry_config.get("auto_cleanup_enabled", True)
    )


@router.post("/data-expiry")
async def update_data_expiry_settings(
    registered_cars_days: int = Query(2, ge=1, le=365, description="Days to keep registered cars data"),
    history_days: int = Query(2, ge=1, le=365, description="Days to keep history data"),
    reports_days: int = Query(2, ge=1, le=365, description="Days to keep reports"),
    car_history_days: int = Query(2, ge=1, le=365, description="Days to keep car history images"),
    auto_cleanup_enabled: bool = Query(True, description="Enable auto cleanup")
):
    """Update data expiry settings."""
    expiry_config = {
        "registered_cars_days": registered_cars_days,
        "history_days": history_days,
        "reports_days": reports_days,
        "car_history_days": car_history_days,
        "auto_cleanup_enabled": auto_cleanup_enabled
    }
    
    if not save_expiry_config(expiry_config):
        raise HTTPException(status_code=500, detail="Failed to save config")
    
    return {"success": True, "message": "Data expiry settings updated"}


@router.post("/data-expiry/cleanup")
async def manual_cleanup_expired_data():
    """Manually trigger cleanup of expired data."""
    expiry_config = load_expiry_config()
    
    result = {
        "registered_cars_deleted": 0,
        "history_deleted": 0,
        "reports_deleted": 0,
        "car_history_folders_deleted": 0
    }
    
    try:
        today = datetime.now().date()
        
        # Clean up registered_cars CSV files
        reg_days = expiry_config.get("registered_cars_days", 2)
        for csv_file in settings.data_dir.glob("registered_cars_*.csv"):
            try:
                date_str = csv_file.stem.split("_")[-1]  # registered_cars_DD-MM-YYYY
                file_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                if (today - file_date).days >= reg_days:
                    csv_file.unlink()
                    result["registered_cars_deleted"] += 1
            except Exception:
                pass
        
        # Clean up history CSV files
        history_days = expiry_config.get("history_days", 2)
        for csv_file in settings.data_dir.glob("history_*.csv"):
            try:
                date_str = csv_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                if (today - file_date).days >= history_days:
                    csv_file.unlink()
                    result["history_deleted"] += 1
            except Exception:
                pass
        
        # Clean up report JSON files
        reports_days = expiry_config.get("reports_days", 2)
        for report_file in settings.report_dir.glob("report_*.json"):
            try:
                date_str = report_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                if (today - file_date).days >= reports_days:
                    report_file.unlink()
                    result["reports_deleted"] += 1
            except Exception:
                pass
        
        # Clean up car_history folders
        car_history_days = expiry_config.get("car_history_days", 2)
        for date_folder in settings.car_history_dir.iterdir():
            if date_folder.is_dir():
                try:
                    folder_date = datetime.strptime(date_folder.name, "%d-%m-%Y").date()
                    if (today - folder_date).days >= car_history_days:
                        shutil.rmtree(date_folder)
                        result["car_history_folders_deleted"] += 1
                except Exception:
                    pass
        
        return {"success": True, **result}
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
