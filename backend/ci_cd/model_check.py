"""
Model Check - Verify AI models are available

Checks for required model files and downloads if missing.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from backend.settings import settings

logger = logging.getLogger(__name__)

# Required models with their paths relative to models_dir
REQUIRED_MODELS = [
    {
        "name": "YOLO Car Detection",
        "path": "car_detect/yolo11n.pt",
        "size_min": 1_000_000,  # 1MB minimum
        "download_url": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt",
    },
]


def check_model_file(model_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a single model file exists and is valid.
    
    Args:
        model_info: Model information dictionary
        
    Returns:
        Check result dictionary
    """
    models_dir = settings.models_dir
    model_path = models_dir / model_info["path"]
    
    result = {
        "name": model_info["name"],
        "path": str(model_path),
        "exists": False,
        "valid": False,
        "size": 0,
    }
    
    if model_path.exists():
        result["exists"] = True
        result["size"] = model_path.stat().st_size
        
        # Check minimum size
        if result["size"] >= model_info.get("size_min", 0):
            result["valid"] = True
        else:
            logger.warning(f"Model {model_info['name']} is too small ({result['size']} bytes)")
    else:
        logger.warning(f"Model not found: {model_path}")
    
    return result


def download_model(model_info: Dict[str, Any]) -> bool:
    """
    Download a model file.
    
    Args:
        model_info: Model information with download_url
        
    Returns:
        True if downloaded successfully
    """
    download_url = model_info.get("download_url")
    if not download_url:
        logger.error(f"No download URL for {model_info['name']}")
        return False
    
    try:
        import httpx
        
        models_dir = settings.models_dir
        model_path = models_dir / model_info["path"]
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"  ⬇️  Downloading {model_info['name']}...")
        logger.info(f"Downloading {model_info['name']} from {download_url}...")
        
        with httpx.Client(timeout=600, follow_redirects=True) as client:
            with client.stream("GET", download_url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(model_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = (downloaded / total) * 100
                            print(f"\r  ⬇️  {model_info['name']}: {pct:.1f}%", end="", flush=True)
                print()  # New line
        
        print(f"  ✅ Downloaded {model_info['name']}")
        logger.info(f"Downloaded {model_info['name']} successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to download {model_info['name']}: {e}")
        logger.error(f"Failed to download {model_info['name']}: {e}")
        return False


def run_model_check(auto_download: bool = False) -> Dict[str, Any]:
    """
    Run model check and optionally download missing models.
    
    Args:
        auto_download: If True, attempt to download missing models
        
    Returns:
        Check result dictionary
    """
    results = []
    all_ok = True
    missing = []
    
    for model_info in REQUIRED_MODELS:
        result = check_model_file(model_info)
        results.append(result)
        
        if not result["valid"]:
            all_ok = False
            missing.append(model_info)
    
    if missing and auto_download:
        logger.info(f"Attempting to download {len(missing)} missing models...")
        for model_info in missing:
            if model_info.get("download_url"):
                success = download_model(model_info)
                if success:
                    # Re-check after download
                    result = check_model_file(model_info)
                    # Update in results
                    for i, r in enumerate(results):
                        if r["name"] == model_info["name"]:
                            results[i] = result
                            break
        
        # Re-evaluate overall status
        all_ok = all(r["valid"] for r in results)
        missing = [m for m in missing if not check_model_file(m)["valid"]]
    
    return {
        "check": "models",
        "success": all_ok,
        "models_dir": str(settings.models_dir),
        "missing": [m["name"] for m in missing],
        "details": results
    }
