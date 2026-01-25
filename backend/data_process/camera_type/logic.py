import csv
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from backend.config import DATA_DIR
from backend.data_process._sync import CameraDataSync

logger = logging.getLogger(__name__)

class CameraTypeLogic:
    HEADERS = ["id", "name", "functions"]
    FILE_NAME = "camtypes.csv"

    def __init__(self):
        self.file_path = DATA_DIR / self.FILE_NAME
        self._ensure_file()

    def _ensure_file(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writeheader()

    def _read_csv(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
            # transform string to list
            for row in data:
                funcs = row.get('functions', '')
                if funcs:
                    # Remove empty strings if split results in them
                    row['functions'] = [f for f in funcs.split(';') if f]
                else:
                    row['functions'] = []
            return data

    def _write_csv(self, data: List[Dict[str, Any]]):
        rows_to_write = []
        for row in data:
            r = row.copy()
            if isinstance(r.get('functions'), list):
                r['functions'] = ";".join(r['functions'])
            rows_to_write.append(r)
            
        with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(rows_to_write)

    def get_types(self) -> List[Dict[str, Any]]:
        return self._read_csv()

    def add_type(self, data: Dict[str, Any]) -> Dict[str, Any]:
        new_type = {
            "id": str(uuid.uuid4()),
            "name": str(data['name']),
            "functions": data.get('functions', [])
        }
        current = self._read_csv()
        current.append(new_type)
        self._write_csv(current)
        return new_type

    def update_type(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self._read_csv()
        updated = None
        old_name = None
        
        for t in current:
            if t['id'] == id:
                old_name = t['name']  # Save old name for sync
                
                if 'name' in data: t['name'] = str(data['name'])
                if 'functions' in data: t['functions'] = data['functions']
                updated = t
                break
        
        if updated:
            self._write_csv(current)
            
            # Sync: Update cameras that have this type
            new_name = updated['name']
            if old_name and old_name != new_name:
                CameraDataSync.sync_camtype_name(old_name, new_name)
                logger.info(f"Camera type '{old_name}' -> '{new_name}': synced to cameras")
            
            return updated
        return None

    def delete_type(self, id: str) -> bool:
        current = self._read_csv()
        initial = len(current)
        
        # Find the type name before deleting
        type_name = None
        for t in current:
            if t['id'] == id:
                type_name = t['name']
                break
        
        current = [t for t in current if t['id'] != id]
        if len(current) < initial:
            self._write_csv(current)
            
            # Sync: Clear type references in cameras
            if type_name:
                CameraDataSync.remove_camtype_references(type_name)
                logger.info(f"Camera type '{type_name}' deleted: cleared from cameras")
            
            return True
        return False
