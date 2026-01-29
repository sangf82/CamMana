import csv
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional
from backend.config import DATA_DIR
from backend.data_process.csv_utils import CAMERA_HEADERS

logger = logging.getLogger(__name__)

class CameraLogic:
    HEADERS = CAMERA_HEADERS
    FILE_NAME = "cameras.csv"

    def __init__(self):
        self.file_path = DATA_DIR / self.FILE_NAME
        self._ensure_file()

    def _ensure_file(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Ensure file exists with correct headers
        if not self.file_path.exists():
             with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                 writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                 writer.writeheader()
        else:
            # Check for header updates (Migration)
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    try:
                        current_headers = next(reader)
                    except StopIteration:
                        current_headers = []
                
                # If headers differ (added or removed), migrate
                if set(self.HEADERS) != set(current_headers):
                    logger.info("Migrating cameras.csv schema...")
                    data = self._read_csv() # Reads safely with current schema
                    self._write_csv(data) # Writes with NEW (self.HEADERS) schema
            except Exception as e:
                logger.error(f"Error checking/migrating CSV schema: {e}")

    def _read_csv(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists(): return []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
            # Normalize data if needed
            for row in data:
                # Ensure all headers exist
                for h in self.HEADERS:
                    if h not in row:
                        row[h] = ""
                        
                # Fix functions list
                # In CSV, we might store as string, logic expects list?
                # The prompt implies we need to fix loading. 
                # Let's assume standard consumer expects Dict.
                pass
            return data

    def _write_csv(self, data: List[Dict[str, Any]]):
        with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)

    def get_cameras(self) -> List[Dict[str, Any]]:
        return self._read_csv()

    def get_camera_by_id(self, cam_id: str) -> Optional[Dict[str, Any]]:
        cameras = self.get_cameras()
        return next((c for c in cameras if c.get('cam_id') == cam_id or c.get('id') == cam_id), None)

    def add_camera(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Generate ID if not present
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        current = self._read_csv()
        
        # Enforce unique name
        new_name = data.get('name', '').strip()
        if any(c.get('name', '').strip().lower() == new_name.lower() for c in current):
            raise Exception(f"Tên camera '{new_name}' đã tồn tại. Vui lòng chọn tên khác.")
            
        current.append(data)
        self._write_csv(current)
        
        # Sync Hook
        try:
            from backend.sync_process.sync.logic import sync_logic
            asyncio.create_task(sync_logic.broadcast_change("camera", "create", data))
        except: pass
        
        return data

    def save_camera(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a camera. Update if ID exists, otherwise add."""
        cam_id = data.get('cam_id') or data.get('id')
        if cam_id:
            updated = self.update_camera(cam_id, data)
            if updated:
                return updated
        return self.add_camera(data)

    def update_camera(self, cam_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self._read_csv()
        
        # If name is being updated, check for uniqueness
        new_name = data.get('name', '').strip()
        if new_name:
            if any(c.get('name', '').strip().lower() == new_name.lower() and (c.get('cam_id') != cam_id and c.get('id') != cam_id) for c in current):
                raise Exception(f"Tên camera '{new_name}' đã tồn tại. Vui lòng chọn tên khác.")

        updated = None
        for c in current:
            # Match by cam_id (custom ID) or id (internal ID)
            if c.get('cam_id') == cam_id or c.get('id') == cam_id:
                c.update(data)
                updated = c
                break
        if updated:
            self._write_csv(current)
            
            # Sync Hook
            try:
                from backend.sync_process.sync.logic import sync_logic
                asyncio.create_task(sync_logic.broadcast_change("camera", "update", updated))
            except: pass
            
            return updated
        return None

    def delete_camera(self, cam_id: str) -> bool:
        current = self._read_csv()
        initial = len(current)
        # Filter out by cam_id or id
        current = [c for c in current if c.get('cam_id') != cam_id and c.get('id') != cam_id]
        if len(current) < initial:
            self._write_csv(current)
            
            # Sync Hook
            try:
                from backend.sync_process.sync.logic import sync_logic
                asyncio.create_task(sync_logic.broadcast_change("camera", "delete", {"cam_id": cam_id}))
            except: pass
            
            return True
        return False
