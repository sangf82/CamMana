import asyncio
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from backend.data_process.config import get_locations
from .detection_client import DetectionClient
from .storage_manager import StorageManager, CheckInResult

class CheckInService:
    """
    Orchestrator for vehicle check-in process.
    Delegates API calls to DetectionClient and file ops to StorageManager.
    """
    
    def __init__(self):
        self.detection_client = DetectionClient()
        self.storage_manager = StorageManager()
    
    async def close(self):
        await self.detection_client.close()

    def _resolve_location_id(self, location_name_or_slug: str) -> Optional[str]:
        """Resolves location name/slug to ID"""
        locations = get_locations()
        name_lower = location_name_or_slug.lower().replace("-", " ").replace("_", " ")
        
        # 1. Direct ID match
        for loc in locations:
            if str(loc.id) == location_name_or_slug:
                return str(loc.id)

        # 2. Slug mapping
        mappings = {
            "cong nam": ["cổng nam", "cong nam"],
            "cong bac": ["cổng bắc", "cong bac"],
            "cong dong": ["cổng đông", "cong dong"]
        }

        for loc in locations:
            loc_name = loc.name.lower()
            if name_lower == loc_name:
                return str(loc.id)
            
            # Check mappings
            for key, patterns in mappings.items():
                if name_lower == key or name_lower in patterns:
                    if any(p in loc_name for p in patterns):
                        return str(loc.id)
            
            # Partial match
            if name_lower in loc_name or loc_name in name_lower:
                return str(loc.id)
                
        return None

    async def process_checkin(
        self,
        front_image_path: Path,
        side_image_path: Path,
        location_id: str,
        date_str: Optional[str] = None
    ) -> CheckInResult:
        """
        Orchestrate check-in flow:
        1. Setup storage (folders, copy images)
        2. Run detections (API)
        3. Save results and update history
        """
        if date_str is None:
            date_str = datetime.now().strftime("%d-%m-%Y")

        # 1. Setup Storage
        car_folder, car_uuid, new_front, new_side = self.storage_manager.setup_checkin_folder(
            location_id, date_str, front_image_path, side_image_path
        )
        
        print(f"[CheckIn] Processing {car_uuid}...")

        # 2. Run Detections
        start_time = datetime.now()
        plate_res, color_res, wheel_res = await self.detection_client.run_all_detections(front_image_path, side_image_path)
        duration = (datetime.now() - start_time).total_seconds()
        print(f"[CheckIn] Detections completed in {duration:.2f}s")
        
        # 3. Parse Logic (could be moved to ResultBuilder, but fine here for now)
        plate_number = plate_res.get("plates", [])[0] if plate_res.get("plates") else None
        
        color = None
        color_conf = 0.0
        if color_res.get("detections"):
            best = max(color_res["detections"], key=lambda x: x.get("confidence", 0))
            color = best.get("color")
            color_conf = best.get("confidence", 0)
            
        raw_wheels = wheel_res.get("wheel_count", 0)
        wheel_count = raw_wheels * 2
        wheel_conf = 0.0
        if wheel_res.get("detections"):
            d_confs = [d.get("confidence", 0) for d in wheel_res["detections"]]
            if d_confs:
                wheel_conf = sum(d_confs) / len(d_confs)

        result = CheckInResult(
            uuid=car_uuid,
            location_id=location_id,
            date=date_str,
            folder_path=str(car_folder),
            plate_number=plate_number,
            plate_confidence=0.9 if plate_number else 0.0,
            color=color,
            color_confidence=color_conf,
            wheel_count=wheel_count,
            wheel_confidence=wheel_conf,
            plate_raw=plate_res,
            color_raw=color_res,
            wheel_raw=wheel_res
        )

        # 4. Save results
        self.storage_manager.save_results(car_folder, result)
        
        # 5. Update History
        history_record = self.storage_manager.save_history(result)
        result.history_record = history_record
        
        print(f"[CheckIn] Completed: plate={plate_number}, color={color}, wheels={wheel_count}")
        return result

    async def verify_plate(self, folder_path: str, verified_plate: str, approved: bool = True) -> Dict[str, Any]:
        """Delegate verification to storage manager"""
        return self.storage_manager.verify_plate(folder_path, verified_plate, approved)
    
    async def process_existing_folder(self, folder_path: Path) -> Optional[CheckInResult]:
        """Process existing folder for testing"""
        if not folder_path.exists():
            return None
            
        folder_name = folder_path.name
        parts = folder_name.split("_")
        
        if len(parts) >= 3:
            location_slug = parts[1]
            date_str = "_".join(parts[2:])
        else:
            return None
            
        front_images = list(folder_path.glob("*front*.jpg")) + list(folder_path.glob("*front*.jpeg"))
        side_images = list(folder_path.glob("*side*.jpg")) + list(folder_path.glob("*side*.jpeg"))
        
        if not front_images or not side_images:
            return None
            
        location_id = self._resolve_location_id(location_slug) or location_slug
        
        return await self.process_checkin(
            front_images[0],
            side_images[0],
            location_id,
            date_str.replace("_", "-")
        )

# Singleton
_checkin_service: Optional[CheckInService] = None

def get_checkin_service() -> CheckInService:
    global _checkin_service
    if _checkin_service is None:
        _checkin_service = CheckInService()
    return _checkin_service

__all__ = ['CheckInService', 'CheckInResult', 'get_checkin_service']
