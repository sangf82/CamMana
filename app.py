"""
CamMana Desktop Application - Zero-Config Bootstrapper
=======================================================

Architecture:
1. Frozen EXE (PySide6) shows splash screen immediately
2. BootstrapManager checks/creates .venv using bundled uv.exe
3. BackendManager spawns Python subprocess from .venv to run FastAPI
4. Main window loads frontend from backend server
5. Clean shutdown: all subprocesses terminated on exit (no zombies)

Key Design Decisions:
- Backend runs as SUBPROCESS (not in-process import) for clean isolation
- Process group management ensures child processes are killed
- No daemon threads holding resources
- Proper signal handling for Windows
"""

import sys
import os
import threading
import time
import shutil
import atexit
import signal
import socket
import subprocess
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QUrl, Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QPixmap, QColor


# =============================================================================
# Path Resolution
# =============================================================================

def get_base_path() -> Path:
    """Get base path for bundled resources (_internal folder in frozen mode)"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def get_app_dir() -> Path:
    """Get application directory (where CamMana.exe lives)"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


BASE_DIR = get_base_path()
APP_DIR = get_app_dir()


# =============================================================================
# Utilities
# =============================================================================

def is_production_mode() -> bool:
    """Check if running in production mode (static frontend exists)"""
    static_dir = APP_DIR / "frontend" / "out"
    return static_dir.exists()


def check_port(host: str, port: int) -> bool:
    """Check if a port is open and accepting connections"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex((host, port)) == 0
    except Exception:
        return False


def clean_pycache():
    """Remove __pycache__ directories (dev mode only)"""
    if getattr(sys, 'frozen', False):
        return
    
    count = 0
    for pycache_dir in APP_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                shutil.rmtree(pycache_dir)
                count += 1
            except Exception:
                pass
    if count:
        print(f"[CamMana] Cleaned {count} __pycache__ directories")


# =============================================================================
# Process Manager - Handles subprocess lifecycle (NO ZOMBIES)
# =============================================================================

class ProcessManager:
    """
    Centralized subprocess management to prevent zombie processes.
    
    Key features:
    - Tracks all spawned processes
    - Uses CREATE_NEW_PROCESS_GROUP on Windows for clean termination
    - Kills entire process tree on shutdown
    - Registered with atexit for guaranteed cleanup
    """
    
    _instance: Optional['ProcessManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._processes: list[subprocess.Popen] = []
            cls._instance._shutdown = False
            atexit.register(cls._instance.cleanup_all)
        return cls._instance
    
    def spawn(self, args: list, cwd: str = None, env: dict = None, 
              capture_output: bool = False) -> subprocess.Popen:
        """
        Spawn a subprocess with proper flags for clean termination.
        """
        if self._shutdown:
            raise RuntimeError("ProcessManager is shutting down")
        
        # Windows-specific flags for process group management
        creationflags = 0
        if sys.platform == "win32":
            creationflags = (
                subprocess.CREATE_NO_WINDOW |
                subprocess.CREATE_NEW_PROCESS_GROUP
            )
        
        kwargs = {
            "args": args,
            "cwd": cwd,
            "env": env,
            "creationflags": creationflags,
        }
        
        if capture_output:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.STDOUT
            kwargs["text"] = True
        else:
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL
        
        proc = subprocess.Popen(**kwargs)
        self._processes.append(proc)
        print(f"[ProcessManager] Spawned PID {proc.pid}: {' '.join(str(a) for a in args[:3])}...")
        return proc
    
    def terminate(self, proc: subprocess.Popen, timeout: float = 5.0):
        """Terminate a specific process and its children."""
        if proc.poll() is not None:
            return  # Already dead
        
        try:
            if sys.platform == "win32":
                # Use taskkill to kill entire process tree
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    timeout=timeout
                )
            else:
                proc.terminate()
                proc.wait(timeout=timeout)
        except Exception as e:
            print(f"[ProcessManager] Error terminating PID {proc.pid}: {e}")
            try:
                proc.kill()
            except Exception:
                pass
    
    def cleanup_all(self):
        """Terminate all tracked processes. Called on app exit."""
        if self._shutdown:
            return
        self._shutdown = True
        
        print(f"[ProcessManager] Cleaning up {len(self._processes)} processes...")
        
        for proc in self._processes:
            self.terminate(proc, timeout=3.0)
        
        self._processes.clear()
        print("[ProcessManager] Cleanup complete")


# =============================================================================
# Bootstrap Manager - First-run environment setup
# =============================================================================

class BootstrapManager(QObject):
    """
    Manages first-run environment setup using bundled uv.exe.
    
    On first run:
    1. Detects missing .venv folder
    2. Runs 'uv sync --frozen' to create environment
    3. Installs all dependencies from pyproject.toml/uv.lock
    """
    
    status_changed = Signal(str)
    progress_changed = Signal(int)  # 0-100
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_frozen = getattr(sys, 'frozen', False)
        self._cancelled = False
    
    def run(self):
        """Start bootstrap in background thread."""
        thread = threading.Thread(target=self._bootstrap, name="BootstrapThread")
        thread.start()
    
    def _find_uv(self) -> Optional[Path]:
        """Locate uv.exe in various possible locations."""
        candidates = [
            APP_DIR / "assets" / "uv.exe",           # Primary location
            APP_DIR / "_internal" / "assets" / "uv.exe",  # PyInstaller internal
            BASE_DIR / "assets" / "uv.exe",          # Fallback
        ]
        
        for path in candidates:
            if path.exists():
                return path
        return None
    
    def _bootstrap(self):
        """Main bootstrap logic."""
        try:
            # In development mode, skip bootstrap
            if not self.is_frozen:
                print("[Bootstrap] Development mode - skipping uv sync")
                self.finished.emit()
                return
            
            venv_path = APP_DIR / ".venv"
            pyproject_path = APP_DIR / "pyproject.toml"
            
            # Check if environment already exists
            if venv_path.exists() and (venv_path / "Scripts" / "python.exe").exists():
                print("[Bootstrap] Existing .venv found")
                self.status_changed.emit("Môi trường đã sẵn sàng")
                self.finished.emit()
                return
            
            # First run - need to create environment
            print("[Bootstrap] First run detected - creating environment")
            self.status_changed.emit("Lần đầu khởi động: Đang thiết lập môi trường...")
            self.progress_changed.emit(5)
            
            # Validate required files
            if not pyproject_path.exists():
                self.error.emit(f"Thiếu file cấu hình: pyproject.toml")
                return
            
            uv_path = self._find_uv()
            if not uv_path:
                self.error.emit("Không tìm thấy uv.exe. Vui lòng tải lại ứng dụng.")
                return
            
            print(f"[Bootstrap] Using uv at: {uv_path}")
            self.progress_changed.emit(10)
            
            # Run uv sync
            self.status_changed.emit("Đang cài đặt thư viện (có thể mất 1-3 phút)...")
            
            process = subprocess.Popen(
                [str(uv_path), "sync", "--frozen"],
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            progress = 10
            while True:
                if self._cancelled:
                    process.terminate()
                    return
                
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        print(f"[uv] {clean_line}")
                        
                        # Update progress based on uv output
                        if "Resolved" in clean_line:
                            progress = 30
                        elif "Downloading" in clean_line or "Installing" in clean_line:
                            progress = min(progress + 2, 90)
                            # Show package being installed
                            short_msg = clean_line[:60] + "..." if len(clean_line) > 60 else clean_line
                            self.status_changed.emit(f"Đang cài đặt: {short_msg}")
                        
                        self.progress_changed.emit(progress)
            
            if process.returncode != 0:
                self.error.emit(f"Lỗi cài đặt môi trường (mã lỗi: {process.returncode})")
                return
            
            # Verify installation
            python_exe = venv_path / "Scripts" / "python.exe"
            if not python_exe.exists():
                self.error.emit("Không thể tạo môi trường Python")
                return
            
            self.progress_changed.emit(100)
            self.status_changed.emit("Thiết lập hoàn tất!")
            print("[Bootstrap] Environment setup complete")
            time.sleep(0.5)
            self.finished.emit()
            
        except Exception as e:
            print(f"[Bootstrap] Error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(f"Lỗi khởi động: {str(e)}")


# =============================================================================
# Backend Manager - Spawns FastAPI server as subprocess
# =============================================================================

class BackendManager(QObject):
    """
    Manages the FastAPI backend as a separate Python subprocess.
    
    Key design:
    - Backend runs in its own process (NOT in-process import)
    - Uses Python from .venv created by uv
    - Clean process isolation = no resource conflicts
    - Proper termination on shutdown
    """
    
    status_changed = Signal(str)
    ready = Signal(str)  # Emits frontend URL
    error = Signal(str)
    
    BACKEND_PORT = 8000  # Must match backend/settings.py default
    FRONTEND_DEV_PORT = 3000
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process_manager = ProcessManager()
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.is_frozen = getattr(sys, 'frozen', False)
        self.is_production = is_production_mode()
    
    def start(self):
        """Start backend server in background thread."""
        thread = threading.Thread(target=self._start_servers, name="BackendStartThread")
        thread.start()
    
    def _get_python_exe(self) -> Path:
        """Get path to Python executable."""
        if self.is_frozen:
            return APP_DIR / ".venv" / "Scripts" / "python.exe"
        else:
            return Path(sys.executable)
    
    def _start_servers(self):
        """Start backend (and optionally frontend dev) servers."""
        try:
            self.status_changed.emit("Đang khởi động hệ thống...")
            
            python_exe = self._get_python_exe()
            
            if not python_exe.exists():
                self.error.emit(f"Không tìm thấy Python: {python_exe}")
                return
            
            # Start backend server
            self._start_backend(python_exe)
            
            # Wait for backend to be ready
            if not self._wait_for_port("127.0.0.1", self.BACKEND_PORT, timeout=60):
                self.error.emit("Backend không khởi động được (timeout)")
                return
            
            print(f"[Backend] Server ready on port {self.BACKEND_PORT}")
            
            if self.is_production:
                # Production: backend serves static frontend
                self.status_changed.emit("Đang tải giao diện...")
                time.sleep(0.3)
                frontend_url = f"http://127.0.0.1:{self.BACKEND_PORT}"
                print("[CamMana] Running in PRODUCTION mode")
            else:
                # Development: start Next.js dev server
                self.status_changed.emit("Đang khởi động Next.js dev server...")
                self._start_frontend_dev()
                
                if not self._wait_for_port("127.0.0.1", self.FRONTEND_DEV_PORT, timeout=60):
                    self.error.emit("Frontend dev server không khởi động được")
                    return
                
                frontend_url = f"http://127.0.0.1:{self.FRONTEND_DEV_PORT}"
                print("[CamMana] Running in DEVELOPMENT mode")
            
            self.status_changed.emit("Hoàn tất! Đang mở ứng dụng...")
            time.sleep(0.3)
            self.ready.emit(frontend_url)
            
        except Exception as e:
            print(f"[Backend] Error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def _start_backend(self, python_exe: Path):
        """Start FastAPI backend as subprocess."""
        
        # Create a simple launcher script inline
        backend_code = '''
import sys
import os

# Set working directory to app folder
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(app_dir)
sys.path.insert(0, app_dir)

# Import and run server
from backend.server import app
from backend import config
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="warning",
        access_log=False
    )
'''
        
        # In frozen mode, run directly with proper PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(APP_DIR)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        
        # Run: python -c "from backend.server import app; ..."
        cmd = [
            str(python_exe),
            "-c",
            f'''
import sys, os
os.chdir(r"{APP_DIR}")
sys.path.insert(0, r"{APP_DIR}")
from backend.server import app
from backend import config
import uvicorn
uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="warning", access_log=False)
'''
        ]
        
        self.backend_process = self.process_manager.spawn(
            args=cmd,
            cwd=str(APP_DIR),
            env=env
        )
        print(f"[Backend] Started with PID {self.backend_process.pid}")
    
    def _start_frontend_dev(self):
        """Start Next.js dev server (development mode only)."""
        frontend_dir = APP_DIR / "frontend"
        
        if not frontend_dir.exists():
            raise Exception("Frontend directory not found")
        
        # Install dependencies if needed
        if not (frontend_dir / "node_modules").exists():
            print("[Frontend] Installing dependencies...")
            self.status_changed.emit("Đang cài đặt frontend dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=str(frontend_dir),
                shell=True,
                capture_output=True
            )
        
        self.frontend_process = self.process_manager.spawn(
            args=["npm", "run", "dev"],
            cwd=str(frontend_dir)
        )
    
    def _wait_for_port(self, host: str, port: int, timeout: int = 30) -> bool:
        """Wait for a port to become available."""
        start = time.time()
        while time.time() - start < timeout:
            if check_port(host, port):
                return True
            time.sleep(0.5)
        return False


# =============================================================================
# Main Window
# =============================================================================

class MainWindow(QMainWindow):
    """Main application window with embedded web view."""
    
    def __init__(self, url: str = None):
        super().__init__()
        
        self.setWindowTitle("CamMana - Camera Manager")
        self.setMinimumSize(1024, 768)
        self.resize(1400, 900)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - 1400) // 2,
            (screen.height() - 900) // 2
        )
        
        # Set icon
        icon_path = BASE_DIR / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Create web view
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        
        if url:
            self.browser.setUrl(QUrl(url))
        
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowMinMaxButtonsHint | 
            Qt.WindowCloseButtonHint
        )
    
    def closeEvent(self, event):
        """Handle window close - cleanup is done by ProcessManager."""
        event.accept()


# =============================================================================
# Application Entry Point
# =============================================================================

def main():
    """Main application entry point."""
    
    # Cleanup pycache on startup (dev mode)
    clean_pycache()
    
    print("[CamMana] Starting...")
    print(f"[CamMana] Mode: {'PRODUCTION' if is_production_mode() else 'DEVELOPMENT'}")
    print(f"[CamMana] App directory: {APP_DIR}")
    print(f"[CamMana] Base directory: {BASE_DIR}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("CamMana")
    app.setOrganizationName("CamMana")
    
    # Create splash screen
    pixmap_path = BASE_DIR / "assets" / "icon.png"
    if pixmap_path.exists():
        pixmap = QPixmap(str(pixmap_path)).scaled(
            256, 256, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
    else:
        pixmap = QPixmap(256, 256)
        pixmap.fill(QColor("#09090b"))
    
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    
    # State
    main_window: Optional[MainWindow] = None
    
    # Create managers
    bootstrapper = BootstrapManager()
    backend = BackendManager()
    
    # --- Signal handlers ---
    
    def on_bootstrap_finished():
        print("[CamMana] Bootstrap complete, starting backend...")
        backend.start()
    
    def on_ready(url: str):
        nonlocal main_window
        main_window = MainWindow(url)
        main_window.show()
        splash.finish(main_window)
        print(f"[CamMana] Application ready at {url}")
    
    def on_status(status: str):
        splash.showMessage(
            status,
            Qt.AlignBottom | Qt.AlignCenter,
            QColor("#fbbf24")
        )
        print(f"[CamMana] {status}")
    
    def on_error(error: str):
        splash.showMessage(
            f"Lỗi: {error}",
            Qt.AlignBottom | Qt.AlignCenter,
            QColor("#ef4444")
        )
        print(f"[CamMana] ERROR: {error}")
        
        # Show error dialog
        QTimer.singleShot(2000, lambda: QMessageBox.critical(
            None, 
            "CamMana - Lỗi", 
            f"Không thể khởi động ứng dụng:\n\n{error}"
        ))
    
    # Connect signals
    bootstrapper.status_changed.connect(on_status)
    bootstrapper.error.connect(on_error)
    bootstrapper.finished.connect(on_bootstrap_finished)
    
    backend.status_changed.connect(on_status)
    backend.error.connect(on_error)
    backend.ready.connect(on_ready)
    
    # Start bootstrap sequence
    bootstrapper.run()
    
    # Run event loop
    exit_code = app.exec()
    
    # Explicit cleanup (also handled by atexit)
    ProcessManager().cleanup_all()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
