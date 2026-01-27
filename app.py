"""
CamMana Desktop Application
Uses PySide6 (Qt) to create a native Windows application
"""

import sys
import os
import threading
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon


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
    from backend import config
    import uvicorn
    
    config_uvicorn = uvicorn.Config(
        app=app,
        host=config.HOST,
        port=config.PORT,
        log_level="warning"
    )
    server = uvicorn.Server(config_uvicorn)
    server.run()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, url):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("CamMana - Camera Manager")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)
        
        # Set application icon
        icon_path = get_base_path() / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Create web view
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)
        
        # Set window flags for better native feel
        self.setWindowFlags(Qt.Window)


def main():
    # Start backend server in background thread
    backend_thread = threading.Thread(target=start_backend_server, daemon=True)
    backend_thread.start()
    
    # Wait for server to start
    print("Starting CamMana...")
    time.sleep(3)
    
    # Determine frontend URL
    base_path = get_base_path()
    static_dir = base_path / "frontend" / "out"
    
    if static_dir.exists():
        # Production mode - serve from FastAPI
        from backend import config
        # Use localhost for connection (0.0.0.0 is bind address only)
        frontend_url = f"http://127.0.0.1:{config.PORT}"
        print(f"Running in production mode")
    else:
        # Development mode - use Next.js dev server
        frontend_url = "http://127.0.0.1:3000"
        print(f"Running in development mode")
        print("Make sure to run 'npm run dev' in the frontend folder!")
    
    print(f"Loading {frontend_url}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("CamMana")
    app.setOrganizationName("CamMana")
    
    # Create main window
    window = MainWindow(frontend_url)
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
