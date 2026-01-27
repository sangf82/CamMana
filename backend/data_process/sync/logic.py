import httpx
import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
import socket
from zeroconf import IPVersion, ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
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
        self.discovered_pcs: Dict[str, str] = {} # name -> url
        self.zc = Zeroconf(ip_version=IPVersion.V4Only)
        self.load_config()
        if remote_url:
            self.remote_url = remote_url
            self.is_destination = False
            self.save_config()
            
        # Start advertising if master
        if self.is_destination:
            self.start_advertising()
        
        # Start browsing for others (clients use this to find master)
        self.browser = ServiceBrowser(self.zc, "_cammana-sync._tcp.local.", self)

    def start_advertising(self):
        """Advertise this PC as a CamMana Master on the network."""
        try:
            desc = {'version': '2.0.0'}
            hostname = socket.gethostname()
            # Try to get the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()

            info = ServiceInfo(
                "_cammana-sync._tcp.local.",
                f"{hostname}._cammana-sync._tcp.local.",
                addresses=[socket.inet_aton(ip)],
                port=int(os.getenv("PORT", "8000")),
                properties=desc,
                server=f"{hostname}.local.",
            )
            self.zc.register_service(info)
            logger.info(f"Registered Zeroconf service for {hostname} at {ip}")
        except Exception as e:
            logger.error(f"Failed to start Zeroconf advertising: {e}")

    def remove_service(self, zc, type_, name):
        if name in self.discovered_pcs:
            del self.discovered_pcs[name]
            logger.info(f"Service {name} removed")

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            if addresses:
                url = f"http://{addresses[0]}:{info.port}"
                self.discovered_pcs[name] = url
                logger.info(f"Discovered CamMana Master: {name} at {url}")

    def update_service(self, zc, type_, name):
        self.add_service(zc, type_, name)

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


    def handle_received_sync(self, payload: SyncPayload):
        """Process a sync payload received from a remote node."""
        if not self.is_destination:
            logger.warning("Received sync payload but not in destination mode. Ignoring.")
            return False
            
        data = payload.data
        if payload.type == "test":
            logger.info("Received test sync signal (ping)")
            return True

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
            elif payload.action == "update_folder_path":
                # Update folder_path for a specific record (used after file sync)
                record_id = data.get("id")
                folder_path = data.get("folder_path")
                if record_id and folder_path:
                    self.history_logic.update_record(record_id, {"folder_path": folder_path})
                    logger.info(f"Updated folder_path for record {record_id}")
                    return True
        elif payload.type == "registered_car":
            from backend.data_process.register_car.logic import RegisteredCarLogic
            reg_logic = RegisteredCarLogic()
            if payload.action == "create" or payload.action == "update":
                reg_logic.save_car(data)
                return True
        elif payload.type == "user":
            from backend.api.user import UserLogic
            user_logic = UserLogic()
            if payload.action == "create" or payload.action == "update":
                user_logic.save_user(data)
                return True
            elif payload.action == "delete":
                username = data.get("username")
                if username:
                    user_logic.delete_user(username)
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

    def __del__(self):
        try:
            self.zc.close()
        except:
            pass
