"""Camera management API endpoints"""
import uuid
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response

from backend.camera_config.camera import ONVIFCameraManager, CameraConfig
from backend.camera_config.streamer import VideoStreamer
from backend.detect_car.detection_service import get_detection_service
from backend import data_process
from backend.api._shared import (
    cameras, get_camera_state,
    CameraConnectRequest, PTZMoveRequest,
    UpdateDetectionModeRequest, UpdateCameraTagRequest
)

camera_router = APIRouter(prefix="/api/cameras", tags=["cameras"])

# Camera Management Endpoints
@camera_router.get("")
async def get_cameras():
    """Get all connected cameras"""
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

@camera_router.post("")
async def save_camera_config(camera: dict):
    """Save or update camera configuration"""
    # Ensure ID
    if 'id' not in camera or not camera['id']:
        camera['id'] = str(uuid.uuid4())
    
    # Resolve Location ID from Location Name
    loc_name = camera.get('location')
    if loc_name:
        locations = data_process.get_locations()
        match = next((l for l in locations if l.get('name') == loc_name), None)
        if match and match.get('id'):
            camera['location_id'] = match['id']
            
    data_process.save_camera(camera)
    return {"success": True, "id": camera['id']}

@camera_router.delete("/{camera_id}")
async def delete_camera(camera_id: str):
    """Delete camera"""
    # Disconnect if active
    if camera_id in cameras:
        cam = cameras[camera_id]
        get_detection_service().unregister_camera(camera_id)
        if cam["streamer"]: cam["streamer"].stop()
        if cam["manager"]: cam["manager"].disconnect()
        del cameras[camera_id]
    
    # Remove from storage
    data_process.delete_camera(camera_id) 
    return {"success": True}

@camera_router.get("/saved")
async def get_saved_cameras():
    """Get all saved camera configurations"""
    saved = data_process.get_all_cameras()
    # Build a lookup of active cameras by IP for reliable matching
    active_by_ip = {cam["config"].ip: (cam_id, cam) for cam_id, cam in cameras.items()}
    
    for cam in saved:
        saved_ip = cam.get('ip')
        if saved_ip in active_by_ip:
            cam_id, active_cam = active_by_ip[saved_ip]
            streamer = active_cam.get("streamer")
            manager = active_cam.get("manager")
            
            if streamer and streamer.is_streaming:
                cam['status'] = 'Online'
            elif manager and manager.connected:
                cam['status'] = 'Connected'
            else:
                cam['status'] = 'Local'
        else:
            cam['status'] = 'Offline'
    return saved

@camera_router.post("/connect")
async def connect_camera(request: CameraConnectRequest):
    """Connect to an ONVIF camera"""
    # Check if already connected
    for cam_id, cam in cameras.items():
        if cam["config"].ip == request.ip:
            return {"success": True, "error": f"Camera {request.ip} already connected", "id": cam_id}
    
    if request.tag and request.tag not in ("front_cam", "side_cam"):
        raise HTTPException(status_code=400, detail="Invalid tag")
    
    config = CameraConfig(ip=request.ip, port=request.port, user=request.user, password=request.password)
    config.name = request.name
    
    manager = ONVIFCameraManager(config)
    
    # Run blocking connection in thread pool with 10 second timeout
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(manager.connect),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        return {"success": False, "error": "Connection timed out after 10 seconds"}
    except Exception as e:
        return {"success": False, "error": f"Connection failed: {str(e)}"}
    
    if result["success"]:
        streamer = VideoStreamer(manager.stream_uri)
        
        # Check if camera already exists in saved cameras by IP - reuse that ID
        existing_cameras = data_process.get_all_cameras()
        existing_cam = next((c for c in existing_cameras if c.get('ip') == request.ip), None)
        
        if existing_cam and existing_cam.get('id'):
            camera_id = existing_cam['id']
        else:
            camera_id = str(uuid.uuid4())
        
        cameras[camera_id] = {"manager": manager, "streamer": streamer, "config": config, "detection_mode": request.detection_mode}
        
        detection_service = get_detection_service()
        detection_service.register_camera(camera_id, streamer, request.tag)
        
        # Update existing record or create new one
        cam_data = {
            'id': camera_id, 'name': request.name, 'ip': request.ip, 'port': request.port,
            'username': request.user, 'password': request.password, 'profile_token': manager.profile_token,
            'stream_uri': manager.stream_uri, 'resolution_width': result.get('resolution', {}).get('width'),
            'resolution_height': result.get('resolution', {}).get('height'), 'tag': request.tag,
            'detection_mode': request.detection_mode
        }
        
        # Preserve existing location info from DB if it exists
        cam_code = None
        cam_location = None
        if existing_cam:
             cam_data['location'] = existing_cam.get('location')
             cam_data['location_id'] = existing_cam.get('location_id')
             cam_data['type'] = existing_cam.get('type')
             cam_data['brand'] = existing_cam.get('brand')
             cam_code = existing_cam.get('cam_id')
             cam_location = existing_cam.get('location')
        
        # Set camera info on streamer for image naming
        streamer.set_camera_info(cam_code=cam_code, location=cam_location)
        
        data_process.save_camera(cam_data)
        result["id"] = camera_id
    return result

@camera_router.post("/{camera_id}/disconnect")
async def disconnect_camera(camera_id: str):
    """Disconnect camera"""
    cam = get_camera_state(camera_id)
    get_detection_service().unregister_camera(camera_id)
    if cam["streamer"]: cam["streamer"].stop()
    if cam["manager"]: cam["manager"].disconnect()
    del cameras[camera_id]
    return {"success": True}

@camera_router.post("/{camera_id}/detection_mode")
async def update_detection_mode(camera_id: str, request: UpdateDetectionModeRequest):
    """Update camera detection mode"""
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
    return {"success": True, "detection_mode": request.detection_mode}

@camera_router.post("/{camera_id}/tag")
async def update_camera_tag(camera_id: str, request: UpdateCameraTagRequest):
    """Update camera tag"""
    get_camera_state(camera_id)
    if request.tag and request.tag not in ("front_cam", "side_cam"):
        raise HTTPException(status_code=400, detail="Invalid tag")
    get_detection_service().set_camera_tag(camera_id, request.tag)
    return {"success": True, "tag": request.tag}

# Stream Endpoints
@camera_router.post("/{camera_id}/stream/start")
async def start_stream(camera_id: str):
    """Start video stream"""
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="Streamer not initialized")
    return {"success": streamer.start()}

@camera_router.post("/{camera_id}/stream/stop")
async def stop_stream(camera_id: str):
    """Stop video stream"""
    streamer = get_camera_state(camera_id)["streamer"]
    if streamer: streamer.stop()
    return {"success": True}

@camera_router.get("/{camera_id}/stream")
async def video_feed(camera_id: str):
    """Get video feed (MJPEG stream)"""
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
    """Get single frame snapshot"""
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="No streamer")
    jpeg_bytes = streamer.get_frame_jpeg()
    if not jpeg_bytes:
        raise HTTPException(status_code=500, detail="Could not capture frame")
    return Response(content=jpeg_bytes, media_type="image/jpeg")

@camera_router.post("/{camera_id}/capture")
async def capture_image(camera_id: str):
    """Capture image to disk"""
    streamer = get_camera_state(camera_id)["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="No streamer")
    return streamer.capture_image()

# PTZ Control Endpoints
@camera_router.post("/{camera_id}/ptz/up")
async def ptz_up(camera_id: str, request: PTZMoveRequest):
    """Move camera up"""
    return get_camera_state(camera_id)["manager"].move_up(request.speed)

@camera_router.post("/{camera_id}/ptz/down")
async def ptz_down(camera_id: str, request: PTZMoveRequest):
    """Move camera down"""
    return get_camera_state(camera_id)["manager"].move_down(request.speed)

@camera_router.post("/{camera_id}/ptz/left")
async def ptz_left(camera_id: str, request: PTZMoveRequest):
    """Move camera left"""
    return get_camera_state(camera_id)["manager"].move_left(request.speed)

@camera_router.post("/{camera_id}/ptz/right")
async def ptz_right(camera_id: str, request: PTZMoveRequest):
    """Move camera right"""
    return get_camera_state(camera_id)["manager"].move_right(request.speed)

@camera_router.post("/{camera_id}/ptz/zoom-in")
async def ptz_zoom_in(camera_id: str, request: PTZMoveRequest):
    """Zoom in"""
    return get_camera_state(camera_id)["manager"].zoom_in(request.speed)

@camera_router.post("/{camera_id}/ptz/zoom-out")
async def ptz_zoom_out(camera_id: str, request: PTZMoveRequest):
    """Zoom out"""
    return get_camera_state(camera_id)["manager"].zoom_out(request.speed)

@camera_router.post("/{camera_id}/ptz/stop")
async def ptz_stop(camera_id: str):
    """Stop PTZ movement"""
    return get_camera_state(camera_id)["manager"].ptz_stop()

# Detection Endpoints
@camera_router.get("/{camera_id}/detect")
async def detect_car(camera_id: str):
    """Run vehicle detection"""
    get_camera_state(camera_id)
    return get_detection_service().detect(camera_id)

@camera_router. post("/{camera_id}/capture_with_detection")
async def capture_with_detection(camera_id: str, force: bool = False):
    """Capture image with vehicle detection"""
    get_camera_state(camera_id)
    return get_detection_service().capture_with_detection(camera_id, force=force)
