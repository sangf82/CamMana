"""
FastAPI Backend Server for CamMana
Handles camera control, video streaming, and API endpoints
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from backend.camera import ONVIFCameraManager, CameraConfig
from backend.streamer import VideoStreamer


# Determine if running as frozen exe
def get_static_dir():
    """Get the path to static files (built Next.js)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent
    
    static_path = base_path / "frontend" / "out"
    return static_path if static_path.exists() else None


# Initialize FastAPI app
app = FastAPI(
    title="CamMana API",
    description="ONVIF Camera Control & Streaming API",
    version="2.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
cameras = {}  # Format: {id: {"manager": manager, "streamer": streamer, "config": config}}

# Request models
class CameraConnectRequest(BaseModel):
    ip: str
    port: int = 8899
    user: str = "admin"
    password: str = ""
    name: str = "Camera"

class PTZMoveRequest(BaseModel):
    speed: float = 0.5


# API Endpoints

@app.get("/api/cameras")
async def get_cameras():
    """Get list of active cameras"""
    return [
        {
            "id": cam_id,
            "name": cam["config"].name,
            "ip": cam["config"].ip,
            "connected": cam["manager"].connected,
            "streaming": cam["streamer"].is_streaming if cam["streamer"] else False,
            "stream_uri": cam["manager"].stream_uri
        }
        for cam_id, cam in cameras.items()
    ]


@app.post("/api/connect")
async def connect_camera(request: CameraConnectRequest):
    """Connect to a new camera"""
    import uuid
    
    # Check if already connected by IP
    for cam_id, cam in cameras.items():
        if cam["config"].ip == request.ip:
            return {"success": False, "error": f"Camera {request.ip} already connected", "id": cam_id}

    config = CameraConfig(
        ip=request.ip,
        port=request.port,
        user=request.user,
        password=request.password
    )
    # Store name in config for retrieval
    config.name = request.name  
    
    manager = ONVIFCameraManager(config)
    result = manager.connect()
    
    if result["success"]:
        # Initialize video streamer
        streamer = VideoStreamer(manager.stream_uri)
        # Generate unique ID
        camera_id = str(uuid.uuid4())
        
        cameras[camera_id] = {
            "manager": manager,
            "streamer": streamer,
            "config": config
        }
        result["id"] = camera_id
    
    return result


@app.post("/api/cameras/{camera_id}/disconnect")
async def disconnect_camera(camera_id: str):
    """Disconnect a specific camera"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    cam = cameras[camera_id]
    if cam["streamer"]:
        cam["streamer"].stop()
    
    if cam["manager"]:
        cam["manager"].disconnect()
    
    del cameras[camera_id]
    return {"success": True}


@app.post("/api/cameras/{camera_id}/stream/start")
async def start_stream(camera_id: str):
    """Start video streaming for specific camera"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    streamer = cameras[camera_id]["streamer"]
    if not streamer:
        raise HTTPException(status_code=400, detail="Streamer not initialized")
    
    success = streamer.start()
    return {"success": success}


@app.post("/api/cameras/{camera_id}/stream/stop")
async def stop_stream(camera_id: str):
    """Stop video streaming for specific camera"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    streamer = cameras[camera_id]["streamer"]
    if streamer:
        streamer.stop()
    
    return {"success": True}


@app.get("/api/cameras/{camera_id}/stream")
async def video_feed(camera_id: str):
    """MJPEG video stream endpoint for specific camera"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    streamer = cameras[camera_id]["streamer"]
    if not streamer or not streamer.is_streaming:
        # Try to auto-start if not streaming
        if streamer:
            streamer.start()
        
        if not streamer or not streamer.is_streaming:
             raise HTTPException(status_code=400, detail="Stream not started")
    
    return StreamingResponse(
        streamer.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/api/cameras/{camera_id}/capture")
async def capture_image(camera_id: str):
    """Capture current frame from specific camera"""
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    streamer = cameras[camera_id]["streamer"]
    if not streamer:
         raise HTTPException(status_code=400, detail="No streamer")
         
    return streamer.capture_image()


# PTZ Control Endpoints

def get_manager(camera_id: str):
    if camera_id not in cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras[camera_id]["manager"]

@app.post("/api/cameras/{camera_id}/ptz/up")
async def ptz_up(camera_id: str, request: PTZMoveRequest):
    return get_manager(camera_id).move_up(request.speed)

@app.post("/api/cameras/{camera_id}/ptz/down")
async def ptz_down(camera_id: str, request: PTZMoveRequest):
    return get_manager(camera_id).move_down(request.speed)

@app.post("/api/cameras/{camera_id}/ptz/left")
async def ptz_left(camera_id: str, request: PTZMoveRequest):
    return get_manager(camera_id).move_left(request.speed)

@app.post("/api/cameras/{camera_id}/ptz/right")
async def ptz_right(camera_id: str, request: PTZMoveRequest):
    return get_manager(camera_id).move_right(request.speed)

@app.post("/api/cameras/{camera_id}/ptz/zoom-in")
async def ptz_zoom_in(camera_id: str, request: PTZMoveRequest):
    return get_manager(camera_id).zoom_in(request.speed)

@app.post("/api/cameras/{camera_id}/ptz/zoom-out")
async def ptz_zoom_out(camera_id: str, request: PTZMoveRequest):
    return get_manager(camera_id).zoom_out(request.speed)

@app.post("/api/cameras/{camera_id}/ptz/stop")
async def ptz_stop(camera_id: str):
    return get_manager(camera_id).ptz_stop()


# Mount static files for production (built Next.js)
static_dir = get_static_dir()
if static_dir:
    # Serve static assets
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next_static")
    
    # Serve index.html for root path
    @app.get("/")
    async def serve_index():
        return FileResponse(static_dir / "index.html")
    
    # Catch-all for client-side routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Skip API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Try to serve the file directly
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Fall back to index.html for SPA routing
        return FileResponse(static_dir / "index.html")


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI server"""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()

