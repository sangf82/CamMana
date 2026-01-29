"""
Sync Logic - Master/Client synchronization using Zeroconf

Handles:
- Zeroconf service discovery and advertising
- Sync configuration persistence
- Data synchronization payloads
"""

import httpx
import asyncio
import logging
import os
import json
import socket
import subprocess
import re
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from zeroconf import IPVersion, ServiceInfo, Zeroconf, ServiceBrowser

from backend.schemas import SyncPayload
from backend.settings import settings

logger = logging.getLogger(__name__)


class SyncLogic:
    """Handles data synchronization between two PCs."""
    
    def __init__(self, remote_url: Optional[str] = None):
        # Lazy import to avoid circular dependency
        from backend.data_process.history.logic import HistoryLogic
        
        self.history_logic = HistoryLogic()
        self.discovered_pcs: Dict[str, str] = {}  # name -> url
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
        self.browser = ServiceBrowser(self.zc, "_cammana-sync._tcp.local.", handlers=[self.add_service, self.remove_service, self.update_service])  # type: ignore

    def _get_best_local_ip(self) -> str:
        """
        Get the best local IP address for advertising.
        Prioritizes physical network interfaces over VPN/virtual ones.
        """
        # Skip these common virtual/VPN prefixes
        blocked_prefixes = ('172.', '10.244.', '169.254.', '100.') # 100.x is Tailscale
        
        # Method 1: Use UDP socket trick (works when internet is available)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if not any(ip.startswith(pref) for pref in blocked_prefixes):
                    return ip
            finally:
                s.close()
        except:
            pass
        
        # Method 2: Parse ipconfig output (Windows specific)
        try:
            result = subprocess.run(
                ["ipconfig"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            output = result.stdout
            
            # Look for IPv4 addresses in common interface patterns
            priority_patterns = [
                (r"Ethernet adapter.*?IPv4 Address.*?:\s*([\d.]+)", 1),
                (r"Wireless LAN adapter Wi-Fi.*?IPv4 Address.*?:\s*([\d.]+)", 2),
                (r"Wireless LAN adapter.*?IPv4 Address.*?:\s*([\d.]+)", 3),
            ]
            
            found_ips = []
            for section in output.split("\n\n"):
                # Skip sections with "Virtual", "Docker", "vEthernet", "Tailscale"
                if any(word in section.lower() for word in ["virtual", "docker", "vethernet", "tailscale"]):
                    continue
                    
                for pattern, priority in priority_patterns:
                    match = re.search(pattern, section, re.DOTALL | re.IGNORECASE)
                    if match:
                        ip = match.group(1)
                        if not any(ip.startswith(pref) for pref in blocked_prefixes) and ip != "127.0.0.1":
                            found_ips.append((priority, ip))
            
            if found_ips:
                found_ips.sort(key=lambda x: x[0])
                return found_ips[0][1]
        except:
            pass
        
        # Method 3: Fallback to socket hostname resolution
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            for ip in ips:
                if not any(ip.startswith(pref) for pref in blocked_prefixes) and ip != "127.0.0.1":
                    return ip
        except:
            pass
        
        # Last resort
        return "127.0.0.1"

    def start_advertising(self):
        """Advertise this PC as a CamMana Master on the network."""
        try:
            desc = {'version': '2.0.0'}
            hostname = socket.gethostname()
            ip = self._get_best_local_ip()

            info = ServiceInfo(
                "_cammana-sync._tcp.local.",
                f"{hostname}._cammana-sync._tcp.local.",
                addresses=[socket.inet_aton(ip)],
                port=settings.port,
                properties=desc,
                server=f"{hostname}.local.",
            )
            self.zc.register_service(info)
            logger.info(f"Registered Zeroconf service for {hostname} at {ip}")
        except Exception as e:
            logger.error(f"Failed to start Zeroconf advertising: {e}")

    def remove_service(self, zc=None, type_=None, name=None, **kwargs):
        """Handle service removal (zeroconf callback)."""
        # Handle both positional and keyword arguments from different zeroconf versions
        zc = zc or kwargs.get('zeroconf')
        type_ = type_ or kwargs.get('service_type')
        name = name or kwargs.get('name')
        if name and name in self.discovered_pcs:
            del self.discovered_pcs[name]
            logger.info(f"Service {name} removed")

    def add_service(self, zc=None, type_=None, name=None, **kwargs):
        """Handle service discovery (zeroconf callback)."""
        # Handle both positional and keyword arguments from different zeroconf versions
        zc = zc or kwargs.get('zeroconf')
        type_ = type_ or kwargs.get('service_type')
        name = name or kwargs.get('name')
        if not zc or not type_ or not name:
            return
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            if addresses:
                url = f"http://{addresses[0]}:{info.port}"
                self.discovered_pcs[name] = url
                logger.info(f"Discovered CamMana Master: {name} at {url}")

    def update_service(self, zc=None, type_=None, name=None, **kwargs):
        """Handle service update (zeroconf callback)."""
        self.add_service(zc, type_, name, **kwargs)

    def load_config(self):
        """Load sync configuration from JSON file."""
        config_file = settings.sync_config_path
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
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
            config_file = settings.sync_config_path
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump({
                    "remote_url": self.remote_url,
                    "is_destination": self.is_destination
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save sync config: {e}")

    def handle_received_sync(self, payload: SyncPayload) -> bool:
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
                self.history_logic.save_record(data)
                return True
            elif payload.action == "update":
                plate = data.get("plate")
                time_in = data.get("time_in")
                if plate and time_in:
                    self.history_logic.update_record_by_plate_time(plate, time_in, data)
                    return True
            elif payload.action == "update_folder_path":
                record_id = data.get("id")
                folder_path = data.get("folder_path")
                if record_id and folder_path:
                    self.history_logic.update_record(record_id, {"folder_path": folder_path})
                    logger.info(f"Updated folder_path for record {record_id}")
                    return True
                    
        elif payload.type == "registered_car":
            from backend.data_process.register_car.logic import RegisteredCarLogic
            reg_logic = RegisteredCarLogic()
            if payload.action in ("create", "update"):
                reg_logic.save_car(data)
                return True
            elif payload.action == "delete":
                car_id = data.get("car_id")
                if car_id:
                    reg_logic.delete_car(car_id)
                    return True
                
        elif payload.type == "user":
            from backend.data_process.user.logic import UserLogic
            user_logic = UserLogic()
            if payload.action in ("create", "update"):
                user_logic.save_user(data)
                return True
            elif payload.action == "delete":
                username = data.get("username")
                if username:
                    user_logic.delete_user(username)
                    return True

        elif payload.type == "camera":
            from backend.camera.logic import CameraLogic
            cam_logic = CameraLogic()
            if payload.action in ("create", "update"):
                cam_logic.save_camera(data)
                return True
            elif payload.action == "delete":
                cam_id = data.get("cam_id")
                if cam_id:
                    cam_logic.delete_camera(cam_id)
                    return True

        elif payload.type == "location":
            from backend.data_process.location.logic import LocationLogic
            loc_logic = LocationLogic()
            if payload.action in ("create", "update"):
                loc_logic.save_location(data)
                return True
            elif payload.action == "delete":
                loc_id = data.get("id")
                if loc_id:
                    loc_logic.delete_location(loc_id)
                    return True

        elif payload.type == "camera_type":
            from backend.data_process.camera_type.logic import CameraTypeLogic
            type_logic = CameraTypeLogic()
            if payload.action in ("create", "update"):
                type_logic.save_camera_type(data)
                return True
            elif payload.action == "delete":
                type_id = data.get("id")
                if type_id:
                    type_logic.delete_type(type_id)
                    return True

        elif payload.type == "system_config":
            from backend.data_process.storage_config import save_system_config
            if payload.action == "update":
                save_system_config(data)
                return True
        return False

    async def broadcast_change(
        self, 
        type: str, 
        action: str, 
        data: Dict[str, Any], 
        current_user_id: Optional[str] = None
    ):
        """Helper to create payload and push in background."""
        # Only Nodes push to Destination. Destination does not push back.
        if self.is_destination or not self.remote_url:
            return

        payload = SyncPayload(
            type=type,
            action=action,
            data=data,
            timestamp=datetime.now().isoformat()
        )
        
        asyncio.create_task(self.push_to_remote(payload))

    async def push_to_remote(self, payload: SyncPayload) -> bool:
        """Push a local change to the remote node."""
        if not self.remote_url:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = self.remote_url.rstrip('/')
                response = await client.post(
                    f"{url}/api/sync/receive",
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"[Sync] Push to remote failed: {e}")
            return False

    def __del__(self):
        try:
            self.zc.close()
        except:
            pass
# Global singleton instance
sync_logic = SyncLogic()
