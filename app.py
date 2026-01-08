"""
CamMana Desktop Application
Uses PyWebView to create a native window with React frontend
"""

import webview
import threading
import time
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_base_path():
    """Get base path for resources"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys._MEIPASS)
    else:
        # Running in development
        return Path(__file__).parent


def start_backend_server():
    """Start FastAPI server in background thread"""
    from backend.server import app
    import uvicorn
    
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    server.run()


class API:
    """JavaScript API exposed to the webview"""
    
    def get_platform(self):
        return sys.platform
    
    def minimize(self):
        for window in webview.windows:
            window.minimize()
    
    def toggle_fullscreen(self):
        for window in webview.windows:
            window.toggle_fullscreen()
    
    def close(self):
        for window in webview.windows:
            window.destroy()


def main():
    # Start backend server in background thread
    backend_thread = threading.Thread(target=start_backend_server, daemon=True)
    backend_thread.start()
    
    # Wait for server to start
    print("Starting CamMana...")
    time.sleep(2)
    
    # Determine frontend URL
    base_path = get_base_path()
    static_dir = base_path / "frontend" / "out"
    
    if static_dir.exists():
        # Production mode - serve from FastAPI
        frontend_url = "http://127.0.0.1:8000"
        print(f"Running in production mode")
    else:
        # Development mode - use Next.js dev server
        frontend_url = "http://127.0.0.1:3000"
        print(f"Running in development mode")
        print("Make sure to run 'npm run dev' in the frontend folder!")
    
    print(f"Opening {frontend_url}")
    
    # Create API instance
    api = API()
    
    # Create main window
    window = webview.create_window(
        title="CamMana - Camera Manager",
        url=frontend_url,
        width=1400,
        height=900,
        min_size=(1024, 768),
        resizable=True,
        frameless=False,
        easy_drag=False,
        js_api=api,
        background_color='#0f1419'
    )
    
    # Start webview
    webview.start(debug=False)


if __name__ == "__main__":
    main()
