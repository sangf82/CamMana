
import logging
import asyncio
import cv2
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from backend.model_process.control import orchestrator
from backend.data_process.history.logic import HistoryLogic
from backend.data_process.register_car.logic import RegisteredCarLogic
from backend.sync_process.sync.proxy import is_client_mode, upload_folder_to_master
from backend.data_process.location.logic import LocationLogic
from backend.config import DATA_ROOT

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
            
            print(f"[Checkout] Processing {len(images)} images")
            
            tasks = []
            for img_info in images:
                img_path = img_info["path"]
                path_exists = img_path.exists() if hasattr(img_path, 'exists') else Path(str(img_path)).exists()
                print(f"[Checkout] Reading image from: {img_path}, exists: {path_exists}")
                frame = await asyncio.to_thread(cv2.imread, str(img_path))
                if frame is not None:
                    funcs = img_info.get("functions", [])
                    print(f"[Checkout] Image loaded successfully, size: {frame.shape}, functions: {funcs}")
                    if funcs:
                        tasks.append((img_info, self.orchestrator.process_image(frame, funcs)))
                else:
                    print(f"[Checkout] FAILED to read image: {img_path}")
            
            # Run all detection tasks
            print(f"[Checkout] Running {len(tasks)} detection tasks")
            for img_info, task in tasks:
                try:
                    result = await task
                    print(f"[Checkout] Task result keys: {list(result.keys()) if result else 'None'}")
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
                except Exception as task_err:
                    print(f"[Checkout] Task error: {task_err}")
            
            # Normalize plate with error handling
            if plate_number and plate_number != "Unknown":
                try:
                    clean_plate = self.registered_logic.normalize_plate(plate_number)
                except Exception as e:
                    logger.warning(f"Plate normalization failed: {e}")
                    clean_plate = plate_number
            else:
                clean_plate = "Unknown"

            # 2. Find Open Session
            target_record = self.history_logic.find_open_session(clean_plate)
            
            uuid_val = None
            folder_path = None
            if target_record:
                uuid_val = target_record["id"]
                folder_path = Path(target_record["folder_path"]) if target_record.get("folder_path") else None
                status = "Đã ra"
            else:
                # Create NEW record for unknown checkout
                import uuid
                uuid_val = str(uuid.uuid4())
                folder_path = self.history_logic.create_car_folder(
                    uuid_val, 
                    plate=clean_plate, 
                    direction="out",
                    location=location_name
                )
                
                status = "Xe ra lạ"
                record_data = {
                    "id": uuid_val,
                    "plate": clean_plate,
                    "location": location_name,
                    "time_in": "---",
                    "status": status,
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
                calib_dir = DATA_ROOT / "calibration"
                
                calib_side = calib_dir / f"calib_side_{side_cam_id}.json"
                if not calib_side.exists(): calib_side = calib_dir / "calib_side.json"
                    
                calib_top = calib_dir / f"calib_top_{top_cam_id}.json"
                if not calib_top.exists(): calib_top = calib_dir / "calib_topdown.json"
                
                # Get background from shared backgrounds folder
                from backend.model_process.utils.background import get_background_for_camera, capture_background_if_empty
                
                bg_image = get_background_for_camera(top_cam_id)
                
                if not bg_image:
                    # Try to capture background if no car detected in top image
                    logger.info(f"[Checkout] No background found, checking if we can capture one...")
                    try:
                        top_img_cv = await asyncio.to_thread(cv2.imread, str(top_img_info["path"]))
                        if top_img_cv is not None:
                            await capture_background_if_empty(top_cam_id, top_img_cv)
                            bg_image = get_background_for_camera(top_cam_id)
                    except Exception as e:
                        logger.warning(f"[Checkout] Failed to capture background: {e}")
                
                if bg_image:
                    logger.info(f"[Checkout] Using background: {bg_image}")
                else:
                    logger.warning(f"[Checkout] Skipped Volume: No background image found.")

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
                             if folder_path and folder_path.exists():
                                 with open(folder_path / "checkout_model_volume_error.json", "w", encoding="utf-8") as f:
                                     json.dump({"error": err, "details": vol_res}, f, indent=4)
                     except Exception as ve:
                         logger.error(f"[Checkout] Volume exception: {ve}", exc_info=True)
                         if folder_path and folder_path.exists():
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
            print(f"[Checkout] Saving to folder: {folder_path}, exists: {folder_path.exists() if folder_path else 'N/A'}")
            print(f"[Checkout] all_results keys: {list(all_results.keys())}")
            print(f"[Checkout] images count: {len(images)}")
            
            if folder_path and folder_path.exists():
                # Save model outputs
                for func_name, res in all_results.items():
                    if func_name != "raw":
                        output_path = folder_path / f"checkout_model_{func_name}.json"
                        print(f"[Checkout] Saving model output to: {output_path}")
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(res, f, indent=4)
                
                # Save images - use unified naming: {cam_name}_{functions}.jpg
                for img_info in images:
                    path = img_info["path"]
                    cam_name = img_info.get("cam_name", "UnknownCam").replace(" ", "_")
                    funcs_str = "_".join(img_info.get("functions", []))
                    ext = Path(str(path)).suffix or ".jpg"
                    new_name = f"{cam_name}_{funcs_str}{ext}"
                    src_exists = Path(str(path)).exists()
                    print(f"[Checkout] Copying image {path} -> {folder_path / new_name}, src exists: {src_exists}")
                    if src_exists:
                        shutil.copy2(str(path), folder_path / new_name)
            else:
                print(f"[Checkout] Folder path invalid or doesn't exist: {folder_path}")


            # 4. Update History Record
            time_out = datetime.now().strftime("%H:%M:%S")
            # Prefer calculated volume_val, fallback to result dict
            final_volume = volume_val if volume_val is not None else (
                all_results.get("truck_bed", {}).get("volume_m3") or all_results.get("volume", {}).get("volume_m3")
            )
            
            update_data = {
                "time_out": time_out,
                "status": status
            }
            if final_volume is not None:
                try:
                    update_data["vol_measured"] = str(round(float(final_volume), 2))
                except (ValueError, TypeError) as e:
                    print(f"[Checkout] Invalid volume value: {final_volume}, error: {e}")
            
            if uuid_val:
                try:
                    print(f"[Checkout] Updating record {uuid_val} with: {update_data}")
                    self.history_logic.update_record(uuid_val, update_data)
                    print(f"[Checkout] Record updated successfully")
                except Exception as e:
                    print(f"[Checkout] Failed to update history record: {e}")
            
            # --- SYNC FOLDER TO MASTER (if in Client mode) ---
            if is_client_mode() and folder_path:
                try:
                    logger.info(f"[CheckOut] Syncing folder to Master: {folder_path}")
                    sync_result = await upload_folder_to_master(Path(folder_path) if isinstance(folder_path, str) else folder_path)
                    if sync_result and sync_result.get("success"):
                        master_folder_path = sync_result.get("folder_path")
                        logger.info(f"[CheckOut] Folder synced to Master: {master_folder_path}")
                        
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

            result = {
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
            print(f"[Checkout] Returning result: {result}")
            return result

            
        except Exception as e:
            print(f"[Checkout] Checkout error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def close(self):
        pass

def get_checkout_service():
    return CheckOutService()

