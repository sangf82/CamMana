"""FastAPI Backend Server for CamMana"""
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import settings first
from backend.settings import settings

# Import routers from new modular structure
from backend.camera.config_api import config_router
from backend.workflow.checkin.api import checkin_router
from backend.workflow.checkout.api import checkout_router
from backend.data_process.user.api import user_router
from backend.sync_process import sync_router, system_router, file_sync_router
from backend.data_process.history.api import router as history_router
from backend.data_process.register_car.api import router as registered_car_router
from backend.data_process.location.api import router as location_router
from backend.data_process.camera_type.api import router as camera_type_router
from backend.data_process.report.api import router as report_router
from backend.camera.api import router as camera_router

BACKEND_DIR = Path(__file__).parent


def clean_pycache():
    """Remove all __pycache__ directories in backend folder"""
    count = 0
    for pycache_dir in BACKEND_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                count += 1
            except Exception:
                pass
    if count:
        print(f"[cam_mana] Cleaned {count} __pycache__ directories")


def get_static_dir():
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    static_path = base_path / "frontend" / "out"
    return static_path if static_path.exists() else None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Include routers
    app.include_router(camera_router)
    app.include_router(config_router)
    app.include_router(history_router)
    app.include_router(checkin_router)
    app.include_router(checkout_router)
    app.include_router(registered_car_router)
    app.include_router(location_router)
    app.include_router(camera_type_router)
    app.include_router(report_router)
    app.include_router(user_router)
    app.include_router(sync_router)
    app.include_router(file_sync_router)
    app.include_router(system_router)
    
    # Serve captured car images from car_history folder
    @app.get("/api/images/{date_folder}/{car_folder}/{filename}")
    async def serve_car_image(date_folder: str, car_folder: str, filename: str):
        """Serve captured car images for evidence display"""
        image_path = settings.car_history_dir / date_folder / car_folder / filename
        if image_path.exists() and image_path.is_file():
            return FileResponse(image_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Image not found")
    
    # CI/CD health check endpoint
    @app.get("/api/health")
    async def health_check():
        """Basic health check endpoint"""
        return {"status": "ok", "version": settings.api_version}
    
    # Serve static frontend files
    static_dir = get_static_dir()
    if static_dir:
        app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next_static")
        
        @app.get("/")
        async def serve_index():
            return FileResponse(static_dir / "index.html")
        
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(static_dir / "index.html")
    
    return app


app = create_app()


def initialize_backend():
    """Initialize backend services (schedulers, data sync, etc.)"""
    try:
        # Start Daily Report Scheduler (10 PM)
        from apscheduler.schedulers.background import BackgroundScheduler
        from backend.data_process.report.logic import ReportLogic
        
        def daily_report_job():
            today = datetime.now().strftime("%d-%m-%Y")
            print(f"[cam_mana] Auto-generating daily report for {today}...")
            ReportLogic().generate_report(today)
            
        scheduler = BackgroundScheduler()
        scheduler.add_job(daily_report_job, 'cron', hour=22, minute=0)
        scheduler.start()
        print("[cam_mana] Daily report scheduler started (at 22:00)")
        
        # Start Background Image Scheduler (every 1 hour)
        from backend.model_process.utils.background import background_manager
        background_manager.start_scheduler()
        print("[cam_mana] Background image scheduler started (every 1 hour)")
        
        # Initialize History logic (daily rotation & cleanup)
        from backend.data_process.history.logic import HistoryLogic
        HistoryLogic()
        print("[cam_mana] History logic initialized")
        
        # Sync camera data with locations and camera types
        from backend.data_process._sync import CameraDataSync
        from backend.data_process.location.logic import LocationLogic
        from backend.data_process.camera_type.logic import CameraTypeLogic
        
        locations = LocationLogic().get_locations()
        camtypes = CameraTypeLogic().get_types()
        result = CameraDataSync.full_sync(locations, camtypes)
        if result['locations'] > 0 or result['types'] > 0:
            print(f"[cam_mana] Synced cameras: {result['locations']} locations, {result['types']} types")
        
    except Exception as e:
        print(f"[cam_mana] Warning: Failed to initialize backend services: {e}")


def run_server(host: str = None, port: int = None, reload: bool = None):
    """Run the FastAPI server.
    
    Args:
        host: Server host (default from settings)
        port: Server port (default from settings)
        reload: Enable hot-reload (default from DEBUG setting)
    """
    import signal
    
    host = host or settings.host
    port = port or settings.port
    reload = reload if reload is not None else settings.debug
    
    def signal_handler(sig, frame):
        raise SystemExit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clean pycache on start
    clean_pycache()
    
    # Initialize backend services
    initialize_backend()
    
    try:
        print(f"[cam_mana] Starting backend on {host}:{port}...")
        if reload:
            print("[cam_mana] Hot-reload enabled (DEBUG mode)")
        
        if reload:
            # Use string reference for reload mode
            uvicorn.run(
                "backend.server:app",
                host=host,
                port=port,
                reload=True,
                reload_dirs=[str(BACKEND_DIR)],
                log_level="info"
            )
        else:
            uvicorn.run(app, host=host, port=port, log_level="info")
            
    except SystemExit:
        pass
    finally:
        clean_pycache()
        print("[cam_mana] Shutdown complete.")


if __name__ == "__main__":
    run_server()
