"""Video Streamer - RTSP to MJPEG conversion with auto-reconnection"""
import os
import cv2
import time
import asyncio
import threading
import queue
from typing import Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np
from dotenv import load_dotenv

load_dotenv()
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
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
        capture_path = os.getenv("CAPTURE_DIR_PATH", "database/saved_image")
        self.capture_dir = Path(capture_path)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        
        # Camera info for image naming (set by camera manager)
        self.cam_code = None
        self.cam_location = None
    
    def set_camera_info(self, cam_code: str = None, location: str = None):
        """Set camera information for image naming"""
        self.cam_code = cam_code
        self.cam_location = location
    
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
                    try:
                        while not self.frame_queue.empty():
                            try: self.frame_queue.get_nowait()
                            except queue.Empty: break
                        self.frame_queue.put_nowait(frame)
                    except queue.Full: pass
                elif self._last_frame_time > 0 and (time.time() - self._last_frame_time) > self._frame_timeout:
                    self._try_reconnect()
            except Exception as e:
                print(f"[Streamer] Error: {e}")
                self._try_reconnect()
    
    def _try_reconnect(self) -> bool:
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            return False
        self._reconnect_attempts += 1
        if self.cap: self.cap.release()
        time.sleep(self._reconnect_delay)
        self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self._last_frame_time = time.time()
            return True
        return False
        
    def start(self) -> bool:
        self._stop_event.set()
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        if self.cap is not None: self.cap.release()
        
        self._stop_event.clear()
        self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
        if not self.cap.isOpened(): return False
        
        # Set to maximum resolution available from camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 4096)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Warmup - read a few frames to stabilize
        for _ in range(30):
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.last_frame = frame
                break
        
        self.is_streaming = self.cap.isOpened()
        if self.is_streaming:
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
        return self.is_streaming
    
    def stop(self):
        self.is_streaming = False
        self._stop_event.set()
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def get_frame_jpeg(self) -> Optional[bytes]:
        try: frame = self.frame_queue.get_nowait()
        except queue.Empty: frame = self.last_frame
        if frame is not None:
            try:
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 98])
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
                if empty_count >= 100: break
            await asyncio.sleep(0.03)
    
    def get_frame_size(self) -> tuple:
        if self.cap:
            return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return 0, 0
    
    def get_stream_info(self) -> dict:
        if self.cap:
            w, h = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            return {"width": w, "height": h, "fps": round(fps, 1) if fps > 0 else 0, "resolution": f"{w}x{h}", "frame_count": self.frame_count}
        return {"width": 0, "height": 0, "fps": 0, "resolution": "N/A", "frame_count": 0}
    
    def capture_image(self) -> dict:
        """Capture image with format: cam-code_location_date.jpg"""
        if self.last_frame is None:
            return {"success": False, "error": "No frame available"}
        try:
            # Generate filename: cam-code_location_date
            date_str = datetime.now().strftime("%d-%m-%Y")
            time_str = datetime.now().strftime("%H%M%S")
            
            # Build filename parts
            cam_part = self.cam_code if self.cam_code else "CAM-XX"
            loc_part = self.cam_location.replace(" ", "-") if self.cam_location else "Unknown"
            
            filename = self.capture_dir / f"{cam_part}_{loc_part}_{date_str}_{time_str}.jpg"
            
            # Save image
            frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
            Image.fromarray(frame_rgb).save(filename, quality=95)
            
            return {
                "success": True, 
                "filename": filename.name,
                "path": str(filename),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def capture_high_res(self) -> Optional[np.ndarray]:
        """Capture a high resolution frame directly from RTSP for detection/analysis"""
        # Simply return last_frame for now - opening a new RTSP connection is unreliable
        # The stream already captures at the camera's native resolution
        return self.last_frame
    
    def get_capture_frame(self) -> Optional[np.ndarray]:
        """Get best available frame for capture"""
        # Return the last frame from the stream - it's already at camera's resolution
        if self.last_frame is not None:
            return self.last_frame.copy()
        return None
