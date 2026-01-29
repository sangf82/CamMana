import os
import cv2
import time
import asyncio
import threading
import queue
import sys
import contextlib
from typing import Optional, AsyncGenerator, Dict, Any
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np
from backend.config import DATA_DIR, PROJECT_ROOT

# Suppress FFmpeg/OpenCV HEVC decoder warnings
# These appear when stream joins mid-GOP (normal for RTSP)
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"  # AV_LOG_QUIET

# Force TCP and add options for better HEVC stream handling
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "allowed_media_types;video|"
    "fflags;discardcorrupt|"
    "err_detect;ignore_err|"
    "analyzeduration;1000000|"
    "probesize;1000000"
)

# Additional FFmpeg log suppression (affects libavcodec)
os.environ["AV_LOG_FORCE_NOCOLOR"] = "1"
os.environ["FFREPORT"] = ""

# Flag to control HEVC warning suppression (set to False for debugging)
SUPPRESS_FFMPEG_STDERR = True

@contextlib.contextmanager
def suppress_ffmpeg_stderr():
    """
    Context manager to suppress FFmpeg stderr output during video capture.
    Works at the OS/C level by redirecting file descriptor 2.
    """
    if not SUPPRESS_FFMPEG_STDERR:
        yield
        return
    
    saved_stderr_fd = None
    null_fd = None
    try:
        saved_stderr_fd = os.dup(2)  # Save original stderr fd
        if sys.platform == 'win32':
            null_fd = os.open('NUL', os.O_WRONLY)
        else:
            null_fd = os.open('/dev/null', os.O_WRONLY)
        os.dup2(null_fd, 2)  # Redirect stderr to null
        yield
    except Exception:
        yield
    finally:
        # Restore stderr
        if saved_stderr_fd is not None:
            try:
                os.dup2(saved_stderr_fd, 2)
                os.close(saved_stderr_fd)
            except:
                pass
        if null_fd is not None:
            try:
                os.close(null_fd)
            except:
                pass

class VideoStreamer:
    def __init__(self, rtsp_uri: str, transport_mode: str = "tcp"):
        self.rtsp_uri = rtsp_uri
        self.transport_mode = transport_mode
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_streaming = False
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2.0
        self._last_frame_time = 0.0
        self._frame_timeout = 10.0
        
        self.capture_dir = PROJECT_ROOT / "database" / "captured_img"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        
        # Camera info for image naming and logging
        self.cam_id = "Unknown"
        self.cam_name = "Unknown"
        self.cam_location = "Unknown"
        
        # Stream info for resolution and FPS
        self._width = 0
        self._height = 0
        self._fps = 0.0
        self._fps_calc_frames = 0
        self._fps_calc_start = 0.0
    
    def set_camera_info(self, id: str = None, name: str = None, location: str = None):
        if id: self.cam_id = id
        if name: self.cam_name = name
        if location: self.cam_location = location
    
    def _capture_loop(self):
        while not self._stop_event.is_set():
            if self.cap is None or not self.cap.isOpened():
                if not self._try_reconnect():
                    self._stop_event.wait(1.0)
                continue
            try:
                with suppress_ffmpeg_stderr():
                    ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    self.frame_count += 1
                    self._last_frame_time = time.time()
                    self._reconnect_attempts = 0
                    
                    # Calculate FPS
                    self._fps_calc_frames += 1
                    elapsed = time.time() - self._fps_calc_start
                    if elapsed >= 1.0:
                        self._fps = self._fps_calc_frames / elapsed
                        self._fps_calc_frames = 0
                        self._fps_calc_start = time.time()
                    
                    # Manage queue
                    try:
                        while not self.frame_queue.empty():
                            try: self.frame_queue.get_nowait()
                            except queue.Empty: break
                        self.frame_queue.put_nowait(frame)
                    except queue.Full: pass
                elif self._last_frame_time > 0 and (time.time() - self._last_frame_time) > self._frame_timeout:
                    self._try_reconnect()
            except Exception as e:
                # Log error carefully
                self._try_reconnect()
    
    def _try_reconnect(self) -> bool:
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            return False
        self._reconnect_attempts += 1
        if self.cap: self.cap.release()
        time.sleep(self._reconnect_delay)
        try:
            # Set transport mode env before opening
            transport = "tcp" if self.transport_mode.lower() == "tcp" else "udp"
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;{transport}|"
                "fflags;discardcorrupt|"
                "err_detect;ignore_err|"
                "analyzeduration;1000000|"
                "probesize;1000000"
            )
            with suppress_ffmpeg_stderr():
                self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self._last_frame_time = time.time()
                return True
        except: pass
        return False
        
    def start(self) -> bool:
        self._stop_event.set()
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        if self.cap is not None: self.cap.release()
        
        self._stop_event.clear()
        try:
            # Set transport mode env
            transport = "tcp" if self.transport_mode.lower() == "tcp" else "udp"
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;{transport}|"
                "fflags;discardcorrupt|"
                "err_detect;ignore_err|"
                "analyzeduration;1000000|"
                "probesize;1000000"
            )

            with suppress_ffmpeg_stderr():
                self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
            if not self.cap.isOpened(): return False
            
            # Setup
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # Warmup - skip initial garbage/gray frames
            for _ in range(20):
                with suppress_ffmpeg_stderr():
                    ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    # Check if frame is alive (not solid gray/black)
                    _, stddev = cv2.meanStdDev(frame)
                    if stddev[0][0] > 5.0: # Good frame found
                        break
            
            self.is_streaming = self.cap.isOpened()
            if self.is_streaming:
                # Capture resolution
                self._width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self._height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self._fps_calc_start = time.time()
                self._fps_calc_frames = 0
                self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.capture_thread.start()
            return self.is_streaming
        except Exception as e:
            print(f"Capture Start Error: {e}")
            return False
    
    def stop(self):
        self.is_streaming = False
        self._stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def get_frame_jpeg(self) -> Optional[bytes]:
        try: frame = self.frame_queue.get_nowait()
        except queue.Empty: frame = self.last_frame
        if frame is not None:
            try:
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret: return jpeg.tobytes()
            except: pass
        return None
    
    async def generate_frames(self) -> AsyncGenerator[bytes, None]:
        empty_count = 0
        while self.is_streaming:
            jpeg = self.get_frame_jpeg()
            if jpeg:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
                empty_count = 0
            else:
                empty_count += 1
                if empty_count >= 50: break
            await asyncio.sleep(0.04)
            
    def capture_image(self) -> Dict[str, Any]:
        from backend.data_process.log.logic import logger_logic
        
        attempts = 0
        max_attempts = 3 # Original + 2 retries
        
        while attempts < max_attempts:
            if self.last_frame is None:
                if attempts < max_attempts - 1:
                    time.sleep(0.5)
                    attempts += 1
                    continue
                return {"success": False, "error": "No frame available after retries"}
            
            # Check frame quality (gray test)
            _, stddev = cv2.meanStdDev(self.last_frame)
            if stddev[0][0] <= 5.0: # Gray or solid frame
                logger_logic.log_event(self.cam_id, "Capture Warning", f"Gray frame detected (stddev={stddev[0][0]:.2f}). Retry {attempts+1}/2.")
                time.sleep(0.5)
                attempts += 1
                continue
            
            # Good frame found
            try:
                date_str = datetime.now().strftime("%d-%m-%Y")
                time_str = datetime.now().strftime("%H%M%S")
                # Filename: name_location_date_time.jpg
                safe_name = "".join(c for c in self.cam_name if c.isalnum() or c in ('-','_'))
                safe_loc = "".join(c for c in self.cam_location if c.isalnum() or c in ('-','_'))
                
                filename = self.capture_dir / f"{safe_name}_{safe_loc}_{date_str}_{time_str}.jpg"
                
                frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
                Image.fromarray(frame_rgb).save(filename, quality=95)
                
                if attempts > 0:
                    logger_logic.log_event(self.cam_id, "Capture Success", f"Captured after {attempts} retries.")
                else:
                    logger_logic.log_event(self.cam_id, "Capture Success", "Image captured successfully.")
                    
                return {"success": True, "path": str(filename), "filename": filename.name}
            except Exception as e:
                logger_logic.log_event(self.cam_id, "Capture Error", f"Save error: {str(e)}")
                return {"success": False, "error": str(e)}
        
        logger_logic.log_event(self.cam_id, "Capture Failure", f"Failed after {max_attempts-1} retries due to gray frames.")
        return {"success": False, "error": "Failed to capture non-gray image after retries"}

    def get_last_frame(self) -> Optional[np.ndarray]:
        if self.last_frame is not None:
            return self.last_frame.copy()
        return None

    def get_stream_info(self) -> Dict[str, Any]:
        """Get current stream resolution and FPS."""
        resolution = f"{self._width}x{self._height}" if self._width > 0 else "N/A"
        return {
            "resolution": resolution,
            "width": self._width,
            "height": self._height,
            "fps": round(self._fps, 1)
        }
