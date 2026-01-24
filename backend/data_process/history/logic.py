
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
        self.today = datetime.now().strftime(self.DATE_FORMAT)
        self.current_file = DATA_DIR / f"{self.FILE_PREFIX}{self.today}.csv"
        self._ensure_dirs()
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
        Folder name format: {plate}_{YYYYMMDD}_{HHMMSS}
        """
        if not self.CAR_HISTORY_DIR.exists():
            return

        count = 0
        for folder in self.CAR_HISTORY_DIR.iterdir():
            if not folder.is_dir():
                continue
            
            # Try to parse date from folder name
            # Format: *_YYYYMMDD_HHMMSS
            try:
                parts = folder.name.split('_')
                if len(parts) >= 3:
                    date_str = parts[-2]
                    time_str = parts[-1]
                    folder_dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    
                    if folder_dt < limit_date:
                        shutil.rmtree(folder)
                        logger.info(f"Deleted expired car folder {folder.name}")
                        count += 1
            except Exception as e:
                logger.warning(f"Skipping folder cleanup for {folder.name}: {e}")
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired car history folders")
        
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
        if date_str:
            target_file = DATA_DIR / f"{self.FILE_PREFIX}{date_str}.csv"
        else:
            target_file = self.current_file
            
        return self._read_csv(target_file)

    def get_available_dates(self) -> List[str]:
        files = list(DATA_DIR.glob(f"{self.FILE_PREFIX}*.csv"))
        dates = []
        for f in files:
            d = self._get_file_date(f.name)
            if d:
                dates.append(d.strftime(self.DATE_FORMAT))
        dates.sort(reverse=True)
        return dates

    def create_car_folder(self, plate: str) -> Path:
        """
        Create a folder for the car interaction: car_history/{plate}_{timestamp}
        """
        timestamp = datetime.now().strftime("%H%M%S") # Just time? Or date_time?
        # Folder structure usually keeps grouping. Maybe by Date/Plate?
        # Requirement: "folder for each car within the @directory:car_history folder"
        # Let's use {plate}_{date}_{time} for uniqueness
        folder_name = f"{plate}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        folder_path = self.CAR_HISTORY_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path

    def add_record(self, record_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Add a new record to today's history.
        """
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

    def update_record(self, record_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        current_data = self._read_csv()
        updated = None
        
        for rec in current_data:
            if rec["id"] == record_id:
                for k, v in update_data.items():
                    if k in self.HEADERS:
                        rec[k] = str(v)
                updated = rec
                break
        
        if updated:
            self._write_csv(self.current_file, current_data)
            return updated
        return None

