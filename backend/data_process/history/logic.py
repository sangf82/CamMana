
import csv
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import uuid

from backend.config import DATA_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

class HistoryLogic:
    HEADERS = [
        "id", "plate", "location", "time_in", "time_out", 
        "vol_std", "vol_measured", "status", "verify", "note", "folder_path"
    ]
    DATE_FORMAT = "%d-%m-%Y"
    FILE_PREFIX = "history_"
    
    # Folder for storing images/logs per car interaction
    CAR_HISTORY_DIR = PROJECT_ROOT / "database" / "car_history"

    def __init__(self):
        self._ensure_dirs()
        self.refresh_state()

    def refresh_state(self):
        new_today = datetime.now().strftime(self.DATE_FORMAT)
        if not hasattr(self, 'today') or self.today != new_today:
            self.today = new_today
            self.current_file = DATA_DIR / f"{self.FILE_PREFIX}{self.today}.csv"
            self.rotate_daily_file()

    def _ensure_dirs(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.CAR_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    def _get_file_date(self, filename: str) -> Optional[datetime]:
        try:
            date_str = filename.replace(self.FILE_PREFIX, "").replace(".csv", "")
            return datetime.strptime(date_str, self.DATE_FORMAT)
        except ValueError:
            return None

    def rotate_daily_file(self):
        """
        Create today's file if missing.
        Delete files older than 2 days (48 hours).
        """
        # 1. Create today's file if missing
        if not self.current_file.exists():
            self._write_csv(self.current_file, [])
            logger.info(f"Created new history file {self.current_file.name}")

        # 2. Cleanup old files
        limit_date = datetime.now() - timedelta(hours=48)
        
        for f in DATA_DIR.glob(f"{self.FILE_PREFIX}*.csv"):
            d = self._get_file_date(f.name)
            if d and d < limit_date:
                try:
                    f.unlink()
                    logger.info(f"Deleted old history file {f.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {f.name}: {e}")

        # 3. Cleanup old car folders
        self.cleanup_expired_folders(limit_date)

    def cleanup_expired_folders(self, limit_date: datetime):
        """
        Delete car history folders older than limit_date.
        Path format: database/car_history/dd-mm-yyyy/uuid_hh-mm-ss
        """
        if not self.CAR_HISTORY_DIR.exists():
            return

        count = 0
        limit_day = limit_date.date()

        for date_folder in self.CAR_HISTORY_DIR.iterdir():
            if not date_folder.is_dir():
                continue
            
            try:
                # Folder name: DD-MM-YYYY
                folder_date = datetime.strptime(date_folder.name, self.DATE_FORMAT).date()
                
                if folder_date < limit_day:
                    shutil.rmtree(date_folder)
                    logger.info(f"Deleted expired date folder: {date_folder.name}")
                    count += 1
            except ValueError:
                # Not a date folder folder, skip
                continue
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired car history day folders")
        
    def _read_csv(self, file_path: Path = None) -> List[Dict[str, str]]:
        target = file_path if file_path else self.current_file
        if not target.exists():
            return []
        with open(target, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_csv(self, path: Path, data: List[Dict[str, str]]):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(data)

    def get_records(self, date_str: Optional[str] = None) -> List[Dict[str, str]]:
        self.refresh_state()
        if date_str:
            target_file = DATA_DIR / f"{self.FILE_PREFIX}{date_str}.csv"
        else:
            target_file = self.current_file
            
        return self._read_csv(target_file)

    def get_available_dates(self) -> List[str]:
        self.refresh_state()
        files = list(DATA_DIR.glob(f"{self.FILE_PREFIX}*.csv"))
        date_objs = []
        for f in files:
            d = self._get_file_date(f.name)
            if d:
                date_objs.append(d)
        
        # Sort chronologically, newest first
        date_objs.sort(reverse=True)
        return [d.strftime(self.DATE_FORMAT) for d in date_objs]

    def create_car_folder(self, record_id: str) -> Path:
        """
        Create a folder for the car interaction: car_history/dd-mm-yyyy/uuid_hh-mm-ss
        """
        date_folder_name = datetime.now().strftime(self.DATE_FORMAT)
        time_suffix = datetime.now().strftime("%H-%M-%S") # Use - for safety in paths
        
        folder_name = f"{record_id}_{time_suffix}"
        
        date_folder_path = self.CAR_HISTORY_DIR / date_folder_name
        date_folder_path.mkdir(parents=True, exist_ok=True)
        
        folder_path = date_folder_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path

    def add_record(self, record_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Add a new record to today's history.
        """
        self.refresh_state()
        current_data = self._read_csv()
        
        # If folder_path is not provided, maybe create it?
        # The caller (Workflow) usually orchestrates creation. 
        # But if passed blank, we can create one.
        folder_path = record_data.get("folder_path", "")
        if not folder_path and record_data.get("plate"):
             # Optional: auto create? For now trust caller or leave empty.
             pass

        new_record = {
            "id": record_data.get("id", str(uuid.uuid4())), # Ensure ID exists
            "plate": record_data.get("plate", "Unknown"),
            "location": record_data.get("location", ""),
            "time_in": record_data.get("time_in", datetime.now().strftime("%H:%M:%S")),
            "time_out": record_data.get("time_out", "---"),
            "vol_std": str(record_data.get("vol_std", "")),
            "vol_measured": str(record_data.get("vol_measured", "")),
            "status": record_data.get("status", "Processing"),
            "verify": record_data.get("verify", ""),
            "note": record_data.get("note", ""),
            "folder_path": str(folder_path)
        }
        
        # Validate keys against headers (ignore extras)
        clean_record = {k: new_record.get(k, "") for k in self.HEADERS}
        
        current_data.append(clean_record)
        self._write_csv(self.current_file, current_data)
        return clean_record

    def update_record(self, record_id: str, update_data: Dict[str, Any], date_str: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Update a record by ID. Searches across all available files if date_str is not provided.
        """
        if date_str:
            dates_to_check = [date_str]
        else:
            dates_to_check = self.get_available_dates()
            
        for d in dates_to_check:
            target_file = DATA_DIR / f"{self.FILE_PREFIX}{d}.csv"
            if not target_file.exists():
                continue
                
            current_data = self._read_csv(target_file)
            updated_rec = None
            for rec in current_data:
                if rec["id"] == record_id:
                    for k, v in update_data.items():
                        if k in self.HEADERS:
                            rec[k] = str(v)
                    updated_rec = rec
                    break
            
            if updated_rec:
                self._write_csv(target_file, current_data)
                return updated_rec
                
        return None

    def find_open_session(self, plate: str) -> Optional[Dict[str, str]]:
        """
        Find the most recent open session (no time_out) for a given plate.
        Robust matching using normalized plate comparison.
        """
        import re
        def normalize_p(p): return re.sub(r'[^a-zA-Z0-9]', '', str(p)).upper()
        
        search_plate = normalize_p(plate)
        if not search_plate or search_plate == "UNKNOWN":
            return None

        dates = self.get_available_dates()
        for d in dates:
            target_file = DATA_DIR / f"{self.FILE_PREFIX}{d}.csv"
            if not target_file.exists(): continue
            
            records = self._read_csv(target_file)
            # Search newest to oldest within file
            for rec in reversed(records):
                # Robust match: normalize plate from record too
                rec_plate = normalize_p(rec.get("plate", ""))
                time_out = rec.get("time_out", "")
                
                # An open session has no time_out value or "---"
                is_open = not time_out or time_out == "---"
                
                if rec_plate == search_plate and is_open:
                    return rec
        return None

    def delete_record(self, record_id: str) -> bool:
        """
        Delete a record by ID.
        """
        dates = self.get_available_dates()
        for d in dates:
            target_file = DATA_DIR / f"{self.FILE_PREFIX}{d}.csv"
            if not target_file.exists(): continue
            
            current_data = self._read_csv(target_file)
            initial_len = len(current_data)
            current_data = [r for r in current_data if r["id"] != record_id]
            
            if len(current_data) < initial_len:
                self._write_csv(target_file, current_data)
                return True
        return False

