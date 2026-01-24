
import logging
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.model_process.control import orchestrator
from backend.data_process.history.logic import HistoryLogic
from backend.data_process.register_car.logic import RegisteredCarLogic
from backend.workflow.config import get_location_strategy, LocationTag

logger = logging.getLogger(__name__)

class CheckInResult:
    def __init__(self, **kwargs):
        self.uuid = kwargs.get("uuid", str(uuid.uuid4()))
        self.folder_path = kwargs.get("folder_path", "")
        self.plate_number = kwargs.get("plate_number", "")
        self.plate_confidence = kwargs.get("plate_confidence", 0.0)
        self.color = kwargs.get("color", "Unknown")
        self.color_confidence = kwargs.get("color_confidence", 0.0)
        self.wheel_count = kwargs.get("wheel_count", 0)
        self.wheel_confidence = kwargs.get("wheel_confidence", 0.0)
        self.status = kwargs.get("status", "Processing")
        self.history_record = kwargs.get("history_record", {})

class CheckInService:
    def __init__(self):
        self.history_logic = HistoryLogic()
        self.registered_logic = RegisteredCarLogic()
        self.orchestrator = orchestrator

    async def process_checkin(
        self,
        front_image_path: Path,
        side_image_path: Path,
        location_id: str,
        date_str: Optional[str] = None
    ) -> CheckInResult:
        """
        Process a check-in event.
        - Run AI Detection.
        - Create Folder.
        - Save Data.
        """
        try:
            # 1. AI Detection
            # Determine functions based on location location_id?
            # Assuming location_id correlates to a tag, or we use standard CheckIn strategy.
            # Ideally we look up location tag by ID. 
            # For now, default to GATE_IN strategy functions: Plate, Truck, Color, Wheels(if side present)
            
            functions = ["plate", "truck", "color"]
            if side_image_path and side_image_path.exists():
                functions.append("wheel")
            
            # We process FRONT image for Plate, Truck, Color
            # We process SIDE image for Wheel
            
            # Helper to read cv2 frame? Orchestrator expects frame.
            import cv2
            import numpy as np
            
            front_frame = cv2.imread(str(front_image_path))
            side_frame = cv2.imread(str(side_image_path)) if side_image_path else None
            
            # Parallel calls
            # Front functions
            front_funcs = ["plate", "truck", "color"]
            front_task = self.orchestrator.process_image(front_frame, front_funcs)
            
            # Side functions
            side_funcs = ["wheel"]
            side_task = self.orchestrator.process_image(side_frame, side_funcs) if side_frame else None
            
            results = await front_task
            side_results = await side_task if side_task else {}
            results.update(side_results)
            
            # Extract Data
            plate_res = results.get("plate", {})
            plate_number = plate_res.get("plate", "Unknown")
            plate_conf = plate_res.get("confidence", 0.0) # Might not be available in simple dict
            
            color_res = results.get("color", {})
            primary_color = color_res.get("primary_color", "Unknown")
            
            wheel_res = results.get("wheel", {})
            wheel_count = wheel_res.get("wheel_count_total", 0)
            
            # 2. Check Registration
            # Use RegisteredCarLogic
            is_registered = False
            # registered_cars = self.registered_logic.get_all_cars()
            # For simplicity, just store raw data for verification step
            
            # 3. Create Folder and Save History
            # If plate is Unknown, use Unknown_{uuid}
            clean_plate = self.registered_logic.normalize_plate(plate_number) if plate_number != "Unknown" else f"Unknown_{uuid.uuid4().hex[:4]}"
            
            folder_path = self.history_logic.create_car_folder(clean_plate)
            
            # Copy images to folder
            if front_image_path.exists():
                shutil.copy2(front_image_path, folder_path / "front.jpg")
            if side_image_path and side_image_path.exists():
                shutil.copy2(side_image_path, folder_path / "side.jpg")
            
            # 4. Create History Record
            record_data = {
                "plate": clean_plate,
                "location": location_id, # or name
                "status": "Check-In Pending",
                "folder_path": str(folder_path),
                "vol_std": "", # Fill from registration later
                "vol_measured": ""
            }
            record = self.history_logic.add_record(record_data)
            
            # 5. Save CheckIn Status JSON (for UI/Pending flow)
            status_data = {
                "uuid": record.get("id"),
                "plate_number": clean_plate,
                "color": primary_color,
                "wheel_count": wheel_count,
                "status": "pending_verification", # "pending_verification" triggers UI
                "folder_path": str(folder_path),
                "created_at": datetime.now().isoformat(),
                "ai_results": {k: v for k, v in results.items() if k != "raw"}
            }
            
            status_file = folder_path / "checkin_status.json"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=4)
            
            return CheckInResult(
                uuid=record.get("id"),
                folder_path=str(folder_path),
                plate_number=clean_plate,
                color=primary_color,
                wheel_count=wheel_count,
                status="pending_verification",
                history_record=record
            )

        except Exception as e:
            logger.error(f"Processing checkin failed: {e}", exc_info=True)
            raise e

    async def verify_plate(self, folder_path: str, verified_plate: str, approved: bool) -> Dict:
        """
        Verify/Correction step.
        """
        path = Path(folder_path)
        if not path.exists():
            raise FileNotFoundError("Folder not found")
        
        status_file = path / "checkin_status.json"
        
        # Determine Status
        status = "Verified" if approved else "Rejected"
        
        # Logic: 
        # 1. Update JSON
        # 2. Update History Record (CSV)
        # 3. Rename Folder if plate changed? (Tricky if files locked, usually keep folder name or rename carefully)
        # For simplicity, keep folder name but update metadata.
        
        uuid_val = ""
        current_data = {}
        if status_file.exists():
            with open(status_file, "r") as f:
                current_data = json.load(f)
                uuid_val = current_data.get("uuid")
        
        # Update History CSV
        if uuid_val:
            self.history_logic.update_record(uuid_val, {
                "plate": verified_plate,
                "status": status,
                "verify": "Manual"
            })
            
        # Update JSON
        current_data["status"] = "verified" if approved else "rejected"
        current_data["verified_plate"] = verified_plate
        
        with open(status_file, "w") as f:
            json.dump(current_data, f, indent=4)
            
        return {"success": True, "status": status, "plate": verified_plate}

    async def close(self):
        pass

def get_checkin_service():
    return CheckInService()
