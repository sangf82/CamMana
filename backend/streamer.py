"""
Video Streamer - Handles RTSP to MJPEG conversion for web streaming
"""

import os
import cv2
import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Suppress OpenCV/FFmpeg warnings
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
# Force TCP for stability and reduced artifacts, increase buffer for high res streams
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024000"


class VideoStreamer:
    """Handles RTSP video streaming and frame capture"""
    
    def __init__(self, rtsp_uri: str):
        self.rtsp_uri = rtsp_uri
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_streaming = False
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        
        # Get capture dir from env or default
        capture_path = os.getenv("CAPTURE_DIR_PATH", "database/captured_img")
        self.capture_dir = Path(capture_path)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        
    def start(self) -> bool:
        """Start video capture"""
        if self.cap is not None:
            self.cap.release()
        
        self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
        
        # Optimize for low latency but stable connection
        # We assume buffer management is handled better by default or specific flags if needed
        
        # Read initial frames to stabilize and clear any initial garbage
        for _ in range(10):
            if self.cap.isOpened():
                self.cap.read()
        
        self.is_streaming = self.cap.isOpened()
        return self.is_streaming
    
    def stop(self):
        """Stop video capture"""
        self.is_streaming = False
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read a single frame"""
        if self.cap is None or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            self.last_frame = frame
            self.frame_count += 1
            return frame
        return None
    
    def get_frame_jpeg(self) -> Optional[bytes]:
        """Get current frame as JPEG bytes"""
        frame = self.read_frame()
        if frame is None:
            # Return last frame if current read failed
            frame = self.last_frame
        
        if frame is not None:
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                return jpeg.tobytes()
        return None
    
    async def generate_frames(self) -> AsyncGenerator[bytes, None]:
        """Generate MJPEG frames for streaming"""
        while self.is_streaming:
            jpeg = self.get_frame_jpeg()
            if jpeg:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
                )
            await asyncio.sleep(0.033)  # ~30 FPS
    
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
