import os
import cv2
import time
import asyncio
import threading
import queue
from typing import Optional, AsyncGenerator, Dict, Any
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np
from backend.config import DATA_DIR, PROJECT_ROOT

os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
# Try to use TCP for RTSP (more stable)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

class VideoStreamer:
    def __init__(self, rtsp_uri: str):
        self.rtsp_uri = rtsp_uri
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
        
        # Camera info for image naming
        self.cam_name = "Unknown"
        self.cam_location = "Unknown"
    
    def set_camera_info(self, name: str = None, location: str = None):
        if name: self.cam_name = name
        if location: self.cam_location = location
    
    def _capture_loop(self):
        while not self._stop_event.is_set():
            if self.cap is None or not self.cap.isOpened():
                if not self._try_reconnect():
                    self._stop_event.wait(1.0)
                continue
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    self.frame_count += 1
                    self._last_frame_time = time.time()
                    self._reconnect_attempts = 0
                    
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
            self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
            if not self.cap.isOpened(): return False
            
            # Setup
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # Warmup
            for _ in range(5):
                ret, frame = self.cap.read()
                if ret: self.last_frame = frame
            
            self.is_streaming = self.cap.isOpened()
            if self.is_streaming:
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
        if self.last_frame is None:
            return {"success": False, "error": "No frame"}
        try:
            date_str = datetime.now().strftime("%d-%m-%Y")
            time_str = datetime.now().strftime("%H%M%S")
            # Filename: name_location_date_time.jpg
            safe_name = "".join(c for c in self.cam_name if c.isalnum() or c in ('-','_'))
            safe_loc = "".join(c for c in self.cam_location if c.isalnum() or c in ('-','_'))
            
            filename = self.capture_dir / f"{safe_name}_{safe_loc}_{date_str}_{time_str}.jpg"
            
            frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
            Image.fromarray(frame_rgb).save(filename, quality=95)
            return {"success": True, "path": str(filename), "filename": filename.name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_last_frame(self) -> Optional[np.ndarray]:
        if self.last_frame is not None:
            return self.last_frame.copy()
        return None
