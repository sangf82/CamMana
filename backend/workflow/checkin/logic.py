import logging
import json
import uuid
import shutil
import asyncio
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.model_process.control import orchestrator
from backend.data_process.history.logic import HistoryLogic
from backend.data_process.location.logic import LocationLogic
from backend.data_process.register_car.logic import RegisteredCarLogic
from backend.data_process.register_car.logic import RegisteredCarLogic
from backend.sync_process.sync.proxy import is_client_mode, upload_folder_to_master

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
        self.location_logic = LocationLogic()

    async def process_checkin(
        self,
        images: List[Dict[str, Any]],
        location_id: str,
        date_str: Optional[str] = None,
    ) -> CheckInResult:
        """
        Process a check-in event.
        - Run AI Detection.
        - Create Folder.
        - Save Data.
        """
        try:
            # 0. Initialize UUID for the session
            session_id = str(uuid.uuid4())

            # Resolve Location Name
            location_name = self.location_logic.get_location_name(location_id)

            # 1. AI Detection on all images
            tasks = []
            for img_info in images:
                path = img_info["path"]
                funcs = img_info.get("functions", [])
                if not path.exists():
                    continue

                # Use to_thread to avoid blocking event loop
                frame = await asyncio.to_thread(cv2.imread, str(path))
                if frame is not None:
                    # Run functions in parallel for this frame
                    tasks.append(self.orchestrator.process_image(frame, funcs))

            # Gather all results
            all_results_list = await asyncio.gather(*tasks)
            results = {}
            for res_dict in all_results_list:
                results.update(res_dict)

            # Extract Data
            plate_res = results.get("plate", {})
            plate_number = plate_res.get("plate", "Unknown")

            color_res = results.get("color", {})
            primary_color = color_res.get("primary_color", "Unknown")

            wheel_res = results.get("wheel", {})
            wheel_count = wheel_res.get("wheel_count_total", 0)

            # 2. Create Folder and Save Model Outputs
            folder_path = self.history_logic.create_car_folder(
                session_id, plate=plate_number, direction="in", location=location_name
            )

            # Save individual model outputs as JSON
            for func_name, res in results.items():
                if func_name != "raw":
                    with open(
                        folder_path / f"model_{func_name}.json", "w", encoding="utf-8"
                    ) as f:
                        json.dump(res, f, indent=4)

            # 3. Save Images with custom naming: {cam_name}_{functions}.jpg
            for img_info in images:
                path = img_info["path"]
                cam_name = img_info.get("cam_name", "UnknownCam").replace(" ", "_")
                funcs_str = "_".join(img_info.get("functions", []))

                ext = path.suffix or ".jpg"
                new_name = f"{cam_name}_{funcs_str}{ext}"
                if path.exists():
                    shutil.copy2(path, folder_path / new_name)

            # 4. Check Registration
            car = self.registered_logic.get_car_by_plate(plate_number)
            vol_std = car.get("car_volume", "") if car else ""

            # 5. Create History Record (CSV)
            clean_plate = (
                self.registered_logic.normalize_plate(plate_number)
                if plate_number != "Unknown"
                else f"Unknown_{session_id[:4]}"
            )

            record_data = {
                "id": session_id,
                "plate": clean_plate,
                "location": location_name,
                "status": "Check-In Pending",
                "folder_path": str(folder_path),
                "vol_std": vol_std,
                "vol_measured": "",
            }
            record = self.history_logic.add_record(record_data)

            # 6. Save Master JSON (checkin_status.json)
            status_data = {
                "uuid": session_id,
                "plate_number": clean_plate,
                "color": primary_color,
                "wheel_count": wheel_count,
                "status": "pending_verification",
                "folder_path": str(folder_path),
                "created_at": datetime.now().isoformat(),
                "registered_info": car if car else {},
                "ai_results": {k: v for k, v in results.items() if k != "raw"},
            }

            status_file = folder_path / "checkin_status.json"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=4)

            # --- SYNC FOLDER TO MASTER (if in Client mode) ---
            if is_client_mode():
                # Define sync task
                async def run_sync_task():
                    try:
                        logger.info(f"[CheckIn] Background syncing folder to Master: {folder_path}")
                        sync_result = await upload_folder_to_master(folder_path)
                        if sync_result and sync_result.get("success"):
                            master_folder_path = sync_result.get("folder_path")
                            logger.info(
                                f"[CheckIn] Folder synced to Master: {master_folder_path}"
                            )

                            # Update the synced record's folder_path on Master
                            from backend.sync_process.sync.proxy import get_master_url
                            from backend.schemas import SyncPayload
                            import httpx

                            master_url = get_master_url()
                            if master_url:
                                payload = SyncPayload(
                                    type="history",
                                    action="update_folder_path",
                                    data={
                                        "id": session_id,
                                        "folder_path": master_folder_path,
                                    },
                                    timestamp=datetime.now().isoformat(),
                                )
                                async with httpx.AsyncClient(timeout=5.0) as client:
                                    await client.post(
                                        f"{master_url.rstrip('/')}/api/sync/receive",
                                        json=payload.model_dump(),
                                        headers={"Content-Type": "application/json"},
                                    )
                        else:
                            logger.warning("[CheckIn] Failed to sync folder to Master")
                    except Exception as e:
                        logger.error(f"[CheckIn] File sync error: {e}")

                # Fire and forget (background task)
                asyncio.create_task(run_sync_task())

            return CheckInResult(
                uuid=session_id,
                folder_path=str(folder_path),
                plate_number=clean_plate,
                color=primary_color,
                wheel_count=wheel_count,
                status="pending_verification",
                history_record=record,
            )

        except Exception as e:
            logger.error(f"Processing checkin failed: {e}", exc_info=True)
            raise e

    async def verify_plate(
        self, folder_path: str, verified_plate: str, approved: bool
    ) -> Dict:
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
            self.history_logic.update_record(
                uuid_val,
                {"plate": verified_plate, "status": status, "verify": "Manual"},
            )

        # Update JSON
        current_data["status"] = "verified" if approved else "rejected"
        current_data["verified_plate"] = verified_plate

        with open(status_file, "w") as f:
            json.dump(current_data, f, indent=4)

        return {"success": True, "status": status, "plate": verified_plate}

    async def process_existing_folder(
        self, folder_path: Path
    ) -> Optional[CheckInResult]:
        """
        Process an existing folder with images.
        Used for testing and reprocessing.
        """
        try:
            # Look for images in the folder
            images = []
            # Find all .jpg files
            jpg_files = list(folder_path.glob("*.jpg"))
            if not jpg_files:
                return None

            for path in jpg_files:
                # Try to guess functions from filename
                name = path.name.lower()
                funcs = []
                if "plate" in name:
                    funcs.append("plate")
                if "wheel" in name:
                    funcs.append("wheel")
                if "color" in name:
                    funcs.append("color")
                if "volume" in name:
                    funcs.append("volume_left_right")

                images.append(
                    {
                        "path": path,
                        "cam_name": "TestCam",
                        "functions": funcs or ["plate", "wheel", "color"],  # Fallback
                    }
                )

            # Use process_checkin logic
            return await self.process_checkin(images, location_id="test_loc")
        except Exception as e:
            logger.error(f"process_existing_folder failed: {e}")
            return None

    async def close(self):
        pass


def get_checkin_service():
    return CheckInService()
