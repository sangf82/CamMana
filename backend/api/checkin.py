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

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.workflow.checkin import get_checkin_service, CheckInResult
from backend.api._shared import cameras as active_cameras
from backend.data_process import get_registered_cars
from backend.workflow.config import LocationTag


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
            response = await client.get("https://thpttl12t1--truck-api-fastapi-app.modal.run/health")
            return {"status": "ok", "api_response": response.json()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class CaptureAndProcessRequest(BaseModel):
    front_camera_id: str
    side_camera_id: Optional[str] = None
    top_camera_id: Optional[str] = None
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
async def capture_and_process(request: CaptureAndProcessRequest):
    """
    Capture images from live cameras and process check-in
    """
    start_total = time.time()
    print(f"[API] capture-and-process request for {request.location_id}")
    
    try:
        checkin_service = get_checkin_service()
        
        # Helper to get frame
        def get_frame(cam_id):
            if not cam_id: return None
            # Get from active cameras
            cam_state = active_cameras.get(cam_id)
            if cam_state:
                streamer = cam_state.get("streamer")
                if streamer:
                    return streamer.get_capture_frame() if hasattr(streamer, 'get_capture_frame') else streamer.last_frame
            return None

        # Capture frames
        front_frame = get_frame(request.front_camera_id)
        side_frame = get_frame(request.side_camera_id) if request.side_camera_id else None
        top_frame = get_frame(request.top_camera_id) if request.top_camera_id else None

        if front_frame is None:
            if side_frame is not None:
                # Use side as fallback for front (plate detection)
                print(f"[API] Front camera failed ({request.front_camera_id}), using side camera as fallback")
                front_frame = side_frame
            elif top_frame is not None:
                 print(f"[API] Both front and side failed, using top as fallback")
                 front_frame = top_frame
            else:
                return CaptureResponse(
                    success=False, 
                    error=f"Không thể chụp hình từ bất kỳ camera nào. Kiểm tra kết nối Camera: {request.front_camera_id}",
                    reason="capture_failed"
                )

        # Fallback if side camera fails or not provided (use front as dummy)
        if side_frame is None:
            side_frame = front_frame
            
        # Save frames to temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as front_temp:
            await asyncio.to_thread(cv2.imwrite, front_temp.name, front_frame)
            front_path = Path(front_temp.name)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as side_temp:
            await asyncio.to_thread(cv2.imwrite, side_temp.name, side_frame)
            side_path = Path(side_temp.name)
            
        top_path = None
        if top_frame is not None:
             with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as top_temp:
                await asyncio.to_thread(cv2.imwrite, top_temp.name, top_frame)
                top_path = Path(top_temp.name)

        from backend.data_process.config import get_locations
        locations = get_locations()
        location_obj = next((l for l in locations if l.id == request.location_id or l.name == request.location_id), None)
        location_tag = location_obj.tag if location_obj else "Cơ bản"

        # Helper to get cam info and functions
        def get_cam_info(cam_id):
            if not cam_id: return None
            # Fetch camera configuration to get its functions
            from backend.camera.logic import CameraLogic
            cam_logic = CameraLogic()
            cam_config = cam_logic.get_camera_by_id(cam_id)
            
            functions = []
            if cam_config:
                from backend.data_process.config import get_cam_types
                cam_types = get_cam_types()
                type_obj = next((t for t in cam_types if t.name == cam_config.get('type')), None)
                if type_obj:
                    # 'functions' field in CSV might be semicolon-separated
                    funcs_raw = type_obj.functions
                    if isinstance(funcs_raw, str):
                        functions = funcs_raw.split(';')
                    elif isinstance(funcs_raw, list):
                        functions = funcs_raw
            
            return {
                "name": cam_config.get('name', 'Unknown') if cam_config else "Unknown",
                "functions": [f for f in functions if f]
            }

        # 1. Front Camera
        front_info = get_cam_info(request.front_camera_id)
        
        # Prepare images list for workflow
        images_to_process = [
            {
                "path": front_path, 
                "cam_name": front_info["name"] if front_info else "FrontCam", 
                "functions": front_info["functions"] if front_info else ["plate", "truck", "color"]
            }
        ]
        
        # 2. Side Camera
        if side_path:
            side_info = get_cam_info(request.side_camera_id)
            images_to_process.append({
                "path": side_path, 
                "cam_name": side_info["name"] if side_info else "SideCam", 
                "functions": side_info["functions"] if side_info else ["wheel"]
            })
            
        # 3. Top Camera
        if top_path:
            top_info = get_cam_info(request.top_camera_id)
            images_to_process.append({
                "path": top_path, 
                "cam_name": top_info["name"] if top_info else "TopCam", 
                "functions": top_info["functions"] if top_info else ["volume_top_down"]
            })

        # Determine if Check-In or Check-Out
        if location_tag == "Cổng ra":
             # Process as Check-Out
             from backend.workflow.checkout import get_checkout_service
             checkout_service = get_checkout_service()
             result_dict = await checkout_service.process_checkout(
                 front_image_path=front_path,
                 location_id=request.location_id
             )
             # Wrap in CaptureResponse format
             folder_path = result_dict.get("folder_path")
             front_url = None
             if folder_path:
                 folder = Path(folder_path)
                 if folder.exists():
                     imgs = list(folder.glob("*.jpg"))
                     if imgs:
                         parent_name = folder.parent.name
                         folder_name = folder.name
                         front_url = f"/api/images/{parent_name}/{folder_name}/{imgs[0].name}"

             return CaptureResponse(
                 success=True,
                 uuid=result_dict.get("uuid"),
                 plate=result_dict.get("plate"),
                 status=result_dict.get("status"),
                 folder_path=folder_path,
                 front_image_url=front_url,
                 history_volume=result_dict.get("history_volume"),
                 duration=time.time() - start_total,
                 is_checkout=True
             )

        # Default to Check-In
        date_str = datetime.now().strftime("%d-%m-%Y")
        result = await checkin_service.process_checkin(
            images=images_to_process,
            location_id=request.location_id,
            date_str=date_str
        )
        
        # --- Volume Estimation ---
        volume_val = None
        is_volume_loc = location_tag in [
            "Tính thể tích vật liệu (Trên dưới)", 
            "Tính thể tích vật liệu (Trái phải)",
            LocationTag.VOLUME_TOP_DOWN.value,
            LocationTag.VOLUME_LEFT_RIGHT.value
        ]

        if is_volume_loc and top_path and result.folder_path:
            # Save top image to folder
            folder = Path(result.folder_path)
            # Use cam name for the top image filename
            top_cam_name = top_info["name"] if top_info else "TopCam"
            shutil.copy2(top_path, folder / f"{top_cam_name}_volume.jpg")
            
            from backend.model_process.control import orchestrator
            
            # Paths for calibration and backgrounds
            calib_dir = Path("database/calibration")
            bg_dir = Path("database/backgrounds")
            
            # 1. Resolve Calibration Files
            # Priority: calib_side_{cam_id}.json -> calib_side.json -> default
            side_cam_id = request.side_camera_id or "default"
            top_cam_id = request.top_camera_id or "default"
            
            calib_side = calib_dir / f"calib_side_{side_cam_id}.json"
            if not calib_side.exists():
                calib_side = calib_dir / "calib_side.json"
                
            calib_top = calib_dir / f"calib_top_{top_cam_id}.json"
            if not calib_top.exists():
                calib_top = calib_dir / "calib_topdown.json"
                
            # 2. Resolve Background Image
            # Priority: bg_{top_cam_id}.jpg -> any jpg in backgrounds
            bg_image = bg_dir / f"bg_{top_cam_id}.jpg"
            if not bg_image.exists():
                bgs = list(bg_dir.glob("*.jpg"))
                bg_image = bgs[0] if bgs else None
            
            if calib_side.exists() and calib_top.exists() and bg_image:
                print(f"[API] Starting volume estimation for location {request.location_id}...")
                try:
                    volume_res = await orchestrator.process_volume(
                        side_image_path=side_path,
                        top_fg_image_path=top_path,
                        top_bg_image_path=bg_image,
                        side_calib_path=calib_side,
                        top_calib_path=calib_top
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
                                    status_data["volume_data_file"] = "volume_estimation.json"
                                    f.seek(0)
                                    json.dump(status_data, f, indent=4, ensure_ascii=False)
                                    f.truncate()
                                except: pass
                        
                        # Persist to History CSV
                        checkin_service.history_logic.update_record(result.uuid, {
                            'vol_measured': str(volume_val)
                        })
                    else:
                        print(f"[API] Volume estimation failed: {volume_res.get('error') if volume_res else 'Unknown error'}")
                except Exception as ve:
                    print(f"[API] Volume estimation exception: {ve}")
            else:
                missing = []
                if not calib_side.exists(): missing.append("calib_side")
                if not calib_top.exists(): missing.append("calib_top")
                if not bg_image: missing.append("bg_image")
                print(f"[API] Skipping volume estimation, missing: {', '.join(missing)}")
                         
        # Cleanup temp files
        front_path.unlink(missing_ok=True)
        side_path.unlink(missing_ok=True)
        if top_path: top_path.unlink(missing_ok=True)
        
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
                    if "front" in img_name or "plate" in img_name:
                        front_image_url = url
                    elif "side" in img_name or "row-crop" in img_name: # row-crop is usually side
                         if not side_image_url: side_image_url = url # prioritization
                    elif "top" in img_name:
                        top_image_url = url
                
                # Fallback Logic
                if not front_image_url and images:
                    front_image_url = f"/api/images/{parent_name}/{folder_name}/{images[0].name}"
                if not side_image_url and len(images) > 1:
                     side_image_url = f"/api/images/{parent_name}/{folder_name}/{images[1].name}"

        total_duration = time.time() - start_total
        print(f"[API] capture-and-process completed in {total_duration:.2f}s")
        
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
            time_in=result.history_record.get("time_in") if result.history_record else None,
            history_plate=result.history_record.get("plate") if result.history_record else None
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return CaptureResponse(
            success=False,
            error=str(e),
            reason="processing_error"
        )



@checkin_router.post("/process")
async def process_checkin(
    front_image: UploadFile = File(...),
    side_image: UploadFile = File(...),
    location_id: str = Form(...),
    date: Optional[str] = Form(None)
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
        
        # Process check-in
        result = await service.process_checkin(
            front_image_path=front_path,
            side_image_path=side_path,
            location_id=location_id,
            date_str=date
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
            "status": result.status
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
            approved=request.approved
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
    car_history_dir = Path("database/car_history")
    
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
                    pending.append({
                        "uuid": status_data.get("uuid"),
                        "location_id": status_data.get("location_id"),
                        "date": status_data.get("date"),
                        "folder_path": str(car_folder),
                        "plate_number": status_data.get("plate_number"),
                        "color": status_data.get("color"),
                        "wheel_count": status_data.get("wheel_count"),
                        "status": status_data.get("status"),
                        "created_at": status_data.get("created_at")
                    })
    
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
            raise HTTPException(status_code=400, detail="Could not process folder - missing images or invalid format")
        
        return {
            "success": True,
            "uuid": result.uuid,
            "folder_path": result.folder_path,
            "plate_number": result.plate_number,
            "color": result.color,
            "wheel_count": result.wheel_count,
            "status": result.status
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
                    results.append({
                        "folder": car_folder.name,
                        "uuid": result.uuid,
                        "plate_number": result.plate_number,
                        "color": result.color,
                        "wheel_count": result.wheel_count,
                        "status": result.status
                    })
            except Exception as e:
                errors.append({
                    "folder": car_folder.name,
                    "error": str(e)
                })
    
    await service.close()
    
    return {
        "success": True,
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
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
