import csv
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

class CameraTypeLogic:
    HEADERS = ["type_id", "type_name", "type_functions"]
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
                funcs = row.get('type_functions', '')
                if funcs:
                    # Remove empty strings if split results in them
                    row['type_functions'] = [f for f in funcs.split(';') if f]
                else:
                    row['type_functions'] = []
            return data

    def _write_csv(self, data: List[Dict[str, Any]]):
        rows_to_write = []
        for row in data:
            r = row.copy()
            if isinstance(r.get('type_functions'), list):
                r['type_functions'] = ";".join(r['type_functions'])
            rows_to_write.append(r)
            
        with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(rows_to_write)

    def get_types(self) -> List[Dict[str, Any]]:
        return self._read_csv()

    def add_type(self, data: Dict[str, Any]) -> Dict[str, Any]:
        new_type = {
            "type_id": str(uuid.uuid4()),
            "type_name": str(data['type_name']),
            "type_functions": data.get('type_functions', [])
        }
        current = self._read_csv()
        current.append(new_type)
        self._write_csv(current)
        return new_type

    def update_type(self, type_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self._read_csv()
        updated = None
        for t in current:
            if t['type_id'] == type_id:
                if 'type_name' in data: t['type_name'] = str(data['type_name'])
                if 'type_functions' in data: t['type_functions'] = data['type_functions']
                updated = t
                break
        if updated:
            self._write_csv(current)
            return updated
        return None

    def delete_type(self, type_id: str) -> bool:
        current = self._read_csv()
        initial = len(current)
        current = [t for t in current if t['type_id'] != type_id]
        if len(current) < initial:
            self._write_csv(current)
            return True
        return False
