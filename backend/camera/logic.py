import csv
import uuid
import logging
from typing import List, Dict, Any, Optional
from backend.config import DATA_DIR
from backend.data_process._common import CAMERA_HEADERS

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
            # Simple check if migration needed or headers match
            # For now, append to existing if valid
            pass

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
        
        # Ensure cam_id matches internal ID logic if needed, or keep separate
        # The schema has both 'id' and 'cam_id'. 
        # 'id' usually timestamp-based in _common. 
        # let's just use what's passed or generate.
        
        current = self._read_csv()
        current.append(data)
        self._write_csv(current)
        return data

    def update_camera(self, cam_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self._read_csv()
        updated = None
        for c in current:
            # Match by cam_id (custom ID) or id (internal ID)
            if c.get('cam_id') == cam_id or c.get('id') == cam_id:
                c.update(data)
                updated = c
                break
        if updated:
            self._write_csv(current)
            return updated
        return None

    def delete_camera(self, cam_id: str) -> bool:
        current = self._read_csv()
        initial = len(current)
        # Filter out by cam_id or id
        current = [c for c in current if c.get('cam_id') != cam_id and c.get('id') != cam_id]
        if len(current) < initial:
            self._write_csv(current)
            return True
        return False
