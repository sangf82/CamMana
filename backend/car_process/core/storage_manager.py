import shutil
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple, Any, List
from dataclasses import dataclass, field

import backend.data_process as storage
from backend.data_process.config import get_locations, get_cam_types

# Car History Directory
CAR_HISTORY_DIR = Path("database/car_history")

@dataclass
class CheckInResult:
    """Result of a check-in processing"""
    uuid: str
    location_id: str
    date: str
    folder_path: str
    
    # Detection results
    plate_number: Optional[str] = None
    plate_confidence: float = 0.0
    color: Optional[str] = None
    color_confidence: float = 0.0
    wheel_count: int = 0  # Already x2
    wheel_confidence: float = 0.0
    
    # Status
    status: str = "pending_verification"  # pending_verification, verified, rejected
    verified_plate: Optional[str] = None
    
    # Raw API responses
    plate_raw: Dict = field(default_factory=dict)
    color_raw: Dict = field(default_factory=dict)
    wheel_raw: Dict = field(default_factory=dict)
    
    # Saved history record
    history_record: Optional[Dict] = None

class StorageManager:
    """Manages file storage and history records for vehicle check-ins"""
    
    def __init__(self):
        CAR_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    def generate_folder_name(self, location_id: str, date_str: str) -> Tuple[str, str]:
        """Generate folder name: uuid_location-id_date. Returns (folder_name, uuid)"""
        car_uuid = str(uuid.uuid4())
        folder_name = f"{car_uuid}_{location_id}_{date_str}"
        return folder_name, car_uuid
    
    def generate_image_name(self, car_uuid: str, camtype_id: str, date_str: str) -> str:
        """Generate image name: uuid_camtype-id_date.jpg"""
        return f"{car_uuid}_{camtype_id}_{date_str}.jpg"

    def _get_camtype_id(self, cam_type: str) -> str:
        """Get best matching camera type ID"""
        cam_types = get_cam_types()
        for ct in cam_types:
            functions = (ct.functions or "").lower()
            if cam_type == "front" and "plate" in functions:
                return str(ct.id)
            elif cam_type == "side" and ("color" in functions or "wheel" in functions):
                return str(ct.id)
        return str(cam_types[0].id) if cam_types else "unknown"

    def _get_location_name(self, location_id: str) -> str:
        """Resolve location name from ID"""
        locations = get_locations()
        for loc in locations:
            if str(loc.id) == str(location_id):
                return loc.name
        return location_id

    def setup_checkin_folder(self, location_id: str, date_str: str, front_src: Path, side_src: Path) -> Tuple[Path, str, Path, Path]:
        """
        Creates the folder structure and copies images.
        Returns: (car_folder_path, car_uuid, new_front_path, new_side_path)
        """
        folder_name, car_uuid = self.generate_folder_name(location_id, date_str)
        date_folder = CAR_HISTORY_DIR / date_str
        car_folder = date_folder / folder_name
        car_folder.mkdir(parents=True, exist_ok=True)

        front_id = self._get_camtype_id("front")
        side_id = self._get_camtype_id("side")

        new_front_name = self.generate_image_name(car_uuid, front_id, date_str)
        new_side_name = self.generate_image_name(car_uuid, side_id, date_str)
        
        new_front_path = car_folder / new_front_name
        new_side_path = car_folder / new_side_name
        
        shutil.copy2(front_src, new_front_path)
        shutil.copy2(side_src, new_side_path)
        
        return car_folder, car_uuid, new_front_path, new_side_path

    def save_results(self, folder: Path, result: CheckInResult):
        """Save detection results and status to JSON files in the folder"""
        # Save separate JSONs
        with open(folder / "plate_result.json", "w", encoding="utf-8") as f:
            json.dump(result.plate_raw, f, indent=2, ensure_ascii=False)
        
        with open(folder / "color_result.json", "w", encoding="utf-8") as f:
            json.dump(result.color_raw, f, indent=2, ensure_ascii=False)
            
        with open(folder / "wheel_result.json", "w", encoding="utf-8") as f:
            wheel_data = result.wheel_raw.copy()
            wheel_data["wheel_count_x2"] = result.wheel_count
            json.dump(wheel_data, f, indent=2, ensure_ascii=False)

        # Save aggregated status
        status_data = {
            "uuid": result.uuid,
            "location_id": result.location_id,
            "date": result.date,
            "folder_path": str(folder),
            "plate_number": result.plate_number,
            "plate_confidence": result.plate_confidence,
            "color": result.color,
            "color_confidence": result.color_confidence,
            "wheel_count": result.wheel_count,
            "wheel_confidence": result.wheel_confidence,
            "status": result.status,
            "created_at": datetime.now().isoformat()
        }
        with open(folder / "checkin_status.json", "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)

    def save_history(self, result: CheckInResult) -> Dict[str, Any]:
        """Save to global history CSV"""
        location_name = self._get_location_name(result.location_id)
        
        history_record = {
            "plate": result.plate_number or f"[PENDING:{result.uuid[:8]}]",
            "location": location_name,
            "time_in": datetime.now().strftime("%H:%M:%S"),
            "time_out": "---",
            "vol_std": "",
            "vol_measured": "",
            "status": result.status,
            "verify": "❌ Chưa xác minh" if result.status == "pending_verification" else "✅ Đã xác minh",
            "note": f"Màu: {result.color or 'N/A'} | Bánh: {result.wheel_count}"
        }
        
        storage.save_history_record(history_record, result.date.replace("-", "_"))
        return history_record

    def verify_plate(self, folder_path: str, verified_plate: str, approved: bool) -> Dict[str, Any]:
        """Handle renaming and status update for verification"""
        folder = Path(folder_path)
        if not folder.exists():
            return {"success": False, "error": "Folder not found"}
        
        status_file = folder / "checkin_status.json"
        if not status_file.exists():
            return {"success": False, "error": "Status file not found"}
            
        with open(status_file, "r", encoding="utf-8") as f:
            status = json.load(f)
            
        old_uuid = status["uuid"]
        
        # Update status logic
        status["status"] = "verified" if approved else "rejected"
        status["verified_plate"] = verified_plate
        status["verified_at"] = datetime.now().isoformat()
        
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
            
        # Rename logic if approved
        if approved and verified_plate:
            try:
                # Rename images
                for img in folder.glob("*.jpg"):
                    new_name = img.name.replace(old_uuid, verified_plate)
                    img.rename(folder / new_name)
                
                # Rename folder
                new_folder_name = folder.name.replace(old_uuid, verified_plate)
                new_folder_path = folder.parent / new_folder_name
                folder.rename(new_folder_path)
                
                # Update path in status file
                status["folder_path"] = str(new_folder_path)
                with open(new_folder_path / "checkin_status.json", "w", encoding="utf-8") as f:
                    json.dump(status, f, indent=2, ensure_ascii=False)
                    
                return {
                    "success": True, 
                    "old_path": str(folder), 
                    "new_path": str(new_folder_path),
                    "verified_plate": verified_plate
                }
            except Exception as e:
                return {"success": False, "error": f"Renaming failed: {str(e)}"}
                
        return {"success": True, "folder_path": str(folder)}
