import csv
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from backend.config import DATA_DIR
from backend.data_process._common import LOCATION_HEADERS
from backend.data_process._sync import CameraDataSync

logger = logging.getLogger(__name__)

class LocationLogic:
    HEADERS = ["id", "name", "tag"]
    FILE_NAME = "locations.csv"
    
    # Valid tags
    TAGS = ["check-in", "check-out", "basic", "Đo thể tích", "Cổng vào", "Cổng ra"]

    def __init__(self):
        self.file_path = DATA_DIR / self.FILE_NAME
        self._ensure_file()

    def _ensure_file(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writeheader()

    def _read_csv(self) -> List[Dict[str, str]]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_csv(self, data: List[Dict[str, str]]):
        with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(data)

    def get_locations(self) -> List[Dict[str, str]]:
        return self._read_csv()

    def add_location(self, data: Dict[str, Any]) -> Dict[str, str]:
        # Mapping for API compatibility if API sends long keys
        name = data.get('name') or data.get('location_name')
        tag = data.get('tag') or data.get('location_tag')

        new_loc = {
            "id": str(uuid.uuid4()),
            "name": str(name),
            "tag": str(tag)
        }
             
        current = self._read_csv()
        current.append(new_loc)
        self._write_csv(current)
        return new_loc

    def update_location(self, loc_id: str, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        current = self._read_csv()
        updated_loc = None
        old_name = None
        
        for loc in current:
            if loc['id'] == loc_id:
                old_name = loc['name']  # Save old name for sync
                
                if 'name' in data: loc['name'] = str(data['name'])
                if 'location_name' in data: loc['name'] = str(data['location_name'])
                
                if 'tag' in data: loc['tag'] = str(data['tag'])
                if 'location_tag' in data: loc['tag'] = str(data['location_tag'])
                
                updated_loc = loc
                break
        
        if updated_loc:
            self._write_csv(current)
            
            # Sync: Update cameras that reference this location
            new_name = updated_loc['name']
            if old_name != new_name:
                CameraDataSync.sync_location_name(loc_id, new_name)
                logger.info(f"Location '{old_name}' -> '{new_name}': synced to cameras")
            
            return updated_loc
        return None

    def delete_location(self, loc_id: str) -> bool:
        current = self._read_csv()
        initial_len = len(current)
        current = [l for l in current if l['id'] != loc_id]
        if len(current) < initial_len:
            self._write_csv(current)
            
            # Sync: Clear location references in cameras
            CameraDataSync.remove_location_references(loc_id)
            logger.info(f"Location {loc_id} deleted: cleared from cameras")
            
            return True
        return False
