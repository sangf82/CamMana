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
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            logger.info(f"[Proxy] Connecting to Master: {url}")
            response = await client.get(url)
            if response.status_code == 200:
                logger.info(f"[Proxy] Connection Successful: {url}")
                return response.json()
            else:
                logger.warning(f"[Proxy] Master returned error {response.status_code} for {url}. Falling back to local/default.")
                return None
        except httpx.ConnectTimeout:
            logger.error(f"[Proxy] Connection TIMEOUT connecting to {url}. Check if Master PC IP is correct and Firewall allows port {config.PORT}.")
            return None
        except httpx.ConnectError as e:
            logger.error(f"[Proxy] Connection REFUSED to {url}. Is Master Server running? Error: {e}")
            return None
        except Exception as e:
            logger.error(f"[Proxy] Connection FAILED to {url}: {e}")
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


async def upload_folder_to_master(folder_path: Path, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
    """
    Upload a car history folder (with all its files) to the Master node.
    
    Args:
        folder_path: Local path to the folder to upload
        timeout: Request timeout in seconds (longer for file uploads)
        
    Returns:
        Response from master with the new folder_path on master, or None if failed
    """
    import socket
    
    master_url = get_master_url()
    if not master_url:
        logger.debug("Not in client mode, skipping folder upload")
        return None
    
    if not folder_path.exists() or not folder_path.is_dir():
        logger.error(f"Folder does not exist: {folder_path}")
        return None
    
    try:
        # Extract folder info
        folder_name = folder_path.name  # e.g., "uuid_in_hh-mm-ss"
        date_folder = folder_path.parent.name  # e.g., "dd-mm-yyyy"
        source_pc = socket.gethostname()
        
        # Collect all files in the folder
        files_to_upload = []
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                files_to_upload.append(file_path)
        
        if not files_to_upload:
            logger.warning(f"No files found in folder: {folder_path}")
            return None
        
        # Prepare multipart files
        files = []
        for fp in files_to_upload:
            files.append(("files", (fp.name, open(fp, "rb"), "application/octet-stream")))
        
        # Prepare form data
        data = {
            "folder_name": folder_name,
            "date_folder": date_folder,
            "source_pc": source_pc
        }
        
        url = master_url.rstrip('/') + "/api/sync/files/upload-folder"
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, data=data, files=files)
            
            # Close file handles
            for _, file_tuple in files:
                file_tuple[1].close()
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[FileSync] Uploaded folder to master: {folder_name} ({len(files_to_upload)} files)")
                return result
            else:
                logger.warning(f"[FileSync] Upload failed with status {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"[FileSync] Failed to upload folder to master: {e}")
        return None


async def sync_folder_and_update_record(
    folder_path: Path, 
    record_id: str,
    sync_logic
) -> Optional[str]:
    """
    Upload folder to master and update the history record with master's folder_path.
    
    Args:
        folder_path: Local folder path
        record_id: The history record UUID
        sync_logic: Reference to the SyncLogic instance
        
    Returns:
        The master's folder_path if successful, None otherwise
    """
    if not is_client_mode():
        return None
    
    # Upload folder
    result = await upload_folder_to_master(folder_path)
    
    if result and result.get("success"):
        master_folder_path = result.get("folder_path")
        
        # Update the synced record on master to use master's folder_path
        # This is done via a special sync call
        try:
            master_url = get_master_url()
            if master_url:
                from backend.schemas import SyncPayload
                from datetime import datetime
                
                payload = SyncPayload(
                    type="history",
                    action="update_folder_path",
                    data={
                        "id": record_id,
                        "folder_path": master_folder_path
                    },
                    timestamp=datetime.now().isoformat()
                )
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"{master_url.rstrip('/')}/api/sync/receive",
                        json=payload.model_dump(),
                        headers={"Content-Type": "application/json"}
                    )
                    
        except Exception as e:
            logger.error(f"Failed to update folder_path on master: {e}")
        
        return master_folder_path
    
    return None

