"""
Data Check - Verify data storage operations

Tests CSV CRUD operations and directory structure.
"""

import logging
import csv
import tempfile
from pathlib import Path
from typing import Dict, Any

from backend.settings import settings

logger = logging.getLogger(__name__)


def check_directory_structure() -> Dict[str, Any]:
    """
    Verify all required directories exist and are writable.
    
    Returns:
        Check result dictionary
    """
    directories = {
        "data_root": settings.data_root,
        "data_dir": settings.data_dir,
        "logs_dir": settings.logs_dir,
        "car_history_dir": settings.car_history_dir,
        "backgrounds_dir": settings.backgrounds_dir,
        "calibration_dir": settings.calibration_dir,
        "captured_img_dir": settings.captured_img_dir,
        "report_dir": settings.report_dir,
    }
    
    results = {}
    all_ok = True
    
    for name, path in directories.items():
        exists = path.exists()
        writable = False
        
        if exists:
            try:
                test_file = path / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
                writable = True
            except Exception:
                writable = False
        
        results[name] = {
            "path": str(path),
            "exists": exists,
            "writable": writable,
        }
        
        if not exists or not writable:
            all_ok = False
    
    return {
        "check": "directories",
        "success": all_ok,
        "details": results
    }


def check_csv_operations() -> Dict[str, Any]:
    """
    Test CSV read/write operations.
    
    Returns:
        Check result dictionary
    """
    tests = {
        "create": False,
        "read": False,
        "update": False,
        "delete": False,
    }
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_file = Path(f.name)
            
            # Create
            writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
            writer.writeheader()
            writer.writerow({"id": "1", "name": "test", "value": "100"})
            tests["create"] = True
        
        # Read
        with open(test_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if len(rows) == 1 and rows[0]["name"] == "test":
                tests["read"] = True
        
        # Update
        with open(test_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
            writer.writeheader()
            writer.writerow({"id": "1", "name": "updated", "value": "200"})
            tests["update"] = True
        
        # Delete
        test_file.unlink()
        if not test_file.exists():
            tests["delete"] = True
            
    except Exception as e:
        logger.error(f"CSV operations check failed: {e}")
    
    all_ok = all(tests.values())
    
    return {
        "check": "csv_operations",
        "success": all_ok,
        "details": tests
    }


def check_history_logic() -> Dict[str, Any]:
    """
    Test History logic operations.
    
    Returns:
        Check result dictionary
    """
    try:
        from backend.data_process.history.logic import HistoryLogic
        
        logic = HistoryLogic()
        
        # Get today's records (should not fail even if empty)
        records = logic.get_records()  # Uses today's date by default
        
        return {
            "check": "history_logic",
            "success": True,
            "record_count": len(records)
        }
        
    except Exception as e:
        logger.error(f"History logic check failed: {e}")
        return {
            "check": "history_logic",
            "success": False,
            "error": str(e)
        }


def run_data_check() -> Dict[str, Any]:
    """
    Run all data storage checks.
    
    Returns:
        Check result dictionary
    """
    dir_result = check_directory_structure()
    csv_result = check_csv_operations()
    history_result = check_history_logic()
    
    all_ok = dir_result["success"] and csv_result["success"] and history_result["success"]
    
    return {
        "check": "data",
        "success": all_ok,
        "details": {
            "directories": dir_result,
            "csv_operations": csv_result,
            "history_logic": history_result
        }
    }
