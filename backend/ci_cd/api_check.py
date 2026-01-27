"""
API Check - Verify external API connectivity

Tests connections to external services like the AI API.
"""

import logging
import asyncio
from typing import Dict, Any, List

import httpx

from backend.settings import settings

logger = logging.getLogger(__name__)

# External APIs to check
EXTERNAL_APIS = [
    {
        "name": "AI/ML API",
        "url": f"{settings.ai_api_url}/health",
        "timeout": 10.0,
        "required": False,  # App can work offline with local models
    },
]


async def check_api_endpoint(api_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check connectivity to a single API endpoint.
    
    Args:
        api_info: API information dictionary
        
    Returns:
        Check result dictionary
    """
    result = {
        "name": api_info["name"],
        "url": api_info["url"],
        "reachable": False,
        "response_time_ms": None,
        "status_code": None,
        "error": None,
    }
    
    try:
        import time
        start = time.time()
        
        async with httpx.AsyncClient(timeout=api_info.get("timeout", 10.0)) as client:
            response = await client.get(api_info["url"])
            
            result["response_time_ms"] = round((time.time() - start) * 1000, 2)
            result["status_code"] = response.status_code
            result["reachable"] = response.status_code < 500
            
    except httpx.ConnectTimeout:
        result["error"] = "Connection timeout"
        logger.warning(f"API timeout: {api_info['name']}")
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
    tasks = [check_api_endpoint(api) for api in EXTERNAL_APIS]
    results = await asyncio.gather(*tasks)
    
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
