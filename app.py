"""
CamMana Desktop Application
Uses PySide6 (Qt) to create a native Windows application

Strategy:
1. Show UI immediately with loading screen
2. Start backend server in background
3. In dev mode, also start Next.js dev server
4. When everything is ready, navigate to the app
"""

import sys
import os
import threading
import time
import shutil
import atexit
import socket
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QUrl, Qt, QTimer, Signal, QObject, QRect
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QPixmap, QColor, QFont


def get_base_path():
    """Get base path for resources"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).parent


# Base directory
BASE_DIR = get_base_path()






def clean_pycache():
    """Remove all __pycache__ directories in project folder"""
    if getattr(sys, 'frozen', False):
        return
    
    count = 0
    for pycache_dir in BASE_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                count += 1
            except Exception:
                pass
    if count:
        print(f"[cam_mana] Cleaned {count} __pycache__ directories")





def is_production_mode():
    """Check if running in production mode"""
    base_path = get_base_path()
    static_dir = base_path / "frontend" / "out"
    return static_dir.exists()


def check_port(host: str, port: int) -> bool:
    """Check if a port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


class ServerStarter(QObject):
    """Background server starter with Qt signals"""
    status_changed = Signal(str)
    ready = Signal(str)  # Emits the frontend URL when ready
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.backend_process = None
        self.frontend_process = None
        self.is_production = is_production_mode()
        
    def start(self):
        """Start servers in background thread"""
        thread = threading.Thread(target=self._start_servers, daemon=True)
        thread.start()
    
    def _start_servers(self):
        """Start backend and optionally frontend servers"""
        try:
            from backend import config
            backend_port = config.PORT
            frontend_port = 3000
            
            # Start backend server
            self.status_changed.emit("Đang khởi động máy chủ backend...")
            self._start_backend()
            
            # Wait for backend to be ready
            if not self._wait_for_port("127.0.0.1", backend_port, timeout=60):
                self.error.emit("Backend server không khởi động được")
                return
            
            print(f"[cam_mana] Backend server ready on port {backend_port}")
            
            if self.is_production:
                # Production mode - backend serves frontend
                self.status_changed.emit("Đang tải giao diện...")
                time.sleep(0.5)  # Small delay for stability
                frontend_url = f"http://127.0.0.1:{backend_port}"
                print("[cam_mana] Running in PRODUCTION mode")
            else:
                # Development mode - start Next.js dev server
                self.status_changed.emit("Đang khởi động Next.js dev server...")
                self._start_frontend_dev()
                
                # Wait for frontend to be ready
                if not self._wait_for_port("127.0.0.1", frontend_port, timeout=60):
                    self.error.emit("Frontend dev server không khởi động được")
                    return
                
                print(f"[cam_mana] Frontend dev server ready on port {frontend_port}")
                frontend_url = f"http://127.0.0.1:{frontend_port}"
                print("[cam_mana] Running in DEVELOPMENT mode")
            
            self.status_changed.emit("Hoàn tất! Đang chuyển đến ứng dụng...")
            time.sleep(0.5)
            self.ready.emit(frontend_url)
            
        except Exception as e:
            print(f"[cam_mana] ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def _start_backend(self):
        """Start FastAPI backend server in background thread"""
        def run_backend():
            try:
                from backend.server import app
                from backend import config
                import uvicorn
                
                uvicorn_config = uvicorn.Config(
                    app=app,
                    host=config.HOST,
                    port=config.PORT,
                    log_level="warning"
                )
                server = uvicorn.Server(uvicorn_config)
                server.run()
            except Exception as e:
                print(f"[cam_mana] Backend error: {e}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=run_backend, daemon=True)
        thread.start()
    
    def _start_frontend_dev(self):
        """Start Next.js dev server for development mode"""
        frontend_dir = BASE_DIR / "frontend"
        
        if not frontend_dir.exists():
            raise Exception("Frontend directory not found")
        
        # Check if node_modules exists
        if not (frontend_dir / "node_modules").exists():
            print("[cam_mana] Installing frontend dependencies...")
            self.status_changed.emit("Đang cài đặt dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=str(frontend_dir),
                shell=True,
                capture_output=True
            )
        
        # Start Next.js dev server
        # In DEV mode, dump output to console so we can debug "White Screen" issues
        self.frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            shell=True,
            stdout=sys.stdout, 
            stderr=sys.stderr,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
    
    def _wait_for_port(self, host: str, port: int, timeout: int = 30) -> bool:
        """Wait for a port to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if check_port(host, port):
                return True
            time.sleep(0.5)
        return False
    
    def cleanup(self):
        """Cleanup subprocess on exit"""
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
            except Exception:
                pass


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, url=None):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("CamMana - Camera Manager")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)
        
        # Center the window
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 1400) // 2
        y = (screen.height() - 900) // 2
        self.move(x, y)
        
        # Set application icon
        icon_path = BASE_DIR / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Create web view
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        
        if url:
            self.browser.setUrl(QUrl(url))
        
        # Set window flags
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)


        
    
    
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        # The starter is managed globally now
        event.accept()


def main():
    # Cleanup __pycache__ on startup
    clean_pycache()
    
    # Register cleanup on exit
    atexit.register(clean_pycache)
    
    print("[cam_mana] Starting CamMana...")
    print(f"[cam_mana] Mode: {'PRODUCTION' if is_production_mode() else 'DEVELOPMENT'}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("CamMana")
    app.setOrganizationName("CamMana")
    
    # Create and show native splash screen
    pixmap_path = BASE_DIR / "assets" / "icon.png"
    if pixmap_path.exists():
        pixmap = QPixmap(str(pixmap_path)).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    else:
        # Fallback empty pixmap if icon not found
        pixmap = QPixmap(256, 256)
        pixmap.fill(QColor("#09090b"))

    splash = QSplashScreen(pixmap)
    splash.show()
    
    # Styling for splash messages
    app.processEvents()
    
    main_window = None
    starter = ServerStarter()
    
    def on_ready(url):
        nonlocal main_window
        main_window = MainWindow(url)
        main_window.show()
        splash.finish(main_window)
        print(f"[cam_mana] App ready, showing main window")

    def on_status(status):
        splash.showMessage(
            status, 
            Qt.AlignBottom | Qt.AlignCenter, 
            QColor("#fbbf24")
        )
        print(f"[cam_mana] Status: {status}")

    def on_error(error):
        splash.showMessage(
            f"Lỗi: {error}", 
            Qt.AlignBottom | Qt.AlignCenter, 
            QColor("#ef4444")
        )
        print(f"[cam_mana] Launcher Error: {error}")

    starter.ready.connect(on_ready)
    starter.status_changed.connect(on_status)
    starter.error.connect(on_error)
    
    # Start the backend servers
    starter.start()
    
    # Register cleanup
    atexit.register(starter.cleanup)
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
