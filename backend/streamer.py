"""
Video Streamer - Handles RTSP to MJPEG conversion for web streaming
"""

import os
import cv2
import asyncio
import threading
import queue
from typing import Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Suppress FFmpeg/OpenCV warnings
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"  # AV_LOG_QUIET
# Force TCP transport for RTSP stability
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"


class VideoStreamer:
    """Handles RTSP video streaming and frame capture with thread-safe design"""
    
    def __init__(self, rtsp_uri: str):
        self.rtsp_uri = rtsp_uri
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_streaming = False
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        
        # Thread-safe frame queue (only keep latest frame to reduce latency)
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Get capture dir from env or default
        capture_path = os.getenv("CAPTURE_DIR_PATH", "database/captured_img")
        self.capture_dir = Path(capture_path)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
    
    def _capture_loop(self):
        """Background thread that continuously reads frames"""
        print(f"[Streamer] Capture thread started for {self.rtsp_uri}")
        
        while not self._stop_event.is_set():
            if self.cap is None or not self.cap.isOpened():
                self._stop_event.wait(0.1)
                continue
            
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    self.frame_count += 1
                    
                    # Put frame in queue, drop old frame if full
                    try:
                        # Clear queue to keep only latest
                        while not self.frame_queue.empty():
                            try:
                                self.frame_queue.get_nowait()
                            except queue.Empty:
                                break
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        pass
            except Exception as e:
                print(f"[Streamer] Capture error: {e}")
                self._stop_event.wait(0.1)
        
        print("[Streamer] Capture thread stopped")
        
    def start(self) -> bool:
        """Start video capture"""
        self._stop_event.set()  # Stop any existing thread
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        
        if self.cap is not None:
            self.cap.release()
        
        self._stop_event.clear()
        self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
        
        if not self.cap.isOpened():
            return False
        
        # Read initial frames to warm up decoder
        warmup_count = 0
        for _ in range(30):
            ret, frame = self.cap.read()
            if ret:
                self.last_frame = frame
                warmup_count += 1
                if warmup_count >= 5:
                    break
        
        self.is_streaming = self.cap.isOpened()
        
        # Start background capture thread
        if self.is_streaming:
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
        
        return self.is_streaming
    
    def stop(self):
        """Stop video capture"""
        self.is_streaming = False
        self._stop_event.set()
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def get_frame_jpeg(self) -> Optional[bytes]:
        """Get latest frame as JPEG bytes (thread-safe)"""
        frame = None
        
        # Try to get latest frame from queue
        try:
            frame = self.frame_queue.get_nowait()
        except queue.Empty:
            frame = self.last_frame
        
        if frame is not None:
            try:
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret:
                    return jpeg.tobytes()
            except Exception:
                pass
        return None
    
    async def generate_frames(self) -> AsyncGenerator[bytes, None]:
        """Generate MJPEG frames for streaming"""
        empty_count = 0
        max_empty = 100  # Stop after ~3 seconds of no frames
        
        while self.is_streaming:
            jpeg = self.get_frame_jpeg()
            if jpeg:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
                )
                empty_count = 0
            else:
                empty_count += 1
                if empty_count >= max_empty:
                    print("[Streamer] No frames, stopping stream")
                    break
            
            # Small delay - frames are produced by capture thread
            await asyncio.sleep(0.03)  # ~30 FPS target
    
    def get_frame_size(self) -> tuple:
        """Get current frame dimensions"""
        if self.cap:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return width, height
        return 0, 0
    
    def capture_image(self) -> dict:
        """Capture current frame and save to file"""
        if self.last_frame is None:
            return {"success": False, "error": "No frame available"}
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.capture_dir / f"capture_{timestamp}.jpg"
            
            # Convert BGR to RGB and save
            frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.save(filename, quality=95)
            
            return {
                "success": True,
                "filename": str(filename),
                "timestamp": timestamp
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
