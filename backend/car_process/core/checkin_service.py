"""
Check-In Service - Processes car check-in using external AI APIs

Handles:
1. Plate detection (ALPR) from front camera
2. Color detection from side camera  
3. Wheel counting from side camera (x2 for full vehicle)
4. Saving results and updating history
5. Human verification flow

File naming convention:
- Folder: uuid_location-id_date
- Images: uuid_camtype-id_date.jpg
"""
import httpx
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

import backend.data_process as storage
from backend.data_process.config import get_locations, get_cam_types

# External API Configuration
API_BASE_URL = "https://thpttl12t1--truck-api-fastapi-app.modal.run"
API_TIMEOUT = 30.0

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


class CheckInService:
    """Service for processing vehicle check-ins"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        CAR_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=API_TIMEOUT)
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_location_id_from_name(self, location_name: str) -> Optional[str]:
        """Get location ID from location name/slug
        
        Maps:
        - 'cong-nam', 'cong nam', 'Cổng Nam' -> 1768207201391
        - 'cong-bac', 'cong bac', 'Cổng Bắc' -> 1768207215054
        - 'cong-dong', 'cong dong', 'Cổng Đông' -> 1768207221305
        """
        locations = get_locations()
        location_name_lower = location_name.lower().replace("-", " ").replace("_", " ")
        
        # Mapping from common slugs to Vietnamese names
        slug_mappings = {
            "cong nam": ["cổng nam", "cong nam"],
            "cong bac": ["cổng bắc", "cong bac"],
            "cong dong": ["cổng đông", "cong dong"],
        }
        
        for loc in locations:
            loc_name_lower = loc.name.lower()
            
            # Direct match
            if location_name_lower == loc_name_lower:
                return str(loc.id)
            
            # Check if the input matches any known slug pattern
            for key, patterns in slug_mappings.items():
                if location_name_lower == key or location_name_lower in patterns:
                    # Check if this location matches the pattern
                    if any(p in loc_name_lower for p in patterns):
                        return str(loc.id)
            
            # Partial match
            if location_name_lower in loc_name_lower or loc_name_lower in location_name_lower:
                return str(loc.id)
        
        # Return None if no match found - caller should handle this
        return None
    
    def _get_camtype_id(self, cam_type: str) -> str:
        """Get camera type ID based on function (front/side)
        
        Maps:
        - 'front' -> 1768207190747 (plate detect)
        - 'side' -> 1768207191619 (color/wheel detect)
        """
        cam_types = get_cam_types()
        
        for ct in cam_types:
            functions = ct.functions.lower() if ct.functions else ""
            # front cam -> plate detect, side cam -> color/wheel detect
            if cam_type == "front" and "plate" in functions:
                return str(ct.id)
            elif cam_type == "side" and ("color" in functions or "wheel" in functions):
                return str(ct.id)
        
        # Fallback: return first matching or first available
        if cam_types:
            return str(cam_types[0].id)
        return "unknown"
    
    def _get_location_name_from_id_or_slug(self, location_id_or_slug: str) -> str:
        """Get proper location name from ID or slug
        
        Can handle:
        - Numeric IDs: '1768207201391' -> 'Cổng Nam'
        - Slugs: 'cong-nam' -> 'Cổng Nam'
        """
        locations = get_locations()
        input_lower = location_id_or_slug.lower().replace("-", " ").replace("_", " ")
        
        # First try direct ID match
        for loc in locations:
            if str(loc.id) == str(location_id_or_slug):
                return loc.name
        
        # Mapping from common slugs to Vietnamese names
        slug_mappings = {
            "cong nam": "cổng nam",
            "cong bac": "cổng bắc",
            "cong dong": "cổng đông",
        }
        
        # Try slug match
        for loc in locations:
            loc_name_lower = loc.name.lower()
            
            # Direct name match
            if input_lower == loc_name_lower:
                return loc.name
            
            # Check slug mappings
            for slug, viet_name in slug_mappings.items():
                if input_lower == slug and viet_name in loc_name_lower:
                    return loc.name
            
            # Partial match
            if input_lower in loc_name_lower or loc_name_lower in input_lower:
                return loc.name
        
        # Fallback: return the original input
        return location_id_or_slug
    
    def generate_folder_name(self, location_id: str, date_str: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate folder name: uuid_location-id_date
        Returns: (folder_name, uuid)
        """
        car_uuid = str(uuid.uuid4())
        if date_str is None:
            date_str = datetime.now().strftime("%d-%m-%Y")
        
        folder_name = f"{car_uuid}_{location_id}_{date_str}"
        return folder_name, car_uuid
    
    def generate_image_name(self, car_uuid: str, camtype_id: str, date_str: Optional[str] = None) -> str:
        """
        Generate image name: uuid_camtype-id_date.jpg
        """
        if date_str is None:
            date_str = datetime.now().strftime("%d-%m-%Y")
        return f"{car_uuid}_{camtype_id}_{date_str}.jpg"
    
    async def detect_plate(self, image_path: Path) -> Dict[str, Any]:
        """Call ALPR API to detect license plate"""
        try:
            with open(image_path, "rb") as f:
                files = {"file": (image_path.name, f, "image/jpeg")}
                response = await self.client.post(
                    f"{API_BASE_URL}/alpr",
                    files=files
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e), "plates": [], "count": 0}
    
    async def detect_color(self, image_path: Path) -> Dict[str, Any]:
        """Call color detection API"""
        try:
            with open(image_path, "rb") as f:
                files = {"file": (image_path.name, f, "image/jpeg")}
                response = await self.client.post(
                    f"{API_BASE_URL}/detect_colors",
                    files=files
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e), "detections": []}
    
    async def detect_wheels(self, image_path: Path) -> Dict[str, Any]:
        """Call wheel counting API"""
        try:
            with open(image_path, "rb") as f:
                files = {"file": (image_path.name, f, "image/jpeg")}
                response = await self.client.post(
                    f"{API_BASE_URL}/count_wheels",
                    files=files
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e), "wheel_count": 0, "detections": []}
    
    async def process_checkin(
        self,
        front_image_path: Path,
        side_image_path: Path,
        location_id: str,
        date_str: Optional[str] = None
    ) -> CheckInResult:
        """
        Process a vehicle check-in with both images
        
        1. Detect plate from front image
        2. Detect color from side image
        3. Count wheels from side image (x2 for full vehicle)
        4. Save results to folder
        5. Create history record with pending status
        """
        if date_str is None:
            date_str = datetime.now().strftime("%d-%m-%Y")
        
        # Generate folder
        folder_name, car_uuid = self.generate_folder_name(location_id, date_str)
        
        # Create date folder and car folder
        date_folder = CAR_HISTORY_DIR / date_str
        car_folder = date_folder / folder_name
        car_folder.mkdir(parents=True, exist_ok=True)
        
        # Get camtype IDs
        front_camtype_id = self._get_camtype_id("front")
        side_camtype_id = self._get_camtype_id("side")
        
        # Copy images with new naming convention
        new_front_name = self.generate_image_name(car_uuid, front_camtype_id, date_str)
        new_side_name = self.generate_image_name(car_uuid, side_camtype_id, date_str)
        
        new_front_path = car_folder / new_front_name
        new_side_path = car_folder / new_side_name
        
        shutil.copy2(front_image_path, new_front_path)
        shutil.copy2(side_image_path, new_side_path)
        
        # Run all detections
        print(f"[CheckIn] Processing {car_uuid}...")
        print(f"[CheckIn] Detecting plate from: {front_image_path}")
        plate_result = await self.detect_plate(front_image_path)
        
        print(f"[CheckIn] Detecting color from: {side_image_path}")
        color_result = await self.detect_color(side_image_path)
        
        print(f"[CheckIn] Counting wheels from: {side_image_path}")
        wheel_result = await self.detect_wheels(side_image_path)
        
        # Parse results
        plate_number = None
        plate_confidence = 0.0
        if plate_result.get("plates") and len(plate_result["plates"]) > 0:
            plate_number = plate_result["plates"][0]
            # Try to extract confidence from raw_results if available
            plate_confidence = 0.9  # Default high confidence if plate found
        
        color = None
        color_confidence = 0.0
        if color_result.get("detections") and len(color_result["detections"]) > 0:
            # Get the detection with highest confidence
            best_detection = max(color_result["detections"], key=lambda x: x.get("confidence", 0))
            color = best_detection.get("color")
            color_confidence = best_detection.get("confidence", 0)
        
        # Wheel count x2 (side image shows one side only)
        raw_wheel_count = wheel_result.get("wheel_count", 0)
        wheel_count = raw_wheel_count * 2
        wheel_confidence = 0.0
        if wheel_result.get("detections") and len(wheel_result["detections"]) > 0:
            wheel_confidence = sum(d.get("confidence", 0) for d in wheel_result["detections"]) / len(wheel_result["detections"])
        
        # Save API results as JSON
        with open(car_folder / "plate_result.json", "w", encoding="utf-8") as f:
            json.dump(plate_result, f, indent=2, ensure_ascii=False)
        
        with open(car_folder / "color_result.json", "w", encoding="utf-8") as f:
            json.dump(color_result, f, indent=2, ensure_ascii=False)
        
        with open(car_folder / "wheel_result.json", "w", encoding="utf-8") as f:
            # Store original count and doubled count
            wheel_result["wheel_count_x2"] = wheel_count
            json.dump(wheel_result, f, indent=2, ensure_ascii=False)
        
        # Create result object
        result = CheckInResult(
            uuid=car_uuid,
            location_id=location_id,
            date=date_str,
            folder_path=str(car_folder),
            plate_number=plate_number,
            plate_confidence=plate_confidence,
            color=color,
            color_confidence=color_confidence,
            wheel_count=wheel_count,
            wheel_confidence=wheel_confidence,
            status="pending_verification",
            plate_raw=plate_result,
            color_raw=color_result,
            wheel_raw=wheel_result
        )
        
        # Save check-in status
        status_data = {
            "uuid": car_uuid,
            "location_id": location_id,
            "date": date_str,
            "folder_path": str(car_folder),
            "plate_number": plate_number,
            "plate_confidence": plate_confidence,
            "color": color,
            "color_confidence": color_confidence,
            "wheel_count": wheel_count,
            "wheel_confidence": wheel_confidence,
            "status": "pending_verification",
            "created_at": datetime.now().isoformat()
        }
        
        with open(car_folder / "checkin_status.json", "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        
        # Save to history with pending status
        self._save_to_history(result)
        
        print(f"[CheckIn] Completed: plate={plate_number}, color={color}, wheels={wheel_count}")
        return result
    
    def _save_to_history(self, result: CheckInResult):
        """Save check-in result to history CSV"""
        # Get proper location name from ID or slug
        location_name = self._get_location_name_from_id_or_slug(result.location_id)
        
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
    
    async def verify_plate(
        self,
        folder_path: str,
        verified_plate: str,
        approved: bool = True
    ) -> Dict[str, Any]:
        """
        Human verification of plate number
        
        1. Update the status in checkin_status.json
        2. Rename folder and files to use plate number instead of UUID
        3. Update history record
        """
        folder = Path(folder_path)
        if not folder.exists():
            return {"success": False, "error": "Folder not found"}
        
        # Read current status
        status_file = folder / "checkin_status.json"
        if not status_file.exists():
            return {"success": False, "error": "Status file not found"}
        
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        
        old_uuid = status_data["uuid"]
        location_id = status_data["location_id"]
        date_str = status_data["date"]
        
        # Update status
        status_data["status"] = "verified" if approved else "rejected"
        status_data["verified_plate"] = verified_plate
        status_data["verified_at"] = datetime.now().isoformat()
        
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        
        # Rename files and folder if approved
        if approved and verified_plate:
            # Rename images: replace UUID with plate number
            for img_file in folder.glob("*.jpg"):
                new_name = img_file.name.replace(old_uuid, verified_plate)
                img_file.rename(folder / new_name)
            
            # Rename folder
            new_folder_name = folder.name.replace(old_uuid, verified_plate)
            new_folder_path = folder.parent / new_folder_name
            folder.rename(new_folder_path)
            
            # Update status file path in the moved folder
            new_status_file = new_folder_path / "checkin_status.json"
            with open(new_status_file, "r", encoding="utf-8") as f:
                updated_data = json.load(f)
            updated_data["folder_path"] = str(new_folder_path)
            with open(new_status_file, "w", encoding="utf-8") as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "old_path": str(folder),
                "new_path": str(new_folder_path),
                "verified_plate": verified_plate
            }
        
        return {
            "success": True,
            "status": status_data["status"],
            "folder_path": str(folder)
        }
    
    async def process_existing_folder(self, folder_path: Path) -> Optional[CheckInResult]:
        """
        Process an existing test folder with front and side images
        Used for testing with existing data
        """
        if not folder_path.exists():
            return None
        
        # Parse folder name to extract info
        # Expected format: uuid_location-slug_date
        folder_name = folder_path.name
        parts = folder_name.split("_")
        
        if len(parts) >= 3:
            existing_uuid = parts[0]
            location_slug = parts[1]
            date_str = "_".join(parts[2:])  # Handle dates like 15-01-2026
        else:
            return None
        
        # Find front and side images
        front_images = list(folder_path.glob("*front*.jpg")) + list(folder_path.glob("*front*.jpeg"))
        side_images = list(folder_path.glob("*side*.jpg")) + list(folder_path.glob("*side*.jpeg"))
        
        if not front_images or not side_images:
            print(f"[CheckIn] Missing images in {folder_path}")
            return None
        
        front_image = front_images[0]
        side_image = side_images[0]
        
        # Get location ID from slug
        location_id = self._get_location_id_from_name(location_slug)
        if not location_id:
            location_id = location_slug  # Fallback to slug
        
        # Process
        return await self.process_checkin(
            front_image_path=front_image,
            side_image_path=side_image,
            location_id=location_id,
            date_str=date_str.replace("_", "-")
        )


# Singleton instance
_checkin_service: Optional[CheckInService] = None


def get_checkin_service() -> CheckInService:
    global _checkin_service
    if _checkin_service is None:
        _checkin_service = CheckInService()
    return _checkin_service


__all__ = ['CheckInService', 'CheckInResult', 'get_checkin_service']
