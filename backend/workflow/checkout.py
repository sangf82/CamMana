
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from backend.model_process.control import orchestrator
from backend.data_process.history.logic import HistoryLogic
from backend.data_process.register_car.logic import RegisteredCarLogic

logger = logging.getLogger(__name__)

class CheckOutService:
    def __init__(self):
        self.history_logic = HistoryLogic()
        self.registered_logic = RegisteredCarLogic()
        self.orchestrator = orchestrator

    async def process_checkout(
        self,
        front_image_path: Path,
        location_id: str,
        date_str: Optional[str] = None
    ) -> Dict:
        """
        Process a check-out event.
        - Detect Plate.
        - Find Open Session.
        - Close Session.
        """
        import cv2
        import shutil
        
        try:
            # 1. AI Detection (Plate only usually suffices for checkout)
            front_frame = cv2.imread(str(front_image_path))
            results = await self.orchestrator.process_image(front_frame, ["plate"])
            
            plate_res = results.get("plate", {})
            plate_number = plate_res.get("plate", "Unknown")
            
            # Normalize
            if plate_number != "Unknown":
                clean_plate = self.registered_logic.normalize_plate(plate_number)
            else:
                clean_plate = "Unknown"

            # 2. Find Open Session
            # Look for records with status="Check-In Pending" or similar and matching plate
            # Logic: Last 24-48 hours?
            # Ideally HistoryLogic API supports querying "open" records.
            # Assuming get_records() returns today's. If checkout connects to yesterday's checkin, we need to search back.
            # For MVP/Refactor, search today's file first.
            
            records = self.history_logic.get_records()
            target_record = None
            
            # Search logic: Most recent entry with same plate and no time_out?
            for rec in reversed(records):
                if rec["plate"] == clean_plate and (not rec["time_out"] or rec["time_out"] == "---"):
                    target_record = rec
                    break
            
            # If not found today, search yesterday? (TODO: Enhancement)
            
            # 3. Update Record
            if target_record:
                # Update Time Out
                time_out = datetime.now().strftime("%H:%M:%S")
                self.history_logic.update_record(target_record["id"], {
                    "time_out": time_out,
                    "status": "Check-Out Pending" # or Completed
                })
                status = "Matched"
                uuid_val = target_record["id"]
            else:
                # Create a new record? Or Log error?
                # Usually gate shouldn't open.
                # Create "Checkout without Checkin" record?
                # For now, just Log.
                status = "Unknown Check-In"
                uuid_val = None
                
            # 4. Save Image (Evidence)
            # Existing folder? "folder_path" in target_record.
            # If matched, verify folder exists and save "checkout_front.jpg".
            if target_record and target_record.get("folder_path"):
                folder = Path(target_record["folder_path"])
                if folder.exists():
                    shutil.copy2(front_image_path, folder / "checkout_front.jpg")
            else:
                # Create folder for orphan checkout?
                # Or skip.
                pass
                
            return {
                "success": True,
                "plate": clean_plate,
                "status": status,
                "uuid": uuid_val
            }
            
        except Exception as e:
            logger.error(f"Checkout error: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        pass

def get_checkout_service():
    return CheckOutService()
