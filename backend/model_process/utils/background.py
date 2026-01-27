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

from backend.settings import settings
from backend.model_process.functions.truck import TruckDetector

logger = logging.getLogger(__name__)


class BackgroundManager:
    """Manages background images for volume calculation."""
    
    _instance: Optional["BackgroundManager"] = None
    _scheduler_running: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detector = None
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
    
    def get_background_path(self, camera_id: str) -> Optional[Path]:
        """
        Get background image path for a camera.
        Returns the most recent background for that camera.
        
        Args:
            camera_id: Camera ID
            
        Returns:
            Path to background image or None if not exists
        """
        # Look for backgrounds with pattern: bg_{camera_id}_{timestamp}.jpg
        pattern = f"bg_{camera_id}_*.jpg"
        bgs = sorted(self.backgrounds_dir.glob(pattern), reverse=True)
        if bgs:
            return bgs[0]
        
        # Fallback: try old format bg_{camera_id}.jpg
        old_path = self.backgrounds_dir / f"bg_{camera_id}.jpg"
        if old_path.exists():
            return old_path
        
        # Fallback: try to find any background for this camera
        bgs = sorted(self.backgrounds_dir.glob("bg_*.jpg"), reverse=True)
        return bgs[0] if bgs else None
    
    def save_background(self, camera_id: str, image: Any) -> bool:
        """
        Save background image for a camera with timestamp.
        Format: bg_{camera_id}_{YYYY-MM-DD_HH-MM-SS}.jpg
        
        Args:
            camera_id: Camera ID
            image: OpenCV image (numpy array)
            
        Returns:
            True if saved successfully
        """
        try:
            self.backgrounds_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamp: 2026-01-27_23-55-07
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"bg_{camera_id}_{timestamp}.jpg"
            bg_path = self.backgrounds_dir / filename
            
            success = cv2.imwrite(str(bg_path), image)
            if success:
                logger.info(f"[BackgroundManager] Saved background: {filename}")
            return success
        except Exception as e:
            logger.error(f"[BackgroundManager] Failed to save background: {e}")
            return False
    
    async def capture_background_from_camera(self, camera_id: str) -> bool:
        """
        Capture background from a camera if no car is detected.
        
        Args:
            camera_id: Camera ID to capture from
            
        Returns:
            True if background was captured and saved
        """
        try:
            from backend.camera.logic import CameraLogic
            
            # Get camera info
            camera_logic = CameraLogic()
            camera = camera_logic.get_camera_by_id(camera_id)
            
            if not camera:
                logger.warning(f"[BackgroundManager] Camera {camera_id} not found")
                return False
            
            # Check if camera has volume_top_down function
            functions_str = camera.get("functions", "")
            functions = functions_str.split(",") if isinstance(functions_str, str) else functions_str
            if "volume_top_down" not in functions:
                logger.debug(f"[BackgroundManager] Camera {camera_id} is not volume_top_down")
                return False
            
            # Get RTSP URL and capture frame
            rtsp_url = camera.get("rtsp_url", "")
            if not rtsp_url:
                logger.warning(f"[BackgroundManager] No RTSP URL for camera {camera_id}")
                return False
            
            # Capture frame using OpenCV directly
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                logger.warning(f"[BackgroundManager] Failed to open stream for {camera_id}")
                return False
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                logger.warning(f"[BackgroundManager] Failed to capture frame from {camera_id}")
                return False
            
            # Check if car is detected
            result = self.detector.detect(frame)
            
            if result.get("detected"):
                logger.info(f"[BackgroundManager] Car detected on {camera_id}, skipping background capture")
                return False
            
            # No car detected - save as background
            return self.save_background(camera_id, frame)
            
        except Exception as e:
            logger.error(f"[BackgroundManager] Error capturing background from {camera_id}: {e}")
            return False
    
    async def update_all_backgrounds(self) -> Dict[str, Any]:
        """
        Update backgrounds for all volume_top_down cameras.
        
        Returns:
            Result dict with success/failure counts
        """
        from backend.camera.logic import CameraLogic
        
        result = {
            "checked": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }
        
        try:
            camera_logic = CameraLogic()
            cameras = camera_logic.get_cameras()
            
            for camera in cameras:
                functions_str = camera.get("functions", "")
                functions = functions_str.split(",") if isinstance(functions_str, str) else functions_str
                if "volume_top_down" not in functions:
                    continue
                
                result["checked"] += 1
                camera_id = camera.get("id") or camera.get("cam_id") or ""
                
                if not camera_id:
                    result["errors"] += 1
                    continue
                
                try:
                    success = await self.capture_background_from_camera(camera_id)
                    if success:
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
    
    def start_scheduler(self):
        """Start hourly background update scheduler."""
        if self._scheduler_running:
            return
        
        from apscheduler.schedulers.background import BackgroundScheduler
        
        def hourly_background_job():
            """Synchronous wrapper for async update."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.update_all_backgrounds())
                loop.close()
                logger.info(f"[BackgroundManager] Hourly update: {result}")
            except Exception as e:
                logger.error(f"[BackgroundManager] Hourly job error: {e}")
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(hourly_background_job, 'interval', hours=1)
        scheduler.start()
        self._scheduler_running = True
        logger.info("[BackgroundManager] Hourly background scheduler started")


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
