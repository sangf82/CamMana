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

from PySide6.QtCore import QUrl, Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon

# Base directory
BASE_DIR = Path(__file__).parent

# Loading page HTML
LOADING_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CamMana - Đang khởi động...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
        }
        
        .container {
            text-align: center;
            padding: 40px;
        }
        
        .logo {
            font-size: 64px;
            margin-bottom: 20px;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
        }
        
        h1 {
            font-size: 36px;
            font-weight: 600;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #f59e0b, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            font-size: 18px;
            color: #94a3b8;
            margin-bottom: 40px;
        }
        
        .loader {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-bottom: 30px;
        }
        
        .loader-dot {
            width: 12px;
            height: 12px;
            background: #f59e0b;
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite;
        }
        
        .loader-dot:nth-child(1) { animation-delay: 0s; }
        .loader-dot:nth-child(2) { animation-delay: 0.2s; }
        .loader-dot:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-20px); }
        }
        
        .status {
            font-size: 14px;
            color: #64748b;
        }
        
        .status-text {
            display: inline-block;
            min-width: 200px;
        }
        
        .footer {
            position: absolute;
            bottom: 30px;
            font-size: 12px;
            color: #475569;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📷</div>
        <h1>CamMana</h1>
        <p class="subtitle">Hệ thống quản lý camera thông minh</p>
        
        <div class="loader">
            <div class="loader-dot"></div>
            <div class="loader-dot"></div>
            <div class="loader-dot"></div>
        </div>
        
        <p class="status">
            <span class="status-text" id="status">Đang khởi động hệ thống...</span>
        </p>
    </div>
    
    <div class="footer">
        © 2026 CamMana - Camera Management System
    </div>
</body>
</html>
"""


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


def get_base_path():
    """Get base path for resources"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).parent


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
        self.frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("CamMana - Camera Manager")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)
        
        # Set application icon
        icon_path = get_base_path() / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Create web view with loading page
        self.browser = QWebEngineView()
        self.browser.setHtml(LOADING_HTML)
        self.setCentralWidget(self.browser)
        
        # Set window flags
        self.setWindowFlags(Qt.Window)
        
        # Create server starter
        self.server_starter = ServerStarter(self)
        self.server_starter.status_changed.connect(self._on_status_changed)
        self.server_starter.ready.connect(self._on_ready)
        self.server_starter.error.connect(self._on_error)
        
        # Start servers after window is shown
        QTimer.singleShot(100, self.server_starter.start)
    
    def _on_status_changed(self, status: str):
        """Update loading status"""
        js = f'document.getElementById("status").textContent = "{status}";'
        self.browser.page().runJavaScript(js)
    
    def _on_ready(self, url: str):
        """Navigate to the app when ready"""
        print(f"[cam_mana] Navigating to {url}")
        self.browser.setUrl(QUrl(url))
    
    def _on_error(self, error: str):
        """Show error in loading page"""
        error_html = f'''
            document.querySelector(".loader").innerHTML = '<div style="font-size: 48px;">❌</div>';
            document.getElementById("status").innerHTML = '<span style="color: #ef4444;">Lỗi: {error}</span>';
        '''
        self.browser.page().runJavaScript(error_html)
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        self.server_starter.cleanup()
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
    
    # Create and show main window immediately
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
