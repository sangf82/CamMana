from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import asyncio
import logging

from .logic import CameraLogic
from .connection import CameraConnection, CameraConnectionConfig
from .capture import VideoStreamer
from .control import PTZController

# Shared state
active_cameras: Dict[str, Dict[str, Any]] = {}
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])
logic = CameraLogic()

# Models
class CameraBase(BaseModel):
    name: str
    ip: str
    port: int = 80
    username: Optional[str] = ""
    password: Optional[str] = ""
    location: Optional[str] = ""
    location_id: Optional[str] = "" # Link to location
    type: Optional[str] = ""
    brand: Optional[str] = ""
    tag: Optional[str] = ""
    # Add other fields as per _common.py headers if needed

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    location: Optional[str] = None
    location_id: Optional[str] = None
    type: Optional[str] = None
    brand: Optional[str] = None
    tag: Optional[str] = None

class CameraResponse(CameraBase):
    id: str # Internal ID
    cam_id: Optional[str] = None # Optional external ID
    status: str = "Offline"

class PTZRequest(BaseModel):
    speed: float = 0.5
    
@router.get("", response_model=List[CameraResponse])
def get_cameras():
    cameras = logic.get_cameras()
    # Enrich with status
    enriched = []
    for c in cameras:
        # Normalize fields for response 
        # (ensure 'port' is int, etc if CSV stored as str)
        try:
            c['port'] = int(c.get('port', 80))
        except:
            c['port'] = 80
            
        c_id = c.get('cam_id') or c.get('id')
        status = "Offline"
        if c_id in active_cameras:
            if active_cameras[c_id]['connection'].connected:
                status = "Connected"
            if active_cameras[c_id]['streamer'].is_streaming:
                status = "Online"
        
        c['status'] = status
        enriched.append(c)
    return enriched

@router.post("", response_model=CameraResponse)
def add_camera(cam: CameraBase):
    try:
        data = cam.dict()
        # Set default status to Idle for new cameras
        if 'status' not in data or not data['status']:
            data['status'] = 'Idle'
        new_cam = logic.add_camera(data)
        # Ensure correct return types
        try: new_cam['port'] = int(new_cam.get('port', 80))
        except: new_cam['port'] = 80
        return {**new_cam, "status": new_cam.get('status', 'Idle')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{cam_id}", response_model=CameraResponse)
def update_camera(cam_id: str, cam: CameraUpdate):
    updated = logic.update_camera(cam_id, cam.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # If active, might need reconnect? For now, user must manually reconnect.
    status = "Offline"
    if cam_id in active_cameras:
         # Check status
         if active_cameras[cam_id]['connection'].connected: status = "Connected"
         if active_cameras[cam_id]['streamer'].is_streaming: status = "Online"
            
    # Normalize types
    try: updated['port'] = int(updated.get('port', 80))
    except: updated['port'] = 80
    
    return {**updated, "status": status}

@router.delete("/{cam_id}")
def delete_camera(cam_id: str):
    if cam_id in active_cameras:
        _disconnect_camera(cam_id)
    success = logic.delete_camera(cam_id)
    if not success:
         raise HTTPException(status_code=404, detail="Camera not found")
    return {"message": "Deleted successfully"}

# Connect/Disconnect
@router.post("/{cam_id}/connect")
async def connect_camera(cam_id: str):
    cameras = logic.get_cameras()
    cam_data = next((c for c in cameras if c.get('cam_id') == cam_id or c.get('id') == cam_id), None)
    if not cam_data:
        raise HTTPException(status_code=404, detail="Camera not found")

    ip = cam_data.get('ip', '')
    try: port = int(cam_data.get('port', 80))
    except: port = 80
    
    config = CameraConnectionConfig(
        ip=ip,
        port=port,
        user=cam_data.get('username', ''),  # Use username field
        password=cam_data.get('password', '')
    )
    
    conn = CameraConnection(config)
    res = await asyncio.to_thread(conn.connect)
    
    if not res['success']:
        raise HTTPException(status_code=400, detail=res['error'])
    
    # Start Streamer
    streamer = VideoStreamer(res['stream_uri'])
    streamer.set_camera_info(name=cam_data.get('name'), location=cam_data.get('location'))
    success = streamer.start()
    
    if not success:
        conn.disconnect()
        raise HTTPException(status_code=500, detail="Failed to start stream")

    # Use the same ID for active_cameras key
    active_cameras[cam_id] = {
        "connection": conn,
        "streamer": streamer,
        "ptz": PTZController(conn)
    }
    
    # Update status in CSV
    logic.update_camera(cam_id, {'status': 'Online'})
    
    return {"success": True, "details": res}

@router.post("/{cam_id}/disconnect")
def disconnect_camera(cam_id: str):
    _disconnect_camera(cam_id)
    return {"success": True}

def _disconnect_camera(cam_id: str):
    if cam_id in active_cameras:
        active_cameras[cam_id]['streamer'].stop()
        active_cameras[cam_id]['connection'].disconnect()
        del active_cameras[cam_id]
        
        # Update status in CSV
        logic.update_camera(cam_id, {'status': 'Offline'})

# Streaming
@router.get("/{cam_id}/stream")
async def video_feed(cam_id: str):
    if cam_id not in active_cameras:
        # Try auto-connect?
        await connect_camera(cam_id)
    
    if cam_id not in active_cameras:
        raise HTTPException(404, "Camera not available")

    streamer = active_cameras[cam_id]['streamer']
    if not streamer.is_streaming:
         streamer.start()

    async def gen():
        try:
            async for frame in streamer.generate_frames():
                yield frame
        except Exception: pass

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

# PTZ
@router.post("/{cam_id}/ptz/{action}")
def ptz_action(cam_id: str, action: str, req: PTZRequest):
    if cam_id not in active_cameras:
        raise HTTPException(404, "Camera not connected")
    
    ptz = active_cameras[cam_id]['ptz']
    
    if action == "up": return ptz.move(tilt=req.speed)
    if action == "down": return ptz.move(tilt=-req.speed)
    if action == "left": return ptz.move(pan=-req.speed)
    if action == "right": return ptz.move(pan=req.speed)
    if action == "zoom_in": return ptz.move(zoom=req.speed)
    if action == "zoom_out": return ptz.move(zoom=-req.speed)
    if action == "stop": return ptz.stop()
    
    raise HTTPException(400, "Invalid action")

# Capture
@router.post("/{cam_id}/capture")
def capture_image(cam_id: str):
    if cam_id not in active_cameras:
         raise HTTPException(404, "Camera not connected")
    return active_cameras[cam_id]['streamer'].capture_image()
