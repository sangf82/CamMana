"""
Check-In API Endpoints

Provides endpoints for:
- Processing new check-ins
- Testing with existing data
- Human verification of plates
- Getting check-in status
"""

import time
import json
import httpx
import shutil
import asyncio
import tempfile
import traceback
import cv2
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.data_process.user.api import get_current_user
from backend.schemas import User as UserSchema
from backend.workflow.checkin.logic import get_checkin_service, CheckInResult
from backend.camera.state import cameras as active_cameras
from backend.data_process import get_registered_cars
from backend.workflow.config import LocationTag
from backend.settings import settings


checkin_router = APIRouter(prefix="/api/checkin", tags=["check-in"])


# Request/Response Models
class VerifyPlateRequest(BaseModel):
    folder_path: str
    verified_plate: str
    approved: bool = True


class CheckInStatusResponse(BaseModel):
    uuid: str
    location_id: str
    date: str
    folder_path: str
    plate_number: Optional[str]
    color: Optional[str]
    wheel_count: int
    status: str
    verified_plate: Optional[str] = None


class ProcessTestDataRequest(BaseModel):
    date_folder: Optional[str] = None  # e.g., "15-01-2026"


# Endpoints
@checkin_router.get("/health")
async def check_api_health():
    """Check if the external AI API is available"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://thpttl12t1--truck-api-fastapi-app.modal.run/health"
            )
            return {"status": "ok", "api_response": response.json()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class CaptureAndProcessRequest(BaseModel):
    front_camera_id: Optional[str] = None
    side_camera_id: Optional[str] = None
    top_camera_id: Optional[str] = None
    cameras: Optional[List[str]] = []
    location_id: str
    location_name: Optional[str] = None


class CaptureResponse(BaseModel):
    success: bool
    uuid: Optional[str] = None
    folder_path: Optional[str] = None
    plate: Optional[str] = None
    plate_confidence: float = 0.0
    color: Optional[str] = None
    color_confidence: float = 0.0
    wheel_count: int = 0
    wheel_confidence: float = 0.0
    volume: Optional[float] = None
    status: Optional[str] = None
    matched: bool = False
    registered_info: Optional[Dict[str, Any]] = None
    front_image_url: Optional[str] = None
    side_image_url: Optional[str] = None
    top_image_url: Optional[str] = None
    duration: float = 0.0
    time_in: Optional[str] = None
    history_plate: Optional[str] = None
    history_volume: Optional[float] = None
    error: Optional[str] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None
    is_checkout: bool = False


@checkin_router.post("/capture-and-process", response_model=CaptureResponse)
async def capture_and_process(
    request: CaptureAndProcessRequest, user: UserSchema = Depends(get_current_user)
):
    """
    Capture images from live cameras and process check-in
    """
    start_total = time.time()
    print(f"[API] >>> START capture-and-process request for {request.location_id}")

    try:
        checkin_service = get_checkin_service()

        # Helper to get frame with retry for gray/empty frames
        async def get_frame(cam_id):
            if not cam_id:
                return None

            frame = None

            # Helper to check if frame is "empty" (all pixels roughly same or very low variance)
            def is_suspicious(f):
                if f is None:
                    return True
                try:
                    # Check mean and variance. Solid gray/black has very low variance.
                    # Solid gray is often mean ~128, variance ~0
                    _, stddev = cv2.meanStdDev(f)
                    return stddev[0][0] < 5.0  # Very low variance is suspicious
                except Exception as e:
                    print(f"[API] Error checking frame variance: {e}")
                    return True

            for attempt in range(3):
                # Get from active cameras
                cam_state = active_cameras.get(cam_id)
                if cam_state:
                    streamer = cam_state.get("streamer")
                    if streamer:
                        try:
                            frame = (
                                streamer.get_capture_frame()
                                if hasattr(streamer, "get_capture_frame")
                                else streamer.last_frame
                            )
                        except Exception as e:
                            print(f"[API] Error getting frame from streamer: {e}")

                if not is_suspicious(frame):
                    return frame

                print(
                    f"[API] Frame from {cam_id} is suspicious (attempt {attempt + 1}), waiting..."
                )
                await asyncio.sleep(0.5)  # Wait for stream to stabilize

            return frame  # Return anyway if all retries fail

        # Helper to get cam info and functions
        def get_cam_info(cam_id):
            if not cam_id:
                return None
            # Fetch camera configuration to get its functions
            from backend.camera.logic import CameraLogic

            cam_logic = CameraLogic()
            cam_config = cam_logic.get_camera_by_id(cam_id)

            functions = []
            if cam_config:
                from backend.data_process.camera_type.logic import CameraTypeLogic

                cam_types = CameraTypeLogic().get_types()
                type_obj = next(
                    (t for t in cam_types if t.get('name') == cam_config.get("type")), None
                )
                if type_obj:
                    # 'functions' field in CSV might be semicolon-separated
                    funcs_raw = type_obj.get('functions', '')
                    if isinstance(funcs_raw, str):
                        functions = funcs_raw.split(";")
                    elif isinstance(funcs_raw, list):
                        functions = funcs_raw

            return {
                "name": cam_config.get("name", "Unknown") if cam_config else "Unknown",
                "functions": [f for f in functions if f],
            }

        # 1. Resolve Camera IDs (Support both new 'cameras' list and legacy fields)
        cam_ids = request.cameras or []
        if request.front_camera_id and request.front_camera_id not in cam_ids:
            cam_ids.append(request.front_camera_id)
        if request.side_camera_id and request.side_camera_id not in cam_ids:
            cam_ids.append(request.side_camera_id)
        if request.top_camera_id and request.top_camera_id not in cam_ids:
            cam_ids.append(request.top_camera_id)
        cam_ids = [c for c in cam_ids if c]  # Filter empty

        print(f"[API] Processing {len(cam_ids)} cameras: {cam_ids}")

        # 2. Capture and Build Image List in Parallel
        print(f"[API] Capturing frames for {len(cam_ids)} cameras in parallel...")
        capture_tasks = [get_frame(cid) for cid in cam_ids]
        frames = await asyncio.gather(*capture_tasks)

        images_to_process = []
        captured_paths = {}  # id -> path

        for cid, frame in zip(cam_ids, frames):
            if frame is None:
                print(f"[API] Failed to capture frame for {cid}")
                continue

            # Save to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                await asyncio.to_thread(cv2.imwrite, tmp.name, frame)
                path = Path(tmp.name)
                captured_paths[cid] = path

            # Get Info
            info = get_cam_info(cid)
            if info:
                print(
                    f"[API] Camera {cid} ({info['name']}) functions: {info['functions']}"
                )
                images_to_process.append(
                    {
                        "path": path,
                        "cam_name": info["name"],
                        "functions": info["functions"],
                        "cam_id": cid,
                    }
                )

        print(f"[API] Prepared {len(images_to_process)} images for processing")
        if not images_to_process:
            print("[API] No images to process, returning error")
            return CaptureResponse(
                success=False,
                error="Không thể chụp hình từ bất kỳ camera nào. Kiểm tra kết nối Camera.",
                reason="capture_failed",
            )

        # 3. Determine Location Strategy
        from backend.data_process.location.logic import LocationLogic

        locations = LocationLogic().get_locations()
        location_obj = next(
            (
                l
                for l in locations
                if l.get('id') == request.location_id or l.get('name') == request.location_id
            ),
            None,
        )
        location_tag = location_obj.get('tag', 'Cơ bản') if location_obj else "Cơ bản"

        # Determine if Check-In or Check-Out
        if location_tag == "Cổng ra":
            # Process as Check-Out
            from backend.workflow.checkout import get_checkout_service

            checkout_service = get_checkout_service()
            result_dict = await checkout_service.process_checkout(
                images=images_to_process, location_id=request.location_id
            )
            # Wrap in CaptureResponse format
            folder_path = result_dict.get("folder_path")
            front_url = None
            side_url = None
            top_url = None
            if folder_path:
                folder = Path(folder_path)
                if folder.exists():
                    parent_name = folder.parent.name
                    folder_name = folder.name

                    # Look for images based on camera functions in filename
                    all_imgs = []
                    for img in folder.glob("*.jpg"):
                        iname = img.name.lower()
                        url = f"/api/images/{parent_name}/{folder_name}/{img.name}"
                        all_imgs.append((iname, url))

                        # Match by function names in filename (using unified naming)
                        if "plate_detect" in iname:
                            if not front_url:
                                front_url = url
                        elif "volume_top_down" in iname:
                            if not top_url:
                                top_url = url
                        elif (
                            "volume_left_right" in iname
                            or "wheel_detect" in iname
                            or "color_detect" in iname
                        ):
                            if not side_url:
                                side_url = url

                    # Fallback: use first image as front if no match
                    if not front_url and all_imgs:
                        front_url = all_imgs[0][1]

            # Cleanup temp files
            for img_info in images_to_process:
                img_info["path"].unlink(missing_ok=True)

            return CaptureResponse(
                success=True,
                uuid=result_dict.get("uuid"),
                plate=result_dict.get("plate"),
                color=result_dict.get("color"),
                wheel_count=result_dict.get("wheel_count", 0),
                status=result_dict.get("status"),
                folder_path=folder_path,
                front_image_url=front_url,
                side_image_url=side_url,
                top_image_url=top_url,
                history_volume=float(result_dict.get("history_volume"))
                if result_dict.get("history_volume") is not None
                else None,
                volume=float(result_dict.get("volume"))
                if result_dict.get("volume") is not None
                else None,
                duration=time.time() - start_total,
                is_checkout=True,
            )

        # Default to Check-In
        print(f"[API] Processing Check-In for location {request.location_id}")
        date_str = datetime.now().strftime("%d-%m-%Y")

        try:
            # Process check-in
            result = await checkin_service.process_checkin(
                images=images_to_process,
                location_id=request.location_id,
                date_str=date_str,
            )
        except Exception as e:
            print(f"[API] Check-In workflow failed: {e}")
            traceback.print_exc()
            raise e

        print(f"[API] Check-In workflow success, uuid={result.uuid}")

        # --- Volume Estimation ---
        volume_val = None
        is_volume_loc = location_tag in [
            "Tính thể tích vật liệu (Trên dưới)",
            "Tính thể tích vật liệu (Trái phải)",
            LocationTag.VOLUME_TOP_DOWN.value,
            LocationTag.VOLUME_LEFT_RIGHT.value,
        ]

        volume_val = None
        volume_res = None
        if is_volume_loc and result.folder_path:
            # Identify Side and Top images for volume
            side_img = next(
                (
                    img
                    for img in images_to_process
                    if any(
                        f in img["functions"]
                        for f in ["volume_left_right", "wheel_detect", "color_detect"]
                    )
                ),
                None,
            )
            top_img = next(
                (
                    img
                    for img in images_to_process
                    if "volume_top_down" in img["functions"]
                ),
                None,
            )

            if side_img and top_img:
                from backend.model_process.control import orchestrator
                from backend.model_process.utils.background import get_background_for_camera

                folder = Path(result.folder_path)

                # Paths for calibration
                calib_dir = settings.calibration_dir

                side_cam_id = side_img.get("cam_id", "default")
                top_cam_id = top_img.get("cam_id", "default")

                # 1. Resolve Calibration Files
                calib_side = calib_dir / f"calib_side_{side_cam_id}.json"
                if not calib_side.exists():
                    calib_side = calib_dir / "calib_side.json"

                calib_top = calib_dir / f"calib_top_{top_cam_id}.json"
                if not calib_top.exists():
                    calib_top = calib_dir / "calib_topdown.json"

                # 2. Resolve Background Image from shared backgrounds folder
                bg_image = get_background_for_camera(top_cam_id)

                if calib_side.exists() and calib_top.exists() and bg_image:
                    print(
                        f"[API] Starting volume estimation for location {request.location_id}..."
                    )
                    try:
                        volume_res = await orchestrator.process_volume(
                            side_image_path=side_img["path"],
                            top_fg_image_path=top_img["path"],
                            top_bg_image_path=bg_image,
                            side_calib_path=calib_side,
                            top_calib_path=calib_top,
                        )

                        if volume_res and volume_res.get("success"):
                            volume_val = volume_res.get("volume")
                            print(f"[API] Volume detected: {volume_val} m3")

                            # Save full volume JSON to folder
                            vol_file = folder / "volume_estimation.json"
                            with open(vol_file, "w", encoding="utf-8") as f:
                                json.dump(volume_res, f, indent=4, ensure_ascii=False)

                            # Update checkin_status.json
                            status_file = folder / "checkin_status.json"
                            if status_file.exists():
                                with open(status_file, "r+", encoding="utf-8") as f:
                                    try:
                                        status_data = json.load(f)
                                        status_data["volume"] = volume_val
                                        status_data["volume_data_file"] = (
                                            "volume_estimation.json"
                                        )
                                        f.seek(0)
                                        json.dump(
                                            status_data, f, indent=4, ensure_ascii=False
                                        )
                                        f.truncate()
                                    except:
                                        pass

                            # Persist to History CSV
                            checkin_service.history_logic.update_record(
                                result.uuid,
                                {
                                    "vol_measured": str(round(volume_val, 2))
                                    if volume_val is not None
                                    else ""
                                },
                            )
                        else:
                            err = volume_res.get("error") if volume_res else "Unknown"
                            print(f"[API] Volume estimation failed: {err}")
                            with open(
                                folder / "volume_error.json", "w", encoding="utf-8"
                            ) as f:
                                json.dump(
                                    {"error": err, "details": volume_res}, f, indent=4
                                )
                    except Exception as ve:
                        print(f"[API] Volume estimation exception: {ve}")
                        with open(
                            folder / "volume_error.json", "w", encoding="utf-8"
                        ) as f:
                            json.dump({"error": str(ve)}, f, indent=4)
                else:
                    msg = []
                    if not calib_side.exists():
                        msg.append("Missing Side Calibration")
                    if not calib_top.exists():
                        msg.append("Missing Top Calibration")
                    if not bg_image:
                        msg.append("Missing Background Image")
                    print(f"[API] Volume Skipped: {', '.join(msg)}")
                    with open(folder / "volume_error.json", "w", encoding="utf-8") as f:
                        json.dump(
                            {"error": "Volume Skipped", "reasons": msg}, f, indent=4
                        )
            else:
                msg = []
                if not side_img:
                    msg.append("Missing Side Cam")
                if not top_img:
                    msg.append("Missing Top Cam")
                if result.folder_path:
                    with open(
                        Path(result.folder_path) / "volume_error.json",
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(
                            {"error": "Volume Skipped", "reasons": msg}, f, indent=4
                        )

        # Cleanup temp files
        print("[API] Cleaning up temp files")
        for img_info in images_to_process:
            img_info["path"].unlink(missing_ok=True)

        # Match with registered cars
        from backend.data_process import find_registered_car

        matched = False
        registered_info = None

        if result.plate_number:
            car = find_registered_car(result.plate_number)
            if car:
                matched = True
                registered_info = {
                    "owner": car.owner,
                    "model": car.model,
                    "color": car.color,
                    "standard_volume": car.standard_volume,
                }

        # Generate Image URLs
        print("[API] Generating Image URLs")
        front_image_url = None
        side_image_url = None
        top_image_url = None

        if result.folder_path:
            folder = Path(result.folder_path)
            if folder.exists():
                images = list(folder.glob("*.jpg"))
                parent_name = folder.parent.name
                folder_name = folder.name

                for img in images:
                    img_name = img.name.lower()
                    url = f"/api/images/{parent_name}/{folder_name}/{img.name}"

                    # Match by function names in filename (unified naming)
                    if "plate_detect" in img_name:
                        if not front_image_url:
                            front_image_url = url
                    elif "volume_top_down" in img_name:
                        if not top_image_url:
                            top_image_url = url
                    elif (
                        "volume_left_right" in img_name
                        or "wheel_detect" in img_name
                        or "color_detect" in img_name
                    ):
                        if not side_image_url:
                            side_image_url = url

                # Fallback Logic
                if not front_image_url and images:
                    front_image_url = (
                        f"/api/images/{parent_name}/{folder_name}/{images[0].name}"
                    )
                if not side_image_url and len(images) > 1:
                    side_image_url = (
                        f"/api/images/{parent_name}/{folder_name}/{images[1].name}"
                    )

        total_duration = time.time() - start_total
        print(f"[API] capture-and-process completed in {total_duration:.2f}s")

        print(f"[API] Constructing CaptureResponse...")
        return CaptureResponse(
            success=True,
            uuid=result.uuid,
            folder_path=result.folder_path,
            plate=result.plate_number,
            plate_confidence=result.plate_confidence,
            color=result.color,
            color_confidence=result.color_confidence,
            wheel_count=result.wheel_count,
            wheel_confidence=result.wheel_confidence,
            volume=volume_val,
            status=result.status,
            matched=matched,
            registered_info=registered_info,
            confidence=result.plate_confidence,
            front_image_url=front_image_url,
            side_image_url=side_image_url,
            top_image_url=top_image_url,
            duration=total_duration,
            time_in=result.history_record.get("time_in")
            if result.history_record
            else None,
            history_plate=result.history_record.get("plate")
            if result.history_record
            else None,
        )

    except Exception as e:
        import traceback

        print(f"[API] Outer Exception caught: {e}")
        traceback.print_exc()
        return CaptureResponse(success=False, error=str(e), reason="processing_error")


@checkin_router.post("/process")
async def process_checkin(
    front_image: UploadFile = File(...),
    side_image: UploadFile = File(...),
    location_id: str = Form(...),
    date: Optional[str] = Form(None),
):
    """
    Process a new vehicle check-in

    - front_image: Image from front camera (for plate detection)
    - side_image: Image from side camera (for color and wheel detection)
    - location_id: Gate/location ID
    - date: Optional date string (dd-mm-yyyy), defaults to today
    """
    import tempfile
    import shutil

    try:
        service = get_checkin_service()

        # Save uploaded files temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as front_temp:
            shutil.copyfileobj(front_image.file, front_temp)
            front_path = Path(front_temp.name)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as side_temp:
            shutil.copyfileobj(side_image.file, side_temp)
            side_path = Path(side_temp.name)

        # Prepare images list for workflow
        images_list = [
            {
                "path": front_path,
                "cam_name": "Front Cam",
                "functions": ["plate"],  # Front cam typically for plate
            },
            {
                "path": side_path,
                "cam_name": "Side Cam",
                "functions": [
                    "wheel",
                    "color",
                    "volume_left_right",
                ],  # Side cam for other features
            },
        ]

        # Process check-in
        result = await service.process_checkin(
            images=images_list, location_id=location_id, date_str=date
        )

        # Cleanup temp files
        front_path.unlink(missing_ok=True)
        side_path.unlink(missing_ok=True)

        return {
            "success": True,
            "uuid": result.uuid,
            "folder_path": result.folder_path,
            "plate_number": result.plate_number,
            "plate_confidence": result.plate_confidence,
            "color": result.color,
            "color_confidence": result.color_confidence,
            "wheel_count": result.wheel_count,
            "wheel_confidence": result.wheel_confidence,
            "status": result.status,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@checkin_router.post("/verify")
async def verify_plate(request: VerifyPlateRequest):
    """
    Human verification of detected plate number

    Updates the check-in record and renames files/folders
    """
    try:
        service = get_checkin_service()
        result = await service.verify_plate(
            folder_path=request.folder_path,
            verified_plate=request.verified_plate,
            approved=request.approved,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@checkin_router.get("/pending")
async def get_pending_verifications():
    """Get all check-ins pending verification"""
    from pathlib import Path
    import json

    pending = []
    car_history_dir = settings.car_history_dir

    if not car_history_dir.exists():
        return {"pending": []}

    # Scan all date folders
    for date_folder in car_history_dir.iterdir():
        if not date_folder.is_dir():
            continue

        # Scan all car folders
        for car_folder in date_folder.iterdir():
            if not car_folder.is_dir():
                continue

            status_file = car_folder / "checkin_status.json"
            if status_file.exists():
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)

                if status_data.get("status") == "pending_verification":
                    pending.append(
                        {
                            "uuid": status_data.get("uuid"),
                            "location_id": status_data.get("location_id"),
                            "date": status_data.get("date"),
                            "folder_path": str(car_folder),
                            "plate_number": status_data.get("plate_number"),
                            "color": status_data.get("color"),
                            "wheel_count": status_data.get("wheel_count"),
                            "status": status_data.get("status"),
                            "created_at": status_data.get("created_at"),
                        }
                    )

    return {"pending": pending, "count": len(pending)}


@checkin_router.post("/test/process-folder")
async def process_test_folder(folder_path: str):
    """
    Process a single existing test folder

    For testing check-in logic with existing images
    """
    try:
        service = get_checkin_service()
        folder = Path(folder_path)

        if not folder.exists():
            raise HTTPException(status_code=404, detail="Folder not found")

        result = await service.process_existing_folder(folder)

        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Could not process folder - missing images or invalid format",
            )

        return {
            "success": True,
            "uuid": result.uuid,
            "folder_path": result.folder_path,
            "plate_number": result.plate_number,
            "color": result.color,
            "wheel_count": result.wheel_count,
            "status": result.status,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@checkin_router.post("/test/process-all")
async def process_all_test_data(request: ProcessTestDataRequest = None):
    """
    Process all test data in car_history folder

    Optionally specify a date folder to process
    """
    car_history_dir = Path("database/car_history")

    if not car_history_dir.exists():
        raise HTTPException(status_code=404, detail="Car history directory not found")

    service = get_checkin_service()
    results = []
    errors = []

    # Find date folders to process
    if request and request.date_folder:
        date_folders = [car_history_dir / request.date_folder]
    else:
        date_folders = [f for f in car_history_dir.iterdir() if f.is_dir()]

    for date_folder in date_folders:
        if not date_folder.exists():
            continue

        # Process each car folder
        for car_folder in date_folder.iterdir():
            if not car_folder.is_dir():
                continue

            # Skip already processed folders (have checkin_status.json with results)
            status_file = car_folder / "checkin_status.json"
            if status_file.exists():
                with open(status_file, "r") as f:
                    existing = json.load(f)
                    if existing.get("plate_number") or existing.get("color"):
                        print(f"[Test] Skipping already processed: {car_folder.name}")
                        continue

            try:
                print(f"[Test] Processing: {car_folder.name}")
                result = await service.process_existing_folder(car_folder)

                if result:
                    results.append(
                        {
                            "folder": car_folder.name,
                            "uuid": result.uuid,
                            "plate_number": result.plate_number,
                            "color": result.color,
                            "wheel_count": result.wheel_count,
                            "status": result.status,
                        }
                    )
            except Exception as e:
                errors.append({"folder": car_folder.name, "error": str(e)})

    await service.close()

    return {
        "success": True,
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


@checkin_router.get("/status/{folder_name}")
async def get_checkin_status(folder_name: str, date_folder: Optional[str] = None):
    """Get status of a specific check-in by folder name"""
    car_history_dir = Path("database/car_history")

    # Search in specific date folder or all
    if date_folder:
        search_dirs = [car_history_dir / date_folder]
    else:
        search_dirs = [f for f in car_history_dir.iterdir() if f.is_dir()]

    for date_dir in search_dirs:
        car_folder = date_dir / folder_name
        status_file = car_folder / "checkin_status.json"

        if status_file.exists():
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)

    raise HTTPException(status_code=404, detail="Check-in not found")
