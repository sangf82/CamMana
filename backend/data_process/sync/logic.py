import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.schemas import SyncPayload
from backend.config import DATA_DIR, PROJECT_ROOT
from backend.data_process.history.logic import HistoryLogic

import json
from pathlib import Path

logger = logging.getLogger(__name__)

SYNC_CONFIG_FILE = PROJECT_ROOT / "database" / "sync_config.json"

class SyncLogic:
    """Handles data synchronization between two PCs."""
    
    def __init__(self, remote_url: Optional[str] = None):
        self.history_logic = HistoryLogic()
        self.load_config()
        if remote_url:
            self.remote_url = remote_url
            self.is_destination = False
            self.save_config()

    def load_config(self):
        """Load sync configuration from JSON file."""
        if SYNC_CONFIG_FILE.exists():
            try:
                with open(SYNC_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.remote_url = config.get("remote_url")
                    self.is_destination = config.get("is_destination", True)
                    logger.info(f"Loaded sync config: destination={self.is_destination}, remote={self.remote_url}")
            except Exception as e:
                logger.error(f"Failed to load sync config: {e}")
                self.remote_url = None
                self.is_destination = True
        else:
            self.remote_url = None
            self.is_destination = True

    def save_config(self):
        """Save sync configuration to JSON file."""
        try:
            SYNC_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SYNC_CONFIG_FILE, 'w') as f:
                json.dump({
                    "remote_url": self.remote_url,
                    "is_destination": self.is_destination
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save sync config: {e}")

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
        if not self.is_destination:
            logger.warning("Received sync payload but not in destination mode. Ignoring.")
            return False
            
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
        # Only Nodes push to Destination. Destination does not push back (to avoid loops).
        if self.is_destination or not self.remote_url:
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
