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
    sync_logic.remote_url = remote_url
    sync_logic.is_destination = is_destination
    sync_logic.save_config()
    return {
        "status": "configured", 
        "remote_url": remote_url,
        "is_destination": is_destination,
        "mode": "Destination (Master)" if is_destination else "Node (Client)"
    }

@sync_router.post("/test-push")
async def test_push():
    """Manually trigger a sync broadcast to test connectivity."""
    if sync_logic.is_destination:
        return {"error": "Cannot test push in Destination mode"}
    
    await sync_logic.broadcast_change(
        type="history",
        action="update",
        data={"id": "test-sync", "plate": "TEST-SYNC", "note": "Sync test from Node"}
    )
    return {"status": "pushed", "target": sync_logic.remote_url}
