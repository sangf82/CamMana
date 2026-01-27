
import logging
import asyncio
import cv2
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from backend.model_process.control import orchestrator
from backend.data_process.history.logic import HistoryLogic
from backend.data_process.register_car.logic import RegisteredCarLogic
from backend.data_process.sync.proxy import is_client_mode, upload_folder_to_master

from backend.data_process.location.logic import LocationLogic

logger = logging.getLogger(__name__)


class CheckOutService:
    def __init__(self):
        self.history_logic = HistoryLogic()
        self.registered_logic = RegisteredCarLogic()
        self.orchestrator = orchestrator
        self.location_logic = LocationLogic()

    async def process_checkout(
        self,
        images: list, # List of dicts with 'path', 'cam_name', 'functions'
        location_id: str,
        date_str: Optional[str] = None
    ) -> Dict:
        """
        Process a check-out event.
        - Run AI on relevant images.
        - Match Plate with Open Session.
        - Handle Volume if applicable.
        - Save evidence to history folder.
        """
        import shutil
        import json
        
        try:
            # Resolve Location Name
            location_name = self.location_logic.get_location_name(location_id)

            # 1. Process ALL images with their functions
            all_results = {}
            plate_number = "Unknown"
            primary_color = "Unknown"
            wheel_count = 0
            
            tasks = []
            for img_info in images:
                frame = await asyncio.to_thread(cv2.imread, str(img_info["path"]))
                if frame is not None:
                    funcs = img_info.get("functions", [])
                    if funcs:
                        tasks.append((img_info, self.orchestrator.process_image(frame, funcs)))
            
            # Run all detection tasks
            for img_info, task in tasks:
                result = await task
                all_results.update(result)
                
                # Extract plate
                if "plate" in result and result["plate"].get("detected"):
                    plate_number = result["plate"].get("plate", "Unknown")
                
                # Extract color
                if "color" in result and result["color"].get("detected"):
                    primary_color = result["color"].get("primary_color", "Unknown")
                    
                # Extract wheel count
                if "wheel" in result and result["wheel"].get("detected"):
                    wheel_count = result["wheel"].get("wheel_count_total", 0)
            
            clean_plate = self.registered_logic.normalize_plate(plate_number) if plate_number != "Unknown" else "Unknown"

            # 2. Find Open Session
            target_record = self.history_logic.find_open_session(clean_plate)
            
            uuid_val = None
            folder_path = None
            status = "Unknown Check-In"

            if target_record:
                uuid_val = target_record["id"]
                folder_path = Path(target_record["folder_path"]) if target_record.get("folder_path") else None
                status = "Matched"
            else:
                # Create NEW record for unknown checkout
                import uuid
                uuid_val = str(uuid.uuid4())
                folder_path = self.history_logic.create_car_folder(uuid_val, plate=clean_plate, direction="out")
                
                record_data = {
                    "id": uuid_val,
                    "plate": clean_plate,
                    "location": location_name,
                    "time_in": "---",
                    "status": "Xe ra lạ",
                    "verify": "Cần KT",
                    "folder_path": str(folder_path),
                    "note": "Xe ra không có dữ liệu vào"
                }
                self.history_logic.add_record(record_data)

            # --- VOLUME DETECTION LOGIC ---
            volume_val = None
            bg_image = None
            
            # Identify Side and Top images for volume
            side_img_info = next((img for img in images if "volume_left_right" in img.get("functions", []) 
                                  or "wheel_detect" in img.get("functions", []) 
                                  or "color_detect" in img.get("functions", [])), None)
            
            top_img_info = next((img for img in images if "volume_top_down" in img.get("functions", [])), None)
            
            print(f"[Checkout] Volume Check: Side={bool(side_img_info)}, Top={bool(top_img_info)}, Path={folder_path}")

            if side_img_info and top_img_info and folder_path:
                side_cam_id = side_img_info.get("cam_id", "default")
                top_cam_id = top_img_info.get("cam_id", "default")
                
                # Resolve Calibration Paths
                calib_dir = Path("database/calibration")
                bg_dir = Path("database/backgrounds")
                
                calib_side = calib_dir / f"calib_side_{side_cam_id}.json"
                if not calib_side.exists(): calib_side = calib_dir / "calib_side.json"
                    
                calib_top = calib_dir / f"calib_top_{top_cam_id}.json"
                if not calib_top.exists(): calib_top = calib_dir / "calib_topdown.json"
                
                # Resolve Background - Use Inpainting for "Cleaned" Background
                from backend.utils.inpainting import generate_seamless_background
                from backend.model_process.functions.truck import TruckDetector
                
                bg_image = None
                cleaned_bg_path = Path("cleaned_output") / f"cleaned_{uuid_val}.jpg"
                
                try:
                    logger.info(f"[Checkout] Detecting truck on top image for inpainting mask...")
                    td = TruckDetector(confidence=0.3) # Lower confidence for topdown
                    top_img_cv = await asyncio.to_thread(cv2.imread, str(top_img_info["path"]))
                    det = td.detect(top_img_cv)
                    
                    bbox = None
                    if det.get("detected"):
                        x1, y1, x2, y2 = det["bbox"]
                        bbox = {"x": x1, "y": y1, "w": x2-x1, "h": y2-y1}
                        logger.info(f"[Checkout] Truck detected on top image at {bbox}")

                    success = await generate_seamless_background(Path(top_img_info["path"]), cleaned_bg_path, truck_bbox=bbox)
                    if success:
                        bg_image = cleaned_bg_path
                        logger.info(f"[Checkout] Cleaned background generated: {bg_image}")
                except Exception as ie:
                    logger.warning(f"[Checkout] Inpainting failed, falling back to static background: {ie}")

                if not bg_image:
                    bg_image_candidate = bg_dir / f"bg_{top_cam_id}.jpg"
                    if bg_image_candidate.exists():
                         bg_image = bg_image_candidate
                    else:
                         bgs = list(bg_dir.glob("*.jpg"))
                         bg_image = bgs[0] if bgs else None
                
                if not bg_image:
                    logger.warning(f"[Checkout] Skipped Volume: No background image found or generated.")

                if calib_side.exists() and calib_top.exists() and bg_image:
                     logger.info(f"[Checkout] Starting volume estimation for session {uuid_val}...")
                     try:
                         # Ensure paths are absolute or correct relative paths
                         vol_res = await self.orchestrator.process_volume(
                             side_image_path=Path(side_img_info["path"]),
                             top_fg_image_path=Path(top_img_info["path"]),
                             top_bg_image_path=bg_image,
                             side_calib_path=calib_side,
                             top_calib_path=calib_top
                         )
                         if vol_res and vol_res.get("success"):
                             volume_val = vol_res.get("volume")
                             all_results["volume"] = vol_res
                             logger.info(f"[Checkout] Volume detected: {volume_val} m3")
                         else:
                             # Save error to JSON for visibility
                             err = vol_res.get('error') if vol_res else 'Unknown'
                             logger.error(f"[Checkout] Volume failed: {err}")
                             with open(folder_path / "checkout_model_volume_error.json", "w", encoding="utf-8") as f:
                                 json.dump({"error": err, "details": vol_res}, f, indent=4)
                     except Exception as ve:
                         logger.error(f"[Checkout] Volume exception: {ve}")
                         with open(folder_path / "checkout_model_volume_error.json", "w", encoding="utf-8") as f:
                             json.dump({"error": str(ve)}, f, indent=4)
            else:
                 msg = []
                 if not side_img_info: msg.append("Missing Side Cam")
                 if not top_img_info: msg.append("Missing Top Cam")
                 if not folder_path: msg.append("Missing Folder Path")
                 
                 logger.warning(f"[Checkout] Volume Skipped: {', '.join(msg)}")
                 if folder_path:
                     with open(folder_path / "checkout_model_volume_error.json", "w", encoding="utf-8") as f:
                         json.dump({"error": "Volume Skipped", "reasons": msg}, f, indent=4)

            # 3. Save results to folder
            if folder_path and folder_path.exists():
                # Save model outputs
                for func_name, res in all_results.items():
                    if func_name != "raw":
                        with open(folder_path / f"checkout_model_{func_name}.json", "w", encoding="utf-8") as f:
                            json.dump(res, f, indent=4)
                
                # Save images - use unified naming: {cam_name}_{functions}.jpg
                for img_info in images:
                    path = img_info["path"]
                    cam_name = img_info.get("cam_name", "UnknownCam").replace(" ", "_")
                    funcs_str = "_".join(img_info.get("functions", []))
                    ext = path.suffix or ".jpg"
                    new_name = f"{cam_name}_{funcs_str}{ext}"
                    if path.exists():
                        shutil.copy2(path, folder_path / new_name)


            # 4. Update History Record
            time_out = datetime.now().strftime("%H:%M:%S")
            # Prefer calculated volume_val, fallback to result dict
            final_volume = volume_val if volume_val is not None else (
                all_results.get("truck_bed", {}).get("volume_m3") or all_results.get("volume", {}).get("volume_m3")
            )
            
            update_data = {
                "time_out": time_out,
                "status": "Đã ra" if status == "Matched" else "Xe ra lạ"
            }
            if final_volume is not None:
                update_data["vol_measured"] = str(round(final_volume, 2))
                
            self.history_logic.update_record(uuid_val, update_data)
            
            # --- SYNC FOLDER TO MASTER (if in Client mode) ---
            if is_client_mode() and folder_path:
                try:
                    logger.info(f"[CheckOut] Syncing folder to Master: {folder_path}")
                    sync_result = await upload_folder_to_master(Path(folder_path) if isinstance(folder_path, str) else folder_path)
                    if sync_result and sync_result.get("success"):
                        master_folder_path = sync_result.get("folder_path")
                        logger.info(f"[CheckOut] Folder synced to Master: {master_folder_path}")
                        
                        # Update the synced record's folder_path on Master
                        from backend.data_process.sync.proxy import get_master_url
                        from backend.schemas import SyncPayload
                        import httpx
                        
                        master_url = get_master_url()
                        if master_url:
                            payload = SyncPayload(
                                type="history",
                                action="update_folder_path",
                                data={
                                    "id": uuid_val,
                                    "folder_path": master_folder_path
                                },
                                timestamp=datetime.now().isoformat()
                            )
                            async with httpx.AsyncClient(timeout=5.0) as client:
                                await client.post(
                                    f"{master_url.rstrip('/')}/api/sync/receive",
                                    json=payload.model_dump(),
                                    headers={"Content-Type": "application/json"}
                                )
                    else:
                        logger.warning("[CheckOut] Failed to sync folder to Master")
                except Exception as e:
                    logger.error(f"[CheckOut] File sync error: {e}")
            
            # Get history volume (vol_measured from entry)
            history_vol = None
            if target_record and target_record.get("vol_measured"):
                try: history_vol = float(target_record["vol_measured"])
                except: pass

            return {
                "success": True,
                "plate": clean_plate,
                "color": primary_color,
                "wheel_count": wheel_count,
                "status": status,
                "uuid": uuid_val,
                "folder_path": str(folder_path) if folder_path else None,
                "history_volume": float(history_vol) if history_vol is not None else None,
                "volume": float(final_volume) if final_volume is not None else None,
                "is_checkout": True
            }

            
        except Exception as e:
            logger.error(f"Checkout error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def close(self):
        pass

def get_checkout_service():
    return CheckOutService()

