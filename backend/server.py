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

from backend.api import camera_router, schedule_router, detection_router
from backend.data_process import db

BACKEND_DIR = Path(__file__).parent


def clean_pycache():
    """Remove all __pycache__ directories in backend folder"""
    count = 0
    for pycache_dir in BACKEND_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            count += 1
    if count:
        print(f"[Server] Cleaned {count} __pycache__ directories")


def get_static_dir():
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    static_path = base_path / "frontend" / "out"
    return static_path if static_path.exists() else None


def create_app() -> FastAPI:
    db.init_db()
    
    app = FastAPI(title="CamMana API", description="ONVIF Camera Control & Streaming API", version="2.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    
    app.include_router(camera_router)
    app.include_router(schedule_router)
    app.include_router(detection_router)
    
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


def run_server(host: str = "127.0.0.1", port: int = 8000):
    import signal
    
    def signal_handler(sig, frame):
        raise SystemExit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clean pycache on start
    clean_pycache()
    
    try:
        print("[Server] Starting CamMana backend...")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except SystemExit:
        pass
    finally:
        # Clean pycache on stop
        clean_pycache()
        print("[Server] Shutdown complete.")


if __name__ == "__main__":
    run_server()
