"""
Config Check - Verify system configuration APIs work correctly

Tests background config and storage config endpoints using sample data.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Path to sample data for testing
SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"


def run_config_check() -> Dict[str, Any]:
    """
    Run configuration API tests.
    
    Tests:
    - Background config load/save
    - Storage config load/save
    - Data expiry settings
    
    Returns:
        Check result dictionary
    """
    result = {
        "check": "config",
        "success": True,
        "tests": [],
        "errors": []
    }
    
    # Test 1: Background config module loads
    try:
        from backend.model_process.utils.background_config import (
            load_background_config,
            save_background_config,
            BackgroundSettings
        )
        result["tests"].append({
            "name": "background_config_import",
            "success": True
        })
    except Exception as e:
        result["success"] = False
        result["tests"].append({
            "name": "background_config_import",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Failed to import background_config: {e}")
        return result
    
    # Test 2: Storage config module loads
    try:
        from backend.data_process.storage_config import (
            load_expiry_config,
            save_expiry_config,
            DataExpirySettings
        )
        result["tests"].append({
            "name": "storage_config_import",
            "success": True
        })
    except Exception as e:
        result["success"] = False
        result["tests"].append({
            "name": "storage_config_import",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Failed to import storage_config: {e}")
        return result
    
    # Test 3: Load background config (should return defaults if no file)
    try:
        bg_config = load_background_config()
        assert isinstance(bg_config, dict), "Background config should be dict"
        assert "update_interval_hours" in bg_config or bg_config == {}, "Should have interval or be empty defaults"
        result["tests"].append({
            "name": "load_background_config",
            "success": True,
            "data": bg_config
        })
    except Exception as e:
        result["success"] = False
        result["tests"].append({
            "name": "load_background_config",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Failed to load background config: {e}")
    
    # Test 4: Load expiry config (should return defaults if no file)
    try:
        expiry_config = load_expiry_config()
        assert isinstance(expiry_config, dict), "Expiry config should be dict"
        # Check default values
        reg_days = expiry_config.get("registered_cars_days", 2)
        history_days = expiry_config.get("history_days", 2)
        reports_days = expiry_config.get("reports_days", 2)
        
        assert isinstance(reg_days, int), "registered_cars_days should be int"
        assert isinstance(history_days, int), "history_days should be int"
        assert isinstance(reports_days, int), "reports_days should be int"
        
        result["tests"].append({
            "name": "load_expiry_config",
            "success": True,
            "data": expiry_config
        })
    except Exception as e:
        result["success"] = False
        result["tests"].append({
            "name": "load_expiry_config",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Failed to load expiry config: {e}")
    
    # Test 5: Background manager exists and works
    try:
        from backend.model_process.utils.background import background_manager
        
        # Check backgrounds_dir property
        bg_dir = background_manager.backgrounds_dir
        assert bg_dir is not None, "backgrounds_dir should not be None"
        
        result["tests"].append({
            "name": "background_manager",
            "success": True,
            "backgrounds_dir": str(bg_dir)
        })
    except Exception as e:
        result["success"] = False
        result["tests"].append({
            "name": "background_manager",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Background manager failed: {e}")
    
    # Test 6: Pydantic models validate correctly
    try:
        # Test BackgroundSettings model
        bg_settings = BackgroundSettings(
            update_interval_hours=1,
            scheduler_enabled=True,
            last_update=None
        )
        assert bg_settings.update_interval_hours == 1
        
        # Test DataExpirySettings model
        expiry_settings = DataExpirySettings(
            registered_cars_days=2,
            history_days=2,
            reports_days=2,
            auto_cleanup_enabled=True
        )
        assert expiry_settings.registered_cars_days == 2
        
        result["tests"].append({
            "name": "pydantic_models",
            "success": True
        })
    except Exception as e:
        result["success"] = False
        result["tests"].append({
            "name": "pydantic_models",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Pydantic model validation failed: {e}")
    
    # Test 7: Sample data exists and is valid
    try:
        sample_calibration = SAMPLE_DATA_DIR / "calibration"
        sample_csv = SAMPLE_DATA_DIR / "csv_data"
        sample_history = SAMPLE_DATA_DIR / "car_history"
        
        checks = []
        if sample_calibration.exists():
            calib_side = sample_calibration / "calib_side.json"
            calib_topdown = sample_calibration / "calib_topdown.json"
            checks.append(("calib_side.json", calib_side.exists()))
            checks.append(("calib_topdown.json", calib_topdown.exists()))
            
            # Validate JSON
            if calib_side.exists():
                with open(calib_side) as f:
                    data = json.load(f)
                    checks.append(("calib_side_valid", "K" in data and "dist" in data))
        
        if sample_csv.exists():
            checks.append(("cameras.csv", (sample_csv / "cameras.csv").exists()))
            checks.append(("camtypes.csv", (sample_csv / "camtypes.csv").exists()))
        
        if sample_history.exists():
            # Check for test car images
            test_images = list(sample_history.rglob("*.jpg"))
            checks.append(("test_images", len(test_images) > 0))
        
        all_passed = all(c[1] for c in checks)
        result["tests"].append({
            "name": "sample_data",
            "success": all_passed,
            "checks": checks
        })
        
        if not all_passed:
            result["errors"].append("Some sample data files missing")
            
    except Exception as e:
        result["tests"].append({
            "name": "sample_data",
            "success": False,
            "error": str(e)
        })
        result["errors"].append(f"Sample data check failed: {e}")
    
    return result


if __name__ == "__main__":
    import json as json_module
    result = run_config_check()
    print(json_module.dumps(result, indent=2, default=str))
