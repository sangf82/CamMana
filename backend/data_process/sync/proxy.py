"""
Proxy utilities for Client mode to fetch data from Master node.
"""
import httpx
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

SYNC_CONFIG_FILE = PROJECT_ROOT / "database" / "sync_config.json"


def get_sync_config() -> Dict[str, Any]:
    """Read sync configuration from file."""
    if SYNC_CONFIG_FILE.exists():
        try:
            with open(SYNC_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read sync config: {e}")
    return {"remote_url": None, "is_destination": True}


def is_client_mode() -> bool:
    """Check if this node is running in client mode (not destination/master)."""
    config = get_sync_config()
    return not config.get("is_destination", True) and config.get("remote_url")


def get_master_url() -> Optional[str]:
    """Get the master URL if in client mode."""
    config = get_sync_config()
    if not config.get("is_destination", True):
        return config.get("remote_url")
    return None


async def proxy_get(endpoint: str, timeout: float = 5.0) -> Optional[Any]:
    """
    Proxy a GET request to the master node.
    
    Args:
        endpoint: The API endpoint (e.g., '/api/registered_cars')
        timeout: Request timeout in seconds
        
    Returns:
        JSON response from master, or None if failed
    """
    master_url = get_master_url()
    if not master_url:
        return None
    
    try:
        url = master_url.rstrip('/') + endpoint
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Proxy GET {url} returned status {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Proxy GET failed for {endpoint}: {e}")
        return None


async def proxy_post(endpoint: str, data: Dict[str, Any], timeout: float = 5.0) -> Optional[Any]:
    """
    Proxy a POST request to the master node.
    
    Args:
        endpoint: The API endpoint
        data: JSON data to send
        timeout: Request timeout in seconds
        
    Returns:
        JSON response from master, or None if failed
    """
    master_url = get_master_url()
    if not master_url:
        return None
    
    try:
        url = master_url.rstrip('/') + endpoint
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.warning(f"Proxy POST {url} returned status {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Proxy POST failed for {endpoint}: {e}")
        return None


async def proxy_put(endpoint: str, data: Dict[str, Any], timeout: float = 5.0) -> Optional[Any]:
    """
    Proxy a PUT request to the master node.
    """
    master_url = get_master_url()
    if not master_url:
        return None
    
    try:
        url = master_url.rstrip('/') + endpoint
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.put(
                url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Proxy PUT {url} returned status {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Proxy PUT failed for {endpoint}: {e}")
        return None


async def proxy_delete(endpoint: str, timeout: float = 5.0) -> bool:
    """
    Proxy a DELETE request to the master node.
    """
    master_url = get_master_url()
    if not master_url:
        return False
    
    try:
        url = master_url.rstrip('/') + endpoint
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.delete(url)
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Proxy DELETE failed for {endpoint}: {e}")
        return False
