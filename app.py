import sys
import os
import threading
import time
import shutil
import atexit
import signal
import socket
import subprocess
import logging
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

# Debug mode: enable with --debug flag or CAMMANA_DEBUG=1 environment variable
DEBUG_MODE = "--debug" in sys.argv or os.environ.get("CAMMANA_DEBUG") == "1"

# Setup base paths
# Nuitka standalone sets __compiled__ at module level
def is_nuitka_standalone() -> bool:
    """Check if running as Nuitka standalone binary"""
    try:
        # Nuitka sets __compiled__ as a module-level constant
        return "__compiled__" in dir() or hasattr(sys.modules.get('__main__'), '__compiled__')
    except:
        return False

def is_frozen_app() -> bool:
    """Check if we are running as a frozen/compiled application"""
    # 1. PyInstaller standard
    if getattr(sys, 'frozen', False):
        return True
    
    # 2. Nuitka Onefile standard
    if hasattr(sys, 'nuitka_binary'):
        return True

    # 3. Nuitka Standalone: Check if Nuitka is in sys.modules
    # Nuitka adds special entries when compiled
    if '__nuitka__' in sys.modules:
        return True
    
    # 4. Check __main__ for Nuitka's compilation marker
    main_mod = sys.modules.get('__main__')
    if main_mod and (hasattr(main_mod, '__compiled__') or "__nuitka_version__" in dir(main_mod)):
        return True

    # 5. Fallback: if executable is NOT in a standard location
    exe_name = Path(sys.executable).name.lower()
    if exe_name not in ('python.exe', 'python', 'python3.exe', 'python3', 'pythonw.exe'):
        return True
        
    return False

def get_resource_path(relative_path: str) -> Path:
    """ Get absolute path to resource, works for dev and for Nuitka/PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return Path(os.path.join(base_path, relative_path))

def get_app_dir() -> Path:
    """ Get directory where the executable or script is located """
    if is_frozen_app():
        return Path(sys.executable).parent
    return Path(__file__).parent.absolute()

APP_DIR = get_app_dir()


def save_crash_log(error: Exception, context: str = "system") -> Path:
    """Save system errors to database/logs for debugging. Returns crash log path."""
    log_dir = APP_DIR / "database" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    crash_file = log_dir / f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    try:
        lines = [
            "=" * 60, "CamMana Crash Report", "=" * 60, "",
            f"Time: {datetime.now().isoformat()}",
            f"Context: {context}",
            f"Debug Mode: {DEBUG_MODE}",
            f"Frozen App: {is_frozen_app()}",
            f"Python: {sys.version}",
            f"Executable: {sys.executable}",
            f"Working Dir: {os.getcwd()}",
            "", "=" * 60, "Error Details", "=" * 60, "",
            f"Type: {type(error).__name__}",
            f"Message: {error}",
            f"\nTraceback:\n{traceback.format_exc()}",
            "", "=" * 60, "System Info", "=" * 60, "",
            f"Platform: {sys.platform}",
            f"Args: {sys.argv}",
        ]
        crash_file.write_text("\n".join(lines), encoding="utf-8")
        logging.error(f"Crash log saved: {crash_file}")
    except Exception as e:
        logging.error(f"Failed to save crash log: {e}")
    
    return crash_file

# Check mode before heavy imports
IS_BACKEND = "--backend" in sys.argv

if not IS_BACKEND:
    # GUI Imports only when NOT in backend mode
    from PySide6.QtCore import QUrl, Qt, QTimer, Signal, QObject
    from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen, QMessageBox
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtGui import QIcon, QPixmap, QColor
else:
    # Mocks for backend process to avoid import errors during module load
    class QObject: 
        def __init__(self, *args, **kwargs): pass
        def connect(self, *args): pass
    def Signal(*args, **kwargs):
        class MockSignal:
            def connect(self, *args): pass
            def emit(self, *args): pass
        return MockSignal()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Initialize centralized logging with separate log files for app, backend, and frontend."""
    try:
        from backend.logging_config import init_all_loggers
        init_all_loggers()
    except ImportError:
        # Fallback if logging_config not available
        log_dir = APP_DIR / "database" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"cammana_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        handler = TimedRotatingFileHandler(
            str(log_file), when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            handlers=[handler, logging.StreamHandler(sys.stdout)]
        )


def is_production_mode() -> bool:
    """Detect if running in production mode"""
    if "--prod" in sys.argv: return True
    if "--dev" in sys.argv: return False
    
    # Primary check: is it frozen/compiled?
    if is_frozen_app(): return True
    
    # Fallback checks
    if (get_resource_path("frontend/out")).exists(): return True
    return not (APP_DIR / "pyproject.toml").exists()

def get_assets_dir() -> Path:
    """Get assets directory - priority to packed assets in production"""
    if is_production_mode():
        packed_assets = get_resource_path("assets")
        if packed_assets.exists(): return packed_assets
    dev_path = Path(__file__).parent / "production" / "assets"
    if dev_path.exists(): return dev_path
    return Path(__file__).parent / "assets"

def check_port(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except: return False

def kill_port(port: int):
    """Identify and kill any process using the specified port (Windows only)."""
    if sys.platform != "win32": return
    try:
        # Find PID using the port
        output = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True)
        for line in output.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                if pid and pid != "0":
                    logging.info(f"Port {port} is busy by PID {pid}. Terminating...")
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    except Exception as e:
        logging.warning(f"Failed to clear port {port}: {e}")

def clean_pycache():
    """Lightweight pycache cleanup - only for backend folder"""
    if getattr(sys, 'frozen', False): return
    target = APP_DIR / "backend"
    if target.exists():
        for pycache_dir in target.rglob("__pycache__"):
            shutil.rmtree(pycache_dir, ignore_errors=True)


class ProcessManager:
    _instance: Optional['ProcessManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._processes = []
            cls._instance._shutdown = False
            atexit.register(cls._instance.cleanup_all)
        return cls._instance
    
    def spawn(self, args: list, cwd: str = None, env: dict = None, capture_output: bool = False, shell: bool = False) -> subprocess.Popen:
        if self._shutdown: raise RuntimeError("Shutting down")
        executable = None
        if sys.platform == "win32" and not shell and args:
            executable = shutil.which(args[0])
        flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0
        kwargs = {"args": args, "cwd": cwd, "env": env, "creationflags": flags, "shell": shell}
        if executable: kwargs["executable"] = executable
        if capture_output: kwargs.update({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True})
        else: kwargs.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})
        try:
            proc = subprocess.Popen(**kwargs)
            self._processes.append(proc)
            logging.info(f"Spawned PID {proc.pid}: {' '.join(str(a) for a in args[:3])}...")
            return proc
        except Exception as e:
            logging.error(f"Failed to spawn {' '.join(str(a) for a in args)}: {e}")
            raise
    
    def terminate(self, proc: subprocess.Popen, timeout: float = 3.0):
        if proc.poll() is not None: return
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=timeout)
            else:
                proc.terminate()
                proc.wait(timeout=timeout)
        except Exception as e:
            logging.warning(f"Failed to terminate PID {proc.pid}: {e}")
            try: proc.kill()
            except: pass

    def cleanup_all(self):
        if self._shutdown: return
        self._shutdown = True
        logging.info(f"Cleaning up {len(self._processes)} processes...")
        for proc in self._processes: self.terminate(proc)
        self._processes.clear()


class BootstrapManager(QObject):
    status_changed, progress_changed = Signal(str), Signal(int)
    finished, error = Signal(), Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_frozen = getattr(sys, 'frozen', False) or hasattr(sys, '__compiled__')
        self._cancelled = False
    
    def run(self):
        threading.Thread(target=self._bootstrap, name="BootstrapThread", daemon=True).start()
    
    def _find_uv(self) -> Optional[Path]:
        assets_dir = get_assets_dir()
        for p in [assets_dir / "uv.exe", APP_DIR / "assets" / "uv.exe"]:
            if p.exists(): return p
        return None
    
    def _bootstrap(self):
        try:
            if not self.is_frozen:
                logging.info("Environment managed by external runner (uv/python)")
                self.finished.emit(); return
            
            # If we are compiled (frozen), we don't need to sync environment
            # BUT we might be in a 'portable' mode that isn't fully compiled (e.g. PyInstaller onedir with venv)
            # However, for Nuitka standalone, we skip.
            if hasattr(sys, '__compiled__') or hasattr(sys, 'nuitka_binary'):
                logging.info("Native binary: skipping environment setup")
                self.finished.emit(); return
            venv_path = APP_DIR / ".venv"
            if venv_path.exists() and (venv_path / "Scripts" / "python.exe").exists():
                self.status_changed.emit("Môi trường sẵn sàng"); self.finished.emit(); return
            
            self.status_changed.emit("Đang thiết lập môi trường...")
            self.progress_changed.emit(5)
            uv_path = self._find_uv()
            if not uv_path: self.error.emit("Không tìm thấy uv.exe"); return
            
            process = subprocess.Popen(
                [str(uv_path), "sync", "--frozen"], cwd=str(APP_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            while True:
                if self._cancelled: process.terminate(); return
                line = process.stdout.readline()
                if not line and process.poll() is not None: break
                if line.strip():
                    self.status_changed.emit(f"Cài đặt: {line.strip()[:50]}")
                    self.progress_changed.emit(min(90, 10 + process.poll() or 10))
            if process.returncode != 0: self.error.emit(f"Lỗi: {process.returncode}"); return
            self.progress_changed.emit(100); self.finished.emit()
        except Exception as e:
            logging.exception("Bootstrap error")
            self.error.emit(str(e))


class BackendManager(QObject):
    status_changed, ready, error = Signal(str), Signal(str), Signal(str)
    PORT, DEV_PORT = 8000, 3000
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process_manager = ProcessManager()
        self.is_frozen = is_frozen_app()
        self.is_production = is_production_mode()
    
    def start(self):
        threading.Thread(target=self._start_servers, name="BackendStartThread", daemon=True).start()
    
    def _start_servers(self):
        try:
            self.status_changed.emit("Khởi động hệ thống...")
            
            # Detect the executable to use for backend (the "python" runner)
            if self.is_frozen:
                # In a bundle, use the binary itself (Nuitka/PyInstaller)
                onefile_exe = os.environ.get("NUITKA_ONEFILE_BINARY")
                python_exe = Path(onefile_exe) if (onefile_exe and Path(onefile_exe).exists()) else Path(sys.executable)
                
                # Manual fallback check: if for some reason sys.executable is wrong or not found
                if not python_exe.exists():
                    for name in ["CamMana.exe", "app.exe", "python.exe"]:
                        alt = APP_DIR / name
                        if alt.exists(): python_exe = alt; break
            else:
                # In development, use the current python interpreter
                python_exe = Path(sys.executable)
            
            if not python_exe.exists():
                details = f"EXE: {sys.executable}\nDIR: {APP_DIR}\nFROZEN: {self.is_frozen}"
                self.error.emit(f"Không tìm thấy trình chạy (Runner not found):\n{python_exe}\n\n{details}"); return
            
            # Clear previous process on port 8000
            self.status_changed.emit("Kiểm tra cổng 8000...")
            kill_port(self.PORT)
            
            self.status_changed.emit("Khởi động Backend...")
            self._start_backend(python_exe)
            
            # Wait for port with health check
            status = False
            start_time = time.time()
            timeout = 120 # 2 minutes is plenty
            
            while time.time() - start_time < timeout:
                # Check if the process died early
                for proc in self.process_manager._processes:
                    if proc.poll() is not None:
                        # Process died! Stop waiting and report error
                        ret_code = proc.poll()
                        error_msg = f"Backend process exited immediately (Code: {ret_code})"
                        self.error.emit(error_msg); return
                
                if check_port(self.PORT):
                    status = True
                    break
                time.sleep(1.0)
                
            if not status:
                error_msg = "Backend timeout (Port 8000) - please check logs."
                self.error.emit(error_msg); return
            
            if self.is_production:
                url = f"http://127.0.0.1:{self.PORT}"
            else:
                self.status_changed.emit("Khởi động dev server...")
                self._start_frontend_dev()
                if not self._wait_for_port(self.DEV_PORT):
                    self.error.emit("Frontend timeout"); return
                url = f"http://127.0.0.1:{self.DEV_PORT}"
            
            self.status_changed.emit("Mở ứng dụng...")
            time.sleep(0.3); self.ready.emit(url)
        except Exception as e:
            logging.exception("Server start error")
            self.error.emit(str(e))
    
    def _start_backend(self, python_exe: Path):
        env = os.environ.copy()
        env.update({"PYTHONPATH": str(APP_DIR), "PYTHONDONTWRITEBYTECODE": "1"})
        log_dir = APP_DIR / "database" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        backend_log = log_dir / "backend_errors.log"

        if python_exe.name.lower().startswith("python"):
            cmd = [str(python_exe), str(APP_DIR / "app.py"), "--backend"]
        else:
            cmd = [str(python_exe), "--backend"]
            
        try:
            with open(backend_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- [BACKEND START] {datetime.now()} ---\n")
            log_file = open(backend_log, "a", encoding="utf-8")
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                cmd, cwd=str(APP_DIR), env=env, 
                stdout=log_file, stderr=log_file,
                creationflags=flags | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.process_manager._processes.append(proc)
        except Exception as e:
            logging.error(f"Failed to spawn backend: {e}")
            raise

    def _start_frontend_dev(self):
        frontend_dir = APP_DIR / "frontend"
        log_dir = APP_DIR / "database" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        frontend_log = log_dir / f"frontend_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        if not (frontend_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), shell=True, capture_output=True)
        
        # Log frontend output to file
        try:
            with open(frontend_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- [FRONTEND DEV START] {datetime.now()} ---\n")
            log_file = open(frontend_log, "a", encoding="utf-8")
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                ["npm", "run", "dev"], 
                cwd=str(frontend_dir), 
                shell=True,
                stdout=log_file, 
                stderr=log_file,
                creationflags=flags
            )
            self.process_manager._processes.append(proc)
        except Exception as e:
            logging.error(f"Failed to spawn frontend dev server: {e}")
            # Fallback to original method
            self.process_manager.spawn(args=["npm", "run", "dev"], cwd=str(frontend_dir), shell=True)

    def _wait_for_port(self, port: int, timeout: int = 60) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if check_port(port): return True
            time.sleep(0.5)
        return False


if not IS_BACKEND:
    class MainWindow(QMainWindow):
        def __init__(self, url: str = None):
            super().__init__()
            self.setWindowTitle("CamMana")
            self.setMinimumSize(1024, 768); self.resize(1400, 900)
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - 1400) // 2, (screen.height() - 900) // 2)
            icon_path = get_assets_dir() / "icon.ico"
            if icon_path.exists(): self.setWindowIcon(QIcon(str(icon_path)))
            self.browser = QWebEngineView()
            self.setCentralWidget(self.browser)
            if url: self.browser.setUrl(QUrl(url))
            self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
else:
    class MainWindow:
        def __init__(self, *args, **kwargs): pass


def main():
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.screen=false"
    os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=2"
    
    if "--backend" in sys.argv:
        try:
            # OPTIMIZATION: Only import backend stuff here
            from backend.server import app as fastapi_app, initialize_backend
            import uvicorn
            print("[cam_mana] Initializing backend services...")
            initialize_backend()
            print("[cam_mana] Starting Uvicorn server...")
            uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="info", access_log=False)
        except Exception as e:
            import traceback
            print(f"Backend process error: {e}")
            traceback.print_exc()
            sys.exit(1)
        return

    setup_logging()
    clean_pycache()
    logging.info(f"Starting CamMana UI (Mode: {'PROD' if is_production_mode() else 'DEV'})")
    
    app = QApplication(sys.argv)
    app.setApplicationName("CamMana")
    
    pixmap_path = get_assets_dir() / "icon.png"
    if not pixmap_path.exists():
        pixmap_path = get_resource_path("assets/icon.png")
    pixmap = QPixmap(str(pixmap_path)).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation) if pixmap_path.exists() else QPixmap(256, 256)
    
    splash = QSplashScreen(pixmap); splash.show()
    app.processEvents()
    
    boot, backend = BootstrapManager(), BackendManager()
    main_win = None

    def fatal_error(msg):
        logging.error(f"FATAL: {msg}")
        # Save crash log for debugging
        try:
            crash_file = save_crash_log(Exception(msg), "gui_fatal_error")
            if DEBUG_MODE:
                logging.info(f"Debug: Crash log at {crash_file}")
        except:
            pass
        splash.showMessage(f"Lỗi: {msg}", Qt.AlignBottom|Qt.AlignCenter, QColor("#ef4444"))
        QTimer.singleShot(100, lambda: (QMessageBox.critical(None, "CamMana - Lỗi", f"Lỗi hệ thống không thể tự khắc phục:\n\n{msg}"), app.quit()))

    def on_ready(url):
        nonlocal main_win
        main_win = MainWindow(url)
        main_win.show()
        splash.finish(main_win)
        logging.info(f"App ready at {url}")

    def update_status(msg):
        splash.showMessage(msg, Qt.AlignBottom|Qt.AlignCenter, QColor("#fbbf24"))
        logging.info(msg)

    boot.status_changed.connect(update_status)
    boot.error.connect(fatal_error)
    boot.finished.connect(backend.start)
    backend.status_changed.connect(update_status)
    backend.error.connect(fatal_error)
    backend.ready.connect(on_ready)
    
    boot.run()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
