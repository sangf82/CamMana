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
    # This would check if the remote node is reachable
    return {
        "remote_url": sync_logic.remote_url or "not_configured",
        "status": "online" if sync_logic.remote_url else "standalone"
    }

@sync_router.post("/configure")
async def configure_sync(remote_url: str):
    """Configure the remote URL for synchronization."""
    sync_logic.remote_url = remote_url
    return {"status": "configured", "remote_url": remote_url}
