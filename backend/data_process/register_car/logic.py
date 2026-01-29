import csv
import shutil
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging
import asyncio

from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

class RegisteredCarLogic:
    HEADERS = [
        "car_id", "car_plate", "car_brand", "car_model", 
        "car_owner", "car_color", "car_wheel", 
        "car_volume", "car_note",
        "car_register_date", "car_update_date"
    ]
    DATE_FORMAT = "%d-%m-%Y"
    FILE_PREFIX = "registered_cars_"

    def __init__(self):
        self.today = datetime.now().strftime(self.DATE_FORMAT)
        self.current_file = DATA_DIR / f"{self.FILE_PREFIX}{self.today}.csv"
        self._ensure_data_dir()
        self.rotate_daily_file()

    def _ensure_data_dir(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _get_file_date(self, filename: str) -> Optional[datetime]:
        try:
            date_str = filename.replace(self.FILE_PREFIX, "").replace(".csv", "")
            return datetime.strptime(date_str, self.DATE_FORMAT)
        except ValueError:
            return None

    def rotate_daily_file(self):
        """
        On startup/init:
        1. Check if today's file exists. If not, copy from previous day (most recent).
        2. Delete files older than 2 days.
        """
        if not self.current_file.exists():
            files = list(DATA_DIR.glob(f"{self.FILE_PREFIX}*.csv"))
            sorted_files = []
            for f in files:
                d = self._get_file_date(f.name)
                if d:
                    sorted_files.append((d, f))
            
            sorted_files.sort(key=lambda x: x[0], reverse=True)
            
            if sorted_files:
                last_date, last_file = sorted_files[0]
                shutil.copy(last_file, self.current_file)
                logger.info(f"Created {self.current_file.name} from {last_file.name}")
            else:
                self._write_csv(self.current_file, [])
                logger.info(f"Created new empty file {self.current_file.name}")

        limit_date = datetime.now() - timedelta(days=2)
        for f in DATA_DIR.glob(f"{self.FILE_PREFIX}*.csv"):
            d = self._get_file_date(f.name)
            if d and d.date() < limit_date.date():
                try:
                    f.unlink()
                except Exception: pass

    def _read_csv(self) -> List[Dict[str, str]]:
        if not self.current_file.exists():
            return []
        with open(self.current_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_csv(self, path: Path, data: List[Dict[str, str]]):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)

    def get_all_cars(self) -> List[Dict[str, str]]:
        return self._read_csv()

    @staticmethod
    def normalize_plate(plate: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '', plate).upper()

    def get_car_by_plate(self, plate: str) -> Optional[Dict[str, str]]:
        norm_plate = self.normalize_plate(plate)
        cars = self.get_all_cars()
        for car in cars:
            if self.normalize_plate(car['car_plate']) == norm_plate:
                return car
        return None

    def add_car(self, car_data: Dict[str, Any]) -> Dict[str, str]:
        current_data = self._read_csv()
        
        norm_plate = self.normalize_plate(car_data.get('car_plate', ''))
        for car in current_data:
            if self.normalize_plate(car['car_plate']) == norm_plate:
                raise ValueError(f"Car with plate {car_data.get('car_plate')} already exists.")

        new_car = {
            "car_id": str(uuid.uuid4()),
            "car_plate": car_data.get('car_plate', ''),
            "car_brand": car_data.get('car_brand', ''),
            "car_model": car_data.get('car_model', ''),
            "car_owner": car_data.get('car_owner', ''),
            "car_color": car_data.get('car_color', ''),
            "car_wheel": str(car_data.get('car_wheel', '')),
            "car_volume": str(car_data.get('car_volume', '')),
            "car_note": car_data.get('car_note', ''),
            "car_register_date": datetime.now().strftime(self.DATE_FORMAT),
            "car_update_date": datetime.now().strftime(self.DATE_FORMAT)
        }
        
        current_data.append(new_car)
        self._write_csv(self.current_file, current_data)
        # Sync Hook
        try:
            from backend.sync_process.sync.logic import sync_logic
            asyncio.create_task(sync_logic.broadcast_change("registered_car", "create", new_car))
        except Exception as e:
            logger.error(f"Failed to sync registered_car create: {e}")
            pass
            
        return new_car

    def save_car(self, car_data: Dict[str, Any]) -> Dict[str, str]:
        """Save a car. Update if ID exists, otherwise update by plate, otherwise add."""
        car_id = car_data.get('car_id')
        if car_id:
            updated = self.update_car(car_id, car_data)
            if updated:
                return updated
        
        # Try finding by plate
        current_data = self._read_csv()
        norm_plate = self.normalize_plate(car_data.get('car_plate', ''))
        for car in current_data:
            if self.normalize_plate(car['car_plate']) == norm_plate:
                return self.update_car(car['car_id'], car_data)
                
        # Not found, add new
        return self.add_car(car_data)

    def update_car(self, car_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        current_data = self._read_csv()
        updated_car = None
        
        for car in current_data:
            if car['car_id'] == car_id:
                # Update fields
                for key in self.HEADERS:
                    if key in update_data and key not in ['car_id', 'car_plate']:
                        car[key] = str(update_data[key])
                
                car['car_update_date'] = datetime.now().strftime(self.DATE_FORMAT)
                updated_car = car
                break
        
        if updated_car:
            self._write_csv(self.current_file, current_data)
            
            # Sync Hook
            try:
                from backend.sync_process.sync.logic import sync_logic
                asyncio.create_task(sync_logic.broadcast_change("registered_car", "update", updated_car))
            except Exception as e:
                logger.error(f"Failed to sync registered_car update: {e}")
                pass
                
            return updated_car
        return None

    def delete_car(self, car_id: str) -> bool:
        current_data = self._read_csv()
        initial_len = len(current_data)
        current_data = [c for c in current_data if c['car_id'] != car_id]
        
        if len(current_data) < initial_len:
            self._write_csv(self.current_file, current_data)
            
            # Sync Hook
            try:
                from backend.sync_process.sync.logic import sync_logic
                asyncio.create_task(sync_logic.broadcast_change("registered_car", "delete", {"car_id": car_id}))
            except Exception as e:
                logger.error(f"Failed to sync registered_car delete: {e}")
                pass
                
            return True
        return False

    def import_cars(self, import_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Merge import_data with current db.
        - Match by normalized plate.
        - If match: Update info.
        - If new: Add.
        - If not in import file: DELETE from DB ("If car data not have in the imported file, delete all that data").
          WAIT. "If car data not have in the imported file, delete all that data" 
          This implies the Import File acts as the MASTER list for sync?
          "merge this import data with current data wiith update logic... If car data not have in the imported file, delete all that data"
          Yes, strict sync.
        """
        stats = {"added": 0, "updated": 0, "deleted": 0}
        
        # Prepare import dict for fast lookup by normalized plate
        # Import data might be raw, mapping keys might be needed. 
        # Assuming import_data follows schema or similar keys.
        # But import might come from XLSX/CSV with different headers. 
        # For this logic class, assume standardized input list of dicts.
        
        import_map = {}
        for row in import_data:
            # Flexible key mapping? Assuming keys match valid keys or similar
            # For robustness, let's look for 'plate', 'brand', 'wheel' aliases?
            # Or assume the caller (API) normalizes keys.
            plate = row.get('car_plate') or row.get('plate')
            if not plate: 
                continue
            norm = self.normalize_plate(plate)
            import_map[norm] = row

        current_data = self._read_csv()
        current_map = {self.normalize_plate(c['car_plate']): c for c in current_data}
        
        final_list = []
        
        # Process Import vs Current
        
        # 1. Update Existing and Add New
        for norm_plate, new_row in import_map.items():
            if norm_plate in current_map:
                # Update
                existing = current_map[norm_plate]
                # Update fields
                existing['car_brand'] = str(new_row.get('car_brand', existing['car_brand']))
                existing['car_wheel'] = str(new_row.get('car_wheel', existing['car_wheel']))
                existing['car_volume'] = str(new_row.get('car_volume', existing['car_volume']))
                existing['car_update_date'] = datetime.now().strftime(self.DATE_FORMAT)
                final_list.append(existing)
                stats['updated'] += 1
            else:
                # Add New
                new_car = {
                    "car_id": str(uuid.uuid4()),
                    "car_plate": new_row.get('car_plate', norm_plate),
                    "car_brand": str(new_row.get('car_brand', '')),
                    "car_wheel": str(new_row.get('car_wheel', '')),
                    "car_volume": str(new_row.get('car_volume', '')),
                    "car_register_date": datetime.now().strftime(self.DATE_FORMAT),
                    "car_update_date": datetime.now().strftime(self.DATE_FORMAT)
                }
                final_list.append(new_car)
                stats['added'] += 1

        # 2. Delete Missing
        # Any items in Current Map that were NOT in Import Map are implicitly excluded from final_list.
        # So 'deleted' count is Total Current - (Updated Count).
        # Wait, if we just build final_list from import_map, anything not in import_map is gone.
        stats['deleted'] = len(current_data) - stats['updated']

        self._write_csv(self.current_file, final_list)
        return stats

    def health_check(self) -> Dict[str, Any]:
        exists = self.current_file.exists()
        count = 0
        valid_schema = True
        if exists:
            try:
                data = self._read_csv()
                count = len(data)
                # Check first row for schema
                if data and any(k not in data[0] for k in self.HEADERS):
                    valid_schema = False
            except Exception:
                valid_schema = False
        
        return {
            "file_path": str(self.current_file),
            "exists": exists,
            "row_count": count,
            "valid_schema": valid_schema
        }
