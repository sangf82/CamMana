"""FastAPI Backend Server for CamMana"""
import sys
import shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# Import from new modular API structure
from backend.api import (
    camera_router, config_router, schedule_router, 
    detection_router, history_router, checkin_router
)

BACKEND_DIR = Path(__file__).parent


def clean_pycache():
    """Remove all __pycache__ directories in backend folder"""
    count = 0
    for pycache_dir in BACKEND_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            count += 1
    if count:
        print(f"[cam_mana] Cleaned {count} __pycache__ directories")


def get_static_dir():
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    static_path = base_path / "frontend" / "out"
    return static_path if static_path.exists() else None


from backend import config

def create_app() -> FastAPI:
    # Removed: db.init_db() - Now using CSV-only storage
    
    app = FastAPI(title=config.API_TITLE, description=config.API_DESCRIPTION, version=config.API_VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    
    app.include_router(camera_router)
    app.include_router(config_router)
    app.include_router(schedule_router)
    app.include_router(detection_router)
    app.include_router(history_router)
    app.include_router(checkin_router)
    
    # Serve captured car images from car_history folder
    @app.get("/api/images/{date_folder}/{car_folder}/{filename}")
    async def serve_car_image(date_folder: str, car_folder: str, filename: str):
        """Serve captured car images for evidence display"""
        image_path = Path("database/car_history") / date_folder / car_folder / filename
        if image_path.exists() and image_path.is_file():
            return FileResponse(image_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Image not found")
    
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


def run_server(host: str = config.HOST, port: int = config.PORT):
    import signal
    from backend import data_process
    
    def signal_handler(sig, frame):
        raise SystemExit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clean pycache on start
    clean_pycache()
    
    # Initialize today's CSV files (auto-migration and cleanup)
    try:
        if data_process.initialize_registered_cars_today():
            print("[cam_mana] Created today's registered cars file")
        if data_process.initialize_history_today():
            print("[cam_mana] Created today's history file")
            
        # Cleanup expired car history folders
        deleted = data_process.cleanup_expired_car_history_folders()
        if deleted > 0:
            print(f"[cam_mana] Cleaned up {deleted} expired car history folders")
    except Exception as e:
        print(f"[cam_mana] Warning: Failed to initialize daily files: {e}")
    
    try:
        print(f"[cam_mana] Starting backend on {host}:{port}...")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except SystemExit:
        pass
    finally:
        # Clean pycache on stop
        clean_pycache()
        print("[cam_mana] Shutdown complete.")


if __name__ == "__main__":
    run_server()
