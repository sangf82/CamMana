"""
Background Manager - Handles automatic background capture and storage

Captures background images from volume_top_down cameras when no car is detected.
Updates backgrounds every hour and stores in database/backgrounds folder.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import cv2
import numpy as np

from backend.settings import settings
from backend.model_process.functions.truck import TruckDetector
from backend.camera.capture import suppress_ffmpeg_stderr

logger = logging.getLogger(__name__)


class BackgroundManager:
    """Manages background images for volume calculation."""
    
    _instance: Optional["BackgroundManager"] = None
    _scheduler_running: bool = False
    _scheduler = None
    _current_interval_hours: int = 1
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detector = None
            cls._instance._scheduler = None
            cls._instance._current_interval_hours = 1
        return cls._instance
    
    @property
    def backgrounds_dir(self) -> Path:
        """Get backgrounds directory."""
        return settings.backgrounds_dir
    
    @property
    def detector(self) -> TruckDetector:
        """Lazy-load truck detector."""
        if self._detector is None:
            self._detector = TruckDetector(confidence=0.3)
        return self._detector
    
    def get_background_path(self, camera_name: str) -> Optional[Path]:
        """
        Get background image path for a camera.
        Returns the most recent background for that camera.
        
        Args:
            camera_name: Camera name (display name)
            
        Returns:
            Path to background image or None if not exists
        """
        # Sanitize camera name for matching (same as in save_background)
        safe_name = camera_name.replace(" ", "_").replace("/", "-")
        
        # Look for backgrounds with new pattern: background_{cam_name}_{timestamp}.jpg
        pattern = f"background_{safe_name}_*.jpg"
        bgs = sorted(self.backgrounds_dir.glob(pattern), reverse=True)
        if bgs:
            return bgs[0]
        
        # Fallback: try any background file
        bgs = sorted(self.backgrounds_dir.glob("background_*.jpg"), reverse=True)
        return bgs[0] if bgs else None
    
    def save_background(self, camera_name: str, image: Any) -> str:
        """
        Save background image for a camera with timestamp.
        Format: background_{cam_name}_{dd-mm-yyyy_hh-mm-ss}.jpg
        
        Args:
            camera_name: Camera name (display name)
            image: OpenCV image (numpy array)
            
        Returns:
            Filename if saved successfully, empty string otherwise
        """
        try:
            self.backgrounds_dir.mkdir(parents=True, exist_ok=True)
            
            # Sanitize camera name for filename (replace spaces with underscores)
            safe_name = camera_name.replace(" ", "_").replace("/", "-")
            
            # Generate timestamp: dd-mm-yyyy_hh-mm-ss
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            filename = f"background_{safe_name}_{timestamp}.jpg"
            bg_path = self.backgrounds_dir / filename
            
            success = cv2.imwrite(str(bg_path), image)
            if success:
                logger.info(f"[BackgroundManager] Saved background: {filename}")
                return filename
            return ""
        except Exception as e:
            logger.error(f"[BackgroundManager] Failed to save background: {e}")
            return ""
    
    async def capture_background_from_camera(self, camera_id: str) -> Dict[str, Any]:
        """
        Capture background from a camera if no car is detected.
        
        Args:
            camera_id: Camera ID to capture from
            
        Returns:
            Dict with success status and captured filename
        """
        try:
            from backend.camera.logic import CameraLogic
            from backend.data_process.camera_type.logic import CameraTypeLogic
            from backend.camera.connection import CameraConnection, CameraConnectionConfig
            import asyncio
            
            # Get camera info
            camera_logic = CameraLogic()
            camera = camera_logic.get_camera_by_id(camera_id)
            
            if not camera:
                logger.warning(f"[BackgroundManager] Camera {camera_id} not found")
                return {"success": False, "error": "Camera not found"}
            
            cam_name = camera.get("name", f"Camera_{camera_id}")
            
            # Get functions from camera type
            types_logic = CameraTypeLogic()
            types_map = {t['name']: t.get('functions', '') for t in types_logic.get_types()}
            cam_type = camera.get('type', '')
            functions_str = types_map.get(cam_type, '')
            
            # Check if camera has volume_top_down function
            functions = functions_str.split(";") if isinstance(functions_str, str) else functions_str
            if "volume_top_down" not in functions:
                logger.debug(f"[BackgroundManager] Camera {camera_id} is not volume_top_down")
                return {"success": False, "error": "Camera is not volume_top_down"}
            
            # Connect to camera via ONVIF to get stream URI
            ip = camera.get('ip', '')
            try:
                port = int(camera.get('port', 80))
            except:
                port = 80
            
            config = CameraConnectionConfig(
                ip=ip,
                port=port,
                user=camera.get('username', ''),
                password=camera.get('password', '')
            )
            
            conn = CameraConnection(config)
            res = await asyncio.to_thread(conn.connect)
            
            if not res.get('success'):
                logger.warning(f"[BackgroundManager] Failed to connect to camera {camera_id}: {res.get('error')}")
                return {"success": False, "error": f"Connection failed: {res.get('error')}"}
            
            stream_uri = res.get('stream_uri', '')
            if not stream_uri:
                conn.disconnect()
                logger.warning(f"[BackgroundManager] No stream URI for camera {camera_id}")
                return {"success": False, "error": "No stream URI"}
            
            # Capture frame using OpenCV with robust RTSP options
            transport = camera.get('transport_mode', 'tcp').lower()
            if transport not in ['tcp', 'udp']:
                transport = 'tcp'
                
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;{transport}|"
                "fflags;discardcorrupt|"
                "err_detect;ignore_err|"
                "analyzeduration;1000000|"
                "probesize;1000000"
            )
            
            with suppress_ffmpeg_stderr():
                cap = cv2.VideoCapture(stream_uri, cv2.CAP_FFMPEG)
                
            if not cap.isOpened():
                conn.disconnect()
                logger.warning(f"[BackgroundManager] Failed to open stream for {camera_id}")
                return {"success": False, "error": "Failed to open stream"}
            
            # Setup buffer
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Warmup - instead of a hard 10s wait, we read frames and check for stability
            logger.info(f"[BackgroundManager] Warming up camera {camera_id}...")
            frame = None
            max_warmup_frames = 60 # ~2 seconds at 30fps
            
            with suppress_ffmpeg_stderr():
                for i in range(max_warmup_frames):
                    ret, f = cap.read()
                    if ret and f is not None:
                        frame = f
                        # Check if frame is stable (not solid color)
                        _, stddev = cv2.meanStdDev(frame)
                        if stddev[0][0] > 10.0:  # Frame has enough variation
                            if i > 5: # Skip first few frames even if "good"
                                break
                    await asyncio.sleep(0.01)
            
            cap.release()
            conn.disconnect()
            
            if frame is None:
                logger.warning(f"[BackgroundManager] Failed to capture stable frame from {camera_id}")
                return {"success": False, "error": "Failed to capture stable frame"}
            
            # Check if car is detected (skip detection for forced capture)
            # result = self.detector.detect(frame)
            # if result.get("detected"):
            #     logger.info(f"[BackgroundManager] Car detected on {camera_id}, skipping")
            #     return {"success": False, "error": "Car detected"}
            
            # Save as background with camera name
            filename = self.save_background(cam_name, frame)
            if filename:
                return {"success": True, "filename": filename, "camera_name": cam_name}
            return {"success": False, "error": "Failed to save image"}
            
        except Exception as e:
            logger.error(f"[BackgroundManager] Error capturing background from {camera_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_all_backgrounds(self) -> Dict[str, Any]:
        """
        Update backgrounds for all volume_top_down cameras.
        
        Returns:
            Result dict with success/failure counts
        """
        from backend.camera.logic import CameraLogic
        from backend.data_process.camera_type.logic import CameraTypeLogic
        
        result = {
            "checked": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }
        
        try:
            camera_logic = CameraLogic()
            types_logic = CameraTypeLogic()
            
            cameras = camera_logic.get_cameras()
            types_map = {t['name']: t.get('functions', '') for t in types_logic.get_types()}
            
            for camera in cameras:
                # Get functions from camera type
                cam_type = camera.get('type', '')
                functions_str = types_map.get(cam_type, '')
                functions = functions_str.split(";") if isinstance(functions_str, str) else functions_str
                if "volume_top_down" not in functions:
                    continue
                
                result["checked"] += 1
                camera_id = camera.get("id") or camera.get("cam_id") or ""
                
                if not camera_id:
                    result["errors"] += 1
                    continue
                
                try:
                    capture_result = await self.capture_background_from_camera(camera_id)
                    if capture_result.get("success"):
                        result["updated"] += 1
                    else:
                        result["skipped"] += 1
                except Exception as e:
                    logger.error(f"[BackgroundManager] Error with camera {camera_id}: {e}")
                    result["errors"] += 1
            
            logger.info(f"[BackgroundManager] Background update complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[BackgroundManager] Failed to update backgrounds: {e}")
            result["errors"] += 1
            return result
    
    def start_scheduler(self, interval_hours: int = 1):
        """
        Start background update scheduler with configurable interval.
        
        Args:
            interval_hours: Update interval in hours (1, 2, 4, or 24)
        """
        if self._scheduler_running:
            return
        
        from apscheduler.schedulers.background import BackgroundScheduler
        
        def background_update_job():
            """Synchronous wrapper for async update."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.update_all_backgrounds())
                loop.close()
                logger.info(f"[BackgroundManager] Scheduled update: {result}")
            except Exception as e:
                logger.error(f"[BackgroundManager] Scheduled job error: {e}")
        
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            background_update_job, 
            'interval', 
            hours=interval_hours,
            id='background_update'
        )
        self._scheduler.start()
        self._scheduler_running = True
        self._current_interval_hours = interval_hours
        logger.info(f"[BackgroundManager] Background scheduler started (interval: {interval_hours}h)")
    
    def update_scheduler_interval(self, interval_hours: int):
        """
        Update the scheduler interval.
        
        Args:
            interval_hours: New interval in hours (1, 2, 4, or 24)
        """
        if not self._scheduler or not self._scheduler_running:
            # Start scheduler if not running
            self.start_scheduler(interval_hours)
            return
        
        if interval_hours == self._current_interval_hours:
            return
        
        try:
            # Reschedule the job with new interval
            self._scheduler.reschedule_job(
                'background_update',
                trigger='interval',
                hours=interval_hours
            )
            self._current_interval_hours = interval_hours
            logger.info(f"[BackgroundManager] Scheduler interval updated to {interval_hours}h")
        except Exception as e:
            logger.error(f"[BackgroundManager] Failed to update interval: {e}")
    
    def stop_scheduler(self):
        """Stop the background scheduler."""
        if self._scheduler and self._scheduler_running:
            self._scheduler.shutdown(wait=False)
            self._scheduler_running = False
            self._scheduler = None
            logger.info("[BackgroundManager] Scheduler stopped")


# Module-level instance
background_manager = BackgroundManager()


def get_background_for_camera(camera_id: str) -> Optional[Path]:
    """
    Get background image path for a camera.
    
    Args:
        camera_id: Camera ID
        
    Returns:
        Path to background image or None
    """
    return background_manager.get_background_path(camera_id)


async def capture_background_if_empty(camera_id: str, frame: Any) -> bool:
    """
    Capture and save background if no car detected in frame.
    Called during checkout when no car is detected.
    
    Args:
        camera_id: Camera ID
        frame: Current frame from camera
        
    Returns:
        True if background was saved
    """
    # Check if car is detected
    result = background_manager.detector.detect(frame)
    
    if result.get("detected"):
        return False
    
    # No car - save as background
    return background_manager.save_background(camera_id, frame)
