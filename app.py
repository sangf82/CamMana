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
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl, Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QPixmap, QColor


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path: str) -> Path:
    """ Get absolute path to resource, works for dev and for Nuitka/PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return Path(os.path.join(base_path, relative_path))

def get_app_dir() -> Path:
    """ Get directory where the executable or script is located """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.absolute()

APP_DIR = get_app_dir()

def setup_logging():
    log_dir = APP_DIR / "database" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"cammana_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    handler = TimedRotatingFileHandler(
        str(log_file), when="midnight", interval=1, backupCount=30, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)]
    )


def is_production_mode() -> bool:
    """Detect if running in production mode"""
    if "--prod" in sys.argv: return True
    if "--dev" in sys.argv: return False
    
    # 1. Check if built assets exist (Primary indicator for production)
    if (get_resource_path("frontend/out")).exists():
        return True
        
    # 2. Check for compiled environment
    if getattr(sys, 'frozen', False) or hasattr(sys, 'nuitka_binary'):
        return True
        
    # 3. If in source tree with pyproject.toml and no assets, default to dev
    is_source_tree = (Path(__file__).parent / "pyproject.toml").exists()
    if is_source_tree: 
        return False
    
    return True # Default to prod if unsure

def get_assets_dir() -> Path:
    """Get assets directory - priority to packed assets in production"""
    # In production (Nuitka/PyInstaller), assets are absolute relative to resource path
    if is_production_mode():
        packed_assets = get_resource_path("assets")
        if packed_assets.exists(): return packed_assets
    
    # In development
    dev_path = Path(__file__).parent / "production" / "assets"
    if dev_path.exists(): return dev_path
    return Path(__file__).parent / "assets"

def check_port(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except: return False

def clean_pycache():
    if getattr(sys, 'frozen', False): return
    for pycache_dir in APP_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
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
        
        # On Windows, subprocess.Popen doesn't always find .cmd/.exe files if shell=False
        # unless we provide the absolute path. shutil.which helps here.
        executable = None
        if sys.platform == "win32" and not shell and args:
            executable = shutil.which(args[0])
            if executable:
                logging.debug(f"Resolved {args[0]} to {executable}")

        flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0
        kwargs = {"args": args, "cwd": cwd, "env": env, "creationflags": flags, "shell": shell}
        if executable:
            kwargs["executable"] = executable
        
        if capture_output:
            kwargs.update({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True})
        else:
            kwargs.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})
        
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
        self.is_compiled = hasattr(sys, 'nuitka_binary')
        self.is_frozen = getattr(sys, 'frozen', False) or self.is_compiled
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
                # Nếu chạy qua 'uv run' hoặc python trực tiếp, môi trường đã được uv quản lý
                logging.info("Environment managed by external runner (uv/python)")
                self.finished.emit(); return
            
            if self.is_compiled:
                logging.info("Native binary: skipping environment setup")
                self.finished.emit(); return

            venv_path, pyproject_path = APP_DIR / ".venv", APP_DIR / "pyproject.toml"
            if venv_path.exists() and (venv_path / "Scripts" / "python.exe").exists():
                self.status_changed.emit("Môi trường sẵn sàng"); self.finished.emit(); return
            
            logging.info("Environment setup required")
            self.status_changed.emit("Đang thiết lập môi trường...")
            self.progress_changed.emit(5)
            
            if not pyproject_path.exists():
                self.error.emit("Thiếu pyproject.toml"); return
            
            uv_path = self._find_uv()
            if not uv_path:
                self.error.emit("Không tìm thấy uv.exe"); return
            
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
                    logging.info(f"[uv] {line.strip()}")
                    self.status_changed.emit(f"Cài đặt: {line.strip()[:50]}")
                    self.progress_changed.emit(min(90, 10 + process.poll() or 10)) # Simple progress
            
            if process.returncode != 0:
                self.error.emit(f"Lỗi: {process.returncode}"); return
            
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
        self.is_frozen, self.is_production = getattr(sys, 'frozen', False), is_production_mode()
    
    def start(self):
        threading.Thread(target=self._start_servers, name="BackendStartThread", daemon=True).start()
    
    def _start_servers(self):
        try:
            self.status_changed.emit("Khởi động hệ thống...")
            # Determine the runner (the "python" executable)
            if hasattr(sys, 'nuitka_binary'):
                # Nuitka onefile mode sets this env var to the external .exe path
                exe_path = os.environ.get("NUITKA_ONEFILE_BINARY")
                python_exe = Path(exe_path) if exe_path else Path(sys.executable)
                logging.info(f"Nuitka runner identified: {python_exe}")
            elif getattr(sys, "frozen", False):
                # PyInstaller logic: search for the local venv we created
                python_exe = APP_DIR / ".venv" / "Scripts" / "python.exe"
            else:
                # Dev mode
                python_exe = Path(sys.executable)
            
            # Skip existence check for Nuitka because sys.executable/env var is the running file
            if not hasattr(sys, 'nuitka_binary') and not python_exe.exists():
                self.error.emit(f"Python not found: {python_exe}"); return
            
            self._start_backend(python_exe)
            
            # Chờ backend sẵn sàng với thông tin lỗi chi tiết nếu thất bại
            # Tăng lên 300 giây (5 phút) cho các máy yếu hoặc lần đầu tải AI models
            status = self._wait_for_port(self.PORT, timeout=300)
            if not status:
                # Tìm nguyên nhân lỗi từ file log
                error_msg = "Backend timeout (Port 8000)"
                try:
                    log_path = APP_DIR / "database" / "logs" / "backend_errors.log"
                    if log_path.exists():
                        lines = log_path.read_text(encoding="utf-8").splitlines()
                        relevant_errors = [l for l in lines[-10:] if "Error" in l or "Exception" in l or "Traceback" in l]
                        if relevant_errors:
                            error_msg = "Lỗi Backend: " + " | ".join(relevant_errors[-2:])
                except: pass
                self.error.emit(error_msg); return
            
            if self.is_production:
                url = f"http://127.0.0.1:{self.PORT}"
                logging.info("Production mode")
            else:
                self.status_changed.emit("Khởi động dev server...")
                self._start_frontend_dev()
                if not self._wait_for_port(self.DEV_PORT):
                    self.error.emit("Frontend timeout"); return
                url = f"http://127.0.0.1:{self.DEV_PORT}"
                logging.info("Dev mode")
            
            self.status_changed.emit("Mở ứng dụng...")
            time.sleep(0.3); self.ready.emit(url)
        except Exception as e:
            logging.exception("Server start error")
            self.error.emit(str(e))
    
    def _start_backend(self, python_exe: Path):
        env = os.environ.copy()
        env.update({"PYTHONPATH": str(APP_DIR), "PYTHONDONTWRITEBYTECODE": "1"})
        
        # Đảm bảo thư mục log tồn tại
        log_dir = APP_DIR / "database" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        backend_log = log_dir / "backend_errors.log"

        # Nếu python_exe là trình thông dịch (python.exe), ta cần truyền file script
        # Nếu là file chạy (EXE), ta chạy trực tiếp tham số --backend
        if python_exe.name.lower() == "python.exe" or python_exe.name.lower() == "python":
            cmd = [str(python_exe), str(APP_DIR / "app.py"), "--backend"]
        else:
            cmd = [str(python_exe), "--backend"]
            
        logging.info(f"Starting backend process: {' '.join(cmd)}")
        
        # Chạy backend và chuyển hướng cả stdout/stderr ra file để debug
        try:
            with open(backend_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- [BACKEND START] {datetime.now()} ---\n")
            
            # Mở file log ở chế độ append cho cả stdout và stderr
            log_file = open(backend_log, "a", encoding="utf-8")
            
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                cmd, cwd=str(APP_DIR), env=env, 
                stdout=log_file, 
                stderr=log_file,
                creationflags=flags | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.process_manager._processes.append(proc)
        except Exception as e:
            logging.error(f"Failed to spawn backend: {e}")
            raise

    def _start_frontend_dev(self):
        frontend_dir = APP_DIR / "frontend"
        if not (frontend_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), shell=True, capture_output=True)
        self.process_manager.spawn(args=["npm", "run", "dev"], cwd=str(frontend_dir), shell=True)

    def _wait_for_port(self, port: int, timeout: int = 60) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if check_port(port): return True
            time.sleep(0.5)
        return False


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


def main():
    # Fix cho lỗi "Unable to open monitor interface" và các cảnh báo Qt QPA
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.screen=false"
    os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=2"
    
    # Handle backend process mode
    if "--backend" in sys.argv:
        try:
            from backend.server import app as fastapi_app, initialize_backend
            import uvicorn
            
            # Khởi tạo các dịch vụ ngầm (Scheduler, Sync, v.v.)
            print("[cam_mana] Initializing backend services...")
            initialize_backend()
            
            # Ưu tiên sử dụng 127.0.0.1 để tránh vấn đề phân giải localhost
            print("[cam_mana] Starting Uvicorn server...")
            uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="info", access_log=False)
        except Exception as e:
            import traceback
            print(f"Backend process error: {e}")
            traceback.print_exc() # In chi tiết lỗi ra stderr (sẽ vào file log)
            sys.exit(1)
        return

    setup_logging()
    clean_pycache()
    logging.info(f"Starting CamMana UI (Mode: {'PROD' if is_production_mode() else 'DEV'})")
    
    app = QApplication(sys.argv)
    app.setApplicationName("CamMana")
    
    pixmap_path = get_assets_dir() / "icon.png"
    if not pixmap_path.exists():
        # Fallback for production builds where it might be in root assets
        pixmap_path = get_resource_path("assets/icon.png")
        
    pixmap = QPixmap(str(pixmap_path)).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation) if pixmap_path.exists() else QPixmap(256, 256)
    
    splash = QSplashScreen(pixmap); splash.show()
    app.processEvents()
    
    boot, backend = BootstrapManager(), BackendManager()
    main_win = None

    def fatal_error(msg):
        logging.error(f"FATAL: {msg}")
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
