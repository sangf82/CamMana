from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.schemas import SyncPayload
from backend.data_process.sync.logic import SyncLogic

sync_router = APIRouter(prefix="/api/sync", tags=["sync"])
sync_logic = SyncLogic()

@sync_router.post("/receive")
async def receive_sync(payload: SyncPayload):
    """Endpoint for other PCs to push data to this PC."""
    success = sync_logic.handle_received_sync(payload)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to process sync payload")
    return {"status": "success"}

@sync_router.get("/status")
async def get_sync_status():
    """Check sync status and connectivity to the other node."""
    return {
        "is_destination": sync_logic.is_destination,
        "remote_url": sync_logic.remote_url or "not_configured",
        "mode": "Destination (Master)" if sync_logic.is_destination else "Node (Client)",
        "status": "online" if (sync_logic.is_destination or sync_logic.remote_url) else "standalone"
    }

@sync_router.post("/configure")
async def configure_sync(remote_url: Optional[str] = None, is_destination: bool = True):
    """Configure the synchronization settings."""
    old_is_destination = sync_logic.is_destination
    
    sync_logic.remote_url = remote_url
    sync_logic.is_destination = is_destination
    sync_logic.save_config()
    
    # Handle Zeroconf advertising when mode changes
    if is_destination and not old_is_destination:
        # Switched to Master mode - start advertising
        sync_logic.start_advertising()
    elif not is_destination and old_is_destination:
        # Switched to Client mode - optionally could stop advertising
        # (Zeroconf doesn't have easy stop, but it's fine for now)
        pass
    
    return {
        "status": "configured", 
        "remote_url": remote_url,
        "is_destination": is_destination,
        "mode": "Destination (Master)" if is_destination else "Node (Client)"
    }

@sync_router.get("/discover")
async def discover_masters():
    """Return list of discovered Master PCs on the local network. Filters out own PC."""
    import socket
    
    own_hostname = socket.gethostname().lower()
    
    result = []
    for name, url in sync_logic.discovered_pcs.items():
        # Filter out own PC (case-insensitive hostname match)
        pc_name = name.split("._cammana-sync")[0].lower() if "._cammana-sync" in name else name.lower()
        
        if pc_name != own_hostname:
            result.append({"name": name, "url": url})
    
    return result

@sync_router.post("/test-push")
async def test_push():
    """Manually trigger a sync broadcast to test connectivity."""
    if sync_logic.is_destination:
        return {"success": False, "message": "Cannot test push while in Master mode"}
    
    if not sync_logic.remote_url:
        return {"success": False, "message": "Master URL not configured"}

    payload = SyncPayload(
        type="test",
        action="ping",
        data={"message": "ping from client"},
        timestamp=datetime.now().isoformat()
    )
    
    success = await sync_logic.push_to_remote(payload)
    if success:
        return {"success": True, "message": f"Successfully connected to Master at {sync_logic.remote_url}"}
    else:
        return {"success": False, "message": f"Failed to connect to Master at {sync_logic.remote_url}"}
