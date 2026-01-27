import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.schemas import SyncPayload
from backend.config import DATA_DIR
from backend.data_process.history.logic import HistoryLogic

logger = logging.getLogger(__name__)

class SyncLogic:
    """Handles data synchronization between two PCs."""
    
    def __init__(self, remote_url: Optional[str] = None):
        self.remote_url = remote_url # e.g. "http://192.168.1.50:8000"
        self.history_logic = HistoryLogic()

    async def push_to_remote(self, payload: SyncPayload):
        """Push a local change to the remote node."""
        if not self.remote_url:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.remote_url}/api/sync/receive",
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to push to remote {self.remote_url}: {e}")
            return False

    def handle_received_sync(self, payload: SyncPayload):
        """Process a sync payload received from a remote node."""
        data = payload.data
        if payload.type == "history":
            if payload.action == "create":
                # Save to local history
                self.history_logic.save_record(data)
                return True
            elif payload.action == "update":
                # Update local history
                plate = data.get("plate")
                time_in = data.get("time_in")
                if plate and time_in:
                    self.history_logic.update_record_by_plate_time(plate, time_in, data)
                    return True
        elif payload.type == "registered_car":
            from backend.data_process.register_car.logic import RegisteredCarLogic
            reg_logic = RegisteredCarLogic()
            if payload.action == "create" or payload.action == "update":
                reg_logic.save_car(data)
                return True
        
        return False

    async def broadcast_change(self, type: str, action: str, data: Dict[str, Any], current_user_id: Optional[str] = None):
        """Helper to create payload and push in background."""
        if not self.remote_url:
            return

        # Prepare payload
        payload = SyncPayload(
            type=type,
            action=action,
            data=data,
            timestamp=datetime.now().isoformat()
        )
        
        # We can include user_id in payload metadata or just trust the network if configured
        # But per user request, we should ideally check if both are "sharing"
        
        asyncio.create_task(self.push_to_remote(payload))

    async def push_to_remote(self, payload: SyncPayload):
        """Push a local change to the remote node."""
        if not self.remote_url:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=1.0) as client: # Fast timeout
                url = self.remote_url.rstrip('/')
                response = await client.post(
                    f"{url}/api/sync/receive",
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200
        except Exception:
            # Silently fail if remote is down to not block local workflow
            return False
