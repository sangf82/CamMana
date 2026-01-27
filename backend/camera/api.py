from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import asyncio
import logging

from backend.api.user import get_current_user
from backend.schemas import User as UserSchema
from .logic import CameraLogic
from .connection import CameraConnection, CameraConnectionConfig
from .capture import VideoStreamer
from .control import PTZController
from backend.api._shared import cameras as active_cameras
from backend.data_process.sync.proxy import is_client_mode, proxy_get, proxy_post, proxy_put, proxy_delete

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

from backend.data_process.camera_type.logic import CameraTypeLogic

class CameraResponse(CameraBase):
    id: str # Internal ID
    cam_id: Optional[str] = None # Optional external ID
    status: str = "Offline"
    functions: List[str] = []

class PTZRequest(BaseModel):
    speed: float = 0.5
    
@router.get("")
async def get_cameras(user: UserSchema = Depends(get_current_user)):
    """Get all cameras. Proxies to Master when in Client mode."""
    # Proxy to master if in client mode
    if is_client_mode():
        logger.info("Client mode: Fetching cameras from master")
        result = await proxy_get("/api/cameras")
        if result is not None:
            return result
    
    all_cameras = logic.get_cameras()
    
    # Get functions mapping
    types_logic = CameraTypeLogic()
    types_map = {t['name']: t['functions'] for t in types_logic.get_types()}

    # All authenticated users can see all cameras
    filtered = all_cameras

    # Enrich with status
    enriched = []
    for c in filtered:
        # Normalize fields for response 
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
        
        # Populate functions
        funcs = types_map.get(c.get('type'), [])
        if isinstance(funcs, str):
            c['functions'] = funcs.split(';')
        elif isinstance(funcs, list):
            c['functions'] = funcs
        else:
            c['functions'] = []
            
        enriched.append(c)
    return enriched


@router.post("")
async def add_camera(cam: CameraBase, user: UserSchema = Depends(get_current_user)):
    """Add a new camera. Proxies to Master when in Client mode."""
    if user.role != "admin" and not user.can_manage_cameras:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Proxy to master if in client mode
    if is_client_mode():
        logger.info("Client mode: Adding camera via master")
        result = await proxy_post("/api/cameras", cam.dict())
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    try:
        data = cam.dict()
        if 'status' not in data or not data['status']:
            data['status'] = 'Idle'
        new_cam = logic.add_camera(data)
        try: new_cam['port'] = int(new_cam.get('port', 80))
        except: new_cam['port'] = 80
        return {**new_cam, "status": new_cam.get('status', 'Idle')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{cam_id}")
async def update_camera(cam_id: str, cam: CameraUpdate, user: UserSchema = Depends(get_current_user)):
    """Update a camera. Proxies to Master when in Client mode."""
    if user.role != "admin" and not user.can_manage_cameras:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Proxy to master if in client mode
    if is_client_mode():
        logger.info(f"Client mode: Updating camera {cam_id} via master")
        result = await proxy_put(f"/api/cameras/{cam_id}", cam.dict(exclude_unset=True))
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    updated = logic.update_camera(cam_id, cam.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    status = "Offline"
    if cam_id in active_cameras:
         if active_cameras[cam_id]['connection'].connected: status = "Connected"
         if active_cameras[cam_id]['streamer'].is_streaming: status = "Online"
            
    try: updated['port'] = int(updated.get('port', 80))
    except: updated['port'] = 80
    
    return {**updated, "status": status}

@router.delete("/{cam_id}")
async def delete_camera(cam_id: str, user: UserSchema = Depends(get_current_user)):
    """Delete a camera. Proxies to Master when in Client mode."""
    if user.role != "admin" and not user.can_manage_cameras:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Proxy to master if in client mode
    if is_client_mode():
        logger.info(f"Client mode: Deleting camera {cam_id} via master")
        success = await proxy_delete(f"/api/cameras/{cam_id}")
        if success:
            return {"message": "Deleted successfully"}
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    if cam_id in active_cameras:
        _disconnect_camera(cam_id)
    success = logic.delete_camera(cam_id)
    if not success:
         raise HTTPException(status_code=404, detail="Camera not found")
    return {"message": "Deleted successfully"}

# Connect/Disconnect
@router.post("/{cam_id}/connect")
async def connect_camera(cam_id: str, user: UserSchema = Depends(get_current_user)):
    if user.role != "admin" and not user.can_manage_cameras:
        raise HTTPException(status_code=403, detail="Permission denied")
        
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
def disconnect_camera(cam_id: str, user: UserSchema = Depends(get_current_user)):
    if user.role != "admin" and not user.can_manage_cameras:
        raise HTTPException(status_code=403, detail="Permission denied")
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
        # Try auto-connect? (requires careful consideration without user object)
        # For now, just raise if not connected
        raise HTTPException(404, "Camera not connected. Please connect from dashboard first.")
    
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
def ptz_action(cam_id: str, action: str, req: PTZRequest, user: UserSchema = Depends(get_current_user)):
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
def capture_image(cam_id: str, user: UserSchema = Depends(get_current_user)):
    if cam_id not in active_cameras:
         raise HTTPException(404, "Camera not connected")
    return active_cameras[cam_id]['streamer'].capture_image()

# Stream Info
@router.get("/{cam_id}/stream-info")
def get_stream_info(cam_id: str, user: UserSchema = Depends(get_current_user)):
    """Get stream resolution and FPS for a connected camera."""
    if cam_id not in active_cameras:
        raise HTTPException(404, "Camera not connected")
    return active_cameras[cam_id]['streamer'].get_stream_info()
