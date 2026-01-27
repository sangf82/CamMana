"""
API Check - Verify external API connectivity

Tests connections to external services like the AI API.
Tests all endpoints: health, colors, alpr, wheels, volume.
Only HTTP 200 status code is considered a success.
"""

import logging
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

from backend.settings import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.ai_api_url

# External APIs to check
EXTERNAL_APIS = [
    {
        "name": "Health Check",
        "endpoint": "/health",
        "method": "GET",
        "timeout": 15.0,
        "required": True,
    },
    {
        "name": "Color Detection",
        "endpoint": "/detect_colors",
        "method": "POST",
        "timeout": 30.0,
        "required": False,
        "image_key": "file",
    },
    {
        "name": "License Plate (ALPR)",
        "endpoint": "/alpr",
        "method": "POST",
        "timeout": 30.0,
        "required": False,
        "image_key": "file",
    },
    {
        "name": "Wheel Count",
        "endpoint": "/count_wheels",
        "method": "POST",
        "timeout": 30.0,
        "required": False,
        "image_key": "file",
    },
    {
        "name": "Volume Estimation",
        "endpoint": "/estimate_volume",
        "method": "POST",
        "timeout": 60.0,
        "required": False,
        "special": "volume",
    },
]


def find_test_image() -> Optional[Path]:
    """Find a test image from car history for API testing."""
    history_dir = settings.car_history_dir
    if not history_dir.exists():
        return None
    
    # Look for any jpg image in car history
    for date_folder in sorted(history_dir.iterdir(), reverse=True):
        if date_folder.is_dir():
            for car_folder in date_folder.iterdir():
                if car_folder.is_dir():
                    for img in car_folder.glob("*.jpg"):
                        return img
    return None


def get_volume_test_files() -> Optional[Dict[str, Path]]:
    """Get files needed for volume API testing."""
    calib_dir = settings.calibration_dir
    bg_dir = settings.backgrounds_dir
    
    calib_side = calib_dir / "calib_side.json"
    calib_topdown = calib_dir / "calib_topdown.json"
    
    if not calib_side.exists() or not calib_topdown.exists():
        return None
    
    # Find a side view image
    side_image = find_test_image()
    if not side_image:
        return None
    
    # For volume, we need bg and fg images from topdown
    # If no background exists, we can't test volume
    bg_images = list(bg_dir.glob("*.jpg")) + list(bg_dir.glob("*.png"))
    if not bg_images:
        # Use the same test image as placeholder (API will still respond)
        bg_image = side_image
    else:
        bg_image = bg_images[0]
    
    return {
        "image": side_image,
        "calib_side": calib_side,
        "img_bg": bg_image,
        "img_fg": side_image,  # Use side image as fg for testing
        "calib_topdown": calib_topdown,
    }


async def check_api_endpoint(api_info: Dict[str, Any], test_image: Optional[Path]) -> Dict[str, Any]:
    """
    Check connectivity to a single API endpoint.
    Only HTTP 200 is accepted as success.
    
    Args:
        api_info: API information dictionary
        test_image: Path to test image for POST requests
        
    Returns:
        Check result dictionary
    """
    url = f"{BASE_URL}{api_info['endpoint']}"
    result = {
        "name": api_info["name"],
        "url": url,
        "reachable": False,
        "response_time_ms": None,
        "status_code": None,
        "response_data": None,
        "error": None,
    }
    
    try:
        start = time.time()
        timeout = api_info.get("timeout", 15.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            if api_info["method"] == "GET":
                response = await client.get(url)
            elif api_info["method"] == "POST":
                # Handle special volume endpoint
                if api_info.get("special") == "volume":
                    volume_files = get_volume_test_files()
                    if not volume_files:
                        result["error"] = "Missing calibration or test files for volume test"
                        return result
                    
                    files = {
                        "image": ("side.jpg", open(volume_files["image"], "rb"), "image/jpeg"),
                        "calib_side": ("calib_side.json", open(volume_files["calib_side"], "rb"), "application/json"),
                        "img_bg": ("bg.jpg", open(volume_files["img_bg"], "rb"), "image/jpeg"),
                        "img_fg": ("fg.jpg", open(volume_files["img_fg"], "rb"), "image/jpeg"),
                        "calib_topdown": ("calib_topdown.json", open(volume_files["calib_topdown"], "rb"), "application/json"),
                    }
                    response = await client.post(url, files=files)
                    # Close file handles
                    for f in files.values():
                        if hasattr(f[1], 'close'):
                            f[1].close()
                else:
                    # Standard image POST
                    if not test_image or not test_image.exists():
                        result["error"] = "No test image available"
                        return result
                    
                    image_key = api_info.get("image_key", "file")
                    with open(test_image, "rb") as f:
                        files = {image_key: ("test.jpg", f, "image/jpeg")}
                        response = await client.post(url, files=files)
            
            result["response_time_ms"] = round((time.time() - start) * 1000, 2)
            result["status_code"] = response.status_code
            
            # Only HTTP 200 is accepted as success
            if response.status_code == 200:
                result["reachable"] = True
                try:
                    result["response_data"] = response.json()
                except Exception:
                    pass
            else:
                result["error"] = f"Expected 200, got {response.status_code}"
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        result["error"] += f" - {error_data['detail']}"
                except Exception:
                    pass
                logger.warning(f"API {api_info['name']} returned {response.status_code}")
            
    except httpx.ConnectTimeout:
        result["error"] = "Connection timeout"
        logger.warning(f"API timeout: {api_info['name']}")
    except httpx.ReadTimeout:
        result["error"] = "Read timeout (server too slow)"
        logger.warning(f"API read timeout: {api_info['name']}")
    except httpx.ConnectError as e:
        result["error"] = f"Connection error: {str(e)}"
        logger.warning(f"API connection error: {api_info['name']}")
    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"API check error for {api_info['name']}: {e}")
    
    return result


async def run_api_check_async() -> Dict[str, Any]:
    """
    Run API connectivity checks asynchronously.
    
    Returns:
        Check result dictionary
    """
    # Find test image for POST endpoints
    test_image = find_test_image()
    if test_image:
        logger.info(f"Using test image: {test_image}")
    else:
        logger.warning("No test image found, some API checks will be skipped")
    
    # Run checks sequentially to avoid overwhelming the API
    results = []
    for api in EXTERNAL_APIS:
        result = await check_api_endpoint(api, test_image)
        results.append(result)
    
    # Check if required APIs are reachable
    all_ok = True
    for api, result in zip(EXTERNAL_APIS, results):
        if api.get("required", False) and not result["reachable"]:
            all_ok = False
    
    return {
        "check": "external_apis",
        "success": all_ok,
        "details": results
    }


def run_api_check() -> Dict[str, Any]:
    """
    Run API connectivity checks (sync wrapper).
    
    Returns:
        Check result dictionary
    """
    return asyncio.run(run_api_check_async())
