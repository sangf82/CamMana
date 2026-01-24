
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
            # Look for records with no time_out across all available history dates
            target_record = self.history_logic.find_open_session(clean_plate)
            
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
                # Create "Checkout without Checkin" record so user can edit later
                import uuid
                new_id = str(uuid.uuid4())
                time_out = datetime.now().strftime("%H:%M:%S")
                
                record_data = {
                    "id": new_id,
                    "plate": clean_plate,
                    "location": location_id,
                    "time_in": "Unknown", # Flag as unknown entry
                    "time_out": time_out,
                    "status": "Unknown Check-In",
                    "verify": "Cần KT",
                    "folder_path": "", # No folder yet
                    "note": "Xe ra không có dữ liệu vào"
                }
                
                # Create folder for evidence if possible
                try:
                    # We can use checkin service folder creation logic if we duplicate it,
                    # or just create a simple folder manually.
                    # reusing logic is better but we are in CheckOutService.
                    # Just create a basic folder.
                    date_folder = datetime.now().strftime("%d-%m-%Y")
                    folder_name = f"{new_id}_{datetime.now().strftime('%H-%M-%S')}"
                    folder_path = HistoryLogic().CAR_HISTORY_DIR / date_folder / folder_name
                    folder_path.mkdir(parents=True, exist_ok=True)
                    record_data["folder_path"] = str(folder_path)
                    
                    if folder_path.exists():
                        shutil.copy2(front_image_path, folder_path / "checkout_front.jpg")
                except Exception as e:
                    logger.error(f"Failed to create evidence folder for unknown checkout: {e}")

                new_rec = self.history_logic.add_record(record_data)
                
                status = "Unknown Check-In"
                uuid_val = new_id
                target_record = new_rec # Assign so below logic works if needed?
                
            # 4. Save Image (Evidence) - Already handled above for new record
            # For existing record:
            if target_record and target_record.get("folder_path") and uuid_val != target_record.get("id"): # differentiate?
                # Actually, if we just created it, we copied content.
                # If it's matched, we copy content.
                pass
            
            # Refined Step 4 for Matched Case
            if target_record and target_record.get("id") != uuid_val: 
                # This condition is tricky. Let's simplify.
                # If we found target_record (matched), we want to save image to ITS folder.
                pass 
            
            # Simpler replacement logic for lines 86-93 to cover both cases cleanly
            if target_record and target_record.get("folder_path"):
                 folder = Path(target_record["folder_path"])
                 if folder.exists():
                     # Check if we already copied it (for new record)
                     if not (folder / "checkout_front.jpg").exists():
                         shutil.copy2(front_image_path, folder / "checkout_front.jpg")
                
            # Try to get history volume (vol_measured from entry)
            history_vol = None
            if target_record and target_record.get("vol_measured"):
                try:
                    history_vol = float(target_record["vol_measured"])
                except:
                    pass

            return {
                "success": True,
                "plate": clean_plate,
                "status": status,
                "uuid": uuid_val,
                "folder_path": target_record.get("folder_path") if target_record else None,
                "history_volume": history_vol
            }
            
        except Exception as e:
            logger.error(f"Checkout error: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        pass

def get_checkout_service():
    return CheckOutService()
