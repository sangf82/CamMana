"""API Layer - Thin API layer that delegates to service modules"""
import os
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel

from backend.camera_config.camera import ONVIFCameraManager, CameraConfig
from backend.camera_config.streamer import VideoStreamer
from backend.detect_car.detection_service import get_detection_service
from backend.data_process import db, csv_storage

# Request Models
class CameraConnectRequest(BaseModel):
    ip: str
    port: int = 8899
    user: str = "admin"
    password: str = ""
    name: str = "Camera"
    tag: Optional[str] = None
    detection_mode: str = "disabled"

class PTZMoveRequest(BaseModel):
    speed: float = 0.5

class UpdateDetectionModeRequest(BaseModel):
    detection_mode: str

class UpdateCameraTagRequest(BaseModel):
    tag: Optional[str]

# Routers
camera_router = APIRouter(prefix="/api/cameras", tags=["cameras"])
schedule_router = APIRouter(prefix="/api", tags=["schedule"])
detection_router = APIRouter(prefix="/api", tags=["detection"])

# In-memory camera state
cameras = {}

def get_camera_state(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]

# Camera Endpoints
@camera_router.get("")
async def get_cameras():
    result = []
    detection_service = get_detection_service()
    for cam_id, cam in cameras.items():
        streamer = cam["streamer"]
        result.append({
            "id": cam_id,
            "name": cam["config"].name,
            "ip": cam["config"].ip,
            "connected": cam["manager"].connected,
            "streaming": streamer.is_streaming if streamer else False,
            "stream_uri": cam["manager"].stream_uri,
            "tag": detection_service._camera_tags.get(cam_id),
            "detection_mode": cam.get("detection_mode", "disabled"),
            "auto_detection_running": detection_service.is_auto_detection_running(cam_id),
            "stream_info": streamer.get_stream_info() if streamer and streamer.is_streaming else None
        })
    return result

@camera_router.get("/saved")
async def get_saved_cameras():
    return db.get_all_cameras()

@camera_router.post("/connect")
async def connect_camera(request: CameraConnectRequest):
    for cam_id, cam in cameras.items():
        if cam["config"].ip == request.ip:
            return {"success": False, "error": f"Camera {request.ip} already connected", "id": cam_id}
    
    if request.tag and request.tag not in ("front_cam", "side_cam"):
        raise HTTPException(status_code=400, detail="Invalid tag")
    
    config = CameraConfig(ip=request.ip, port=request.port, user=request.user, password=request.password)
    config.name = request.name
    
    manager = ONVIFCameraManager(config)
    result = manager.connect()
    
    if result["success"]:
        streamer = VideoStreamer(manager.stream_uri)
        camera_id = str(uuid.uuid4())
        
        cameras[camera_id] = {"manager": manager, "streamer": streamer, "config": config, "detection_mode": request.detection_mode}
        
        detection_service = get_detection_service()
        detection_service.register_camera(camera_id, streamer, request.tag)
        
        db.save_camera({
            'id': camera_id, 'name': request.name, 'ip': request.ip, 'port': request.port,
            'username': request.user, 'password': request.password, 'profile_token': manager.profile_token,
            'stream_uri': manager.stream_uri, 'resolution_width': result.get('resolution', {}).get('width'),
            'resolution_height': result.get('resolution', {}).get('height'), 'tag': request.tag,
            'detection_mode': request.detection_mode
        })
        result["id"] = camera_id
    return result

@camera_router.post("/{camera_id}/disconnect")
async def disconnect_camera(camera_id: str):
    cam = get_camera_state(camera_id)
    get_detection_service().unregister_camera(camera_id)
    if cam["streamer"]: cam["streamer"].stop()
    if cam["manager"]: cam["manager"].disconnect()
    del cameras[camera_id]
    return {"success": True}

@camera_router.post("/{camera_id}/detection_mode")
async def update_detection_mode(camera_id: str, request: UpdateDetectionModeRequest):
    cam = get_camera_state(camera_id)
    if request.detection_mode not in ("auto", "manual", "disabled"):
        raise HTTPException(status_code=400, detail="Invalid detection mode")
    
    detection_service = get_detection_service()
    old_mode = cam.get("detection_mode", "disabled")
    
    if request.detection_mode == "auto" and old_mode != "auto":
        detection_service.start_auto_detection(camera_id)
    elif old_mode == "auto" and request.detection_mode != "auto":
        detection_service.stop_auto_detection(camera_id)
    
    cam["detection_mode"] = request.detection_mode
    db.update_camera_detection_mode(camera_id, request.detection_mode)
    return {"success": True, "detection_mode": request.detection_mode}

@camera_router.post("/{camera_id}/tag")
async def update_camera_tag(camera_id: str, request: UpdateCameraTagRequest):
    get_camera_state(camera_id)
    if request.tag and request.tag not in ("front_cam", "side_cam"):
        raise HTTPException(status_code=400, detail="Invalid tag")
    get_detection_service().set_camera_tag(camera_id, request.tag)
    return {"success": True, "tag": request.tag}

# Stream Endpoints
@camera_router.post("/{camera_id}/stream/start")
async def start_stream(camera_id: str):
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="Streamer not initialized")
    return {"success": streamer.start()}

@camera_router.post("/{camera_id}/stream/stop")
async def stop_stream(camera_id: str):
    streamer = get_camera_state(camera_id)["streamer"]
    if streamer: streamer.stop()
    return {"success": True}

@camera_router.get("/{camera_id}/stream")
async def video_feed(camera_id: str):
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer or not streamer.is_streaming:
        if streamer: streamer.start()
        if not streamer or not streamer.is_streaming:
            raise HTTPException(status_code=400, detail="Stream not started")
    
    async def safe_generate():
        try:
            async for frame in streamer.generate_frames():
                yield frame
        except (GeneratorExit, Exception):
            pass
    
    return StreamingResponse(safe_generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@camera_router.get("/{camera_id}/snapshot")
async def get_snapshot(camera_id: str):
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="No streamer")
    jpeg_bytes = streamer.get_frame_jpeg()
    if not jpeg_bytes:
        raise HTTPException(status_code=500, detail="Could not capture frame")
    return Response(content=jpeg_bytes, media_type="image/jpeg")

@camera_router.post("/{camera_id}/capture")
async def capture_image(camera_id: str):
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="No streamer")
    return streamer.capture_image()

# PTZ Control Endpoints
@camera_router.post("/{camera_id}/ptz/up")
async def ptz_up(camera_id: str, request: PTZMoveRequest):
    return get_camera_state(camera_id)["manager"].move_up(request.speed)

@camera_router.post("/{camera_id}/ptz/down")
async def ptz_down(camera_id: str, request: PTZMoveRequest):
    return get_camera_state(camera_id)["manager"].move_down(request.speed)

@camera_router.post("/{camera_id}/ptz/left")
async def ptz_left(camera_id: str, request: PTZMoveRequest):
    return get_camera_state(camera_id)["manager"].move_left(request.speed)

@camera_router.post("/{camera_id}/ptz/right")
async def ptz_right(camera_id: str, request: PTZMoveRequest):
    return get_camera_state(camera_id)["manager"].move_right(request.speed)

@camera_router.post("/{camera_id}/ptz/zoom-in")
async def ptz_zoom_in(camera_id: str, request: PTZMoveRequest):
    return get_camera_state(camera_id)["manager"].zoom_in(request.speed)

@camera_router.post("/{camera_id}/ptz/zoom-out")
async def ptz_zoom_out(camera_id: str, request: PTZMoveRequest):
    return get_camera_state(camera_id)["manager"].zoom_out(request.speed)

@camera_router.post("/{camera_id}/ptz/stop")
async def ptz_stop(camera_id: str):
    return get_camera_state(camera_id)["manager"].ptz_stop()

# Detection Endpoints
@camera_router.get("/{camera_id}/detect")
async def detect_car(camera_id: str):
    get_camera_state(camera_id)
    return get_detection_service().detect(camera_id)

@camera_router.post("/{camera_id}/capture_with_detection")
async def capture_with_detection(camera_id: str, force: bool = False):
    get_camera_state(camera_id)
    return get_detection_service().capture_with_detection(camera_id, force=force)

@detection_router.get("/captured_cars")
async def get_captured_cars(limit: int = 50, date: Optional[str] = None):
    return csv_storage.get_captured_cars(date=date, limit=limit)

@detection_router.get("/captured_cars/search")
async def search_captured_cars(plate: str, date: Optional[str] = None):
    return csv_storage.search_by_plate(plate, date=date)

@detection_router.get("/detection_logs")
async def get_detection_logs(camera_id: Optional[str] = None, date: Optional[str] = None, limit: int = 100):
    return csv_storage.get_detection_logs(camera_id=camera_id, date=date, limit=limit)

# Schedule Endpoints
@schedule_router.get("/schedule")
async def get_schedule():
    try:
        import pandas as pd
        import numpy as np
        
        file_path = os.getenv("SCHEDULE_FILE_PATH", "database/schedule/CCN_template.xlsx")
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Schedule file not found: {file_path}")
        
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        
        rename_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'stt' in col_lower: rename_map[col] = 'stt'
            elif 'thời gian' in col_lower or 'measure time' in col_lower: rename_map[col] = 'time_in'
            elif 'biển số' in col_lower or 'plate' in col_lower: rename_map[col] = 'plate'
            elif 'loại xe' in col_lower or 'truck model' in col_lower: rename_map[col] = 'vehicle_type'
            elif 'kích thước' in col_lower: rename_map[col] = 'dimensions'
            elif 'thể tích' in col_lower: rename_map[col] = 'volume'
            elif 'trạng thái' in col_lower or 'status' in col_lower: rename_map[col] = 'status_validity'
            elif 'ghi chú' in col_lower or 'notes' in col_lower: rename_map[col] = 'notes'
        
        df.rename(columns=rename_map, inplace=True)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df = df.astype(object).where(pd.notnull(df), None)
        if 'time_in' in df.columns:
            df['time_in'] = df['time_in'].astype(str)
        
        return df.to_dict(orient='records')
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@schedule_router.post("/schedule/upload")
async def upload_schedule(file: UploadFile = File(...)):
    try:
        file_path = os.getenv("SCHEDULE_FILE_PATH", "database/schedule/CCN_template.xlsx")
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        return {"success": True, "filename": file.filename}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
