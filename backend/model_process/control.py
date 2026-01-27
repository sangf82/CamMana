
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
import numpy as np
from pathlib import Path

from backend.model_process.functions.truck import TruckDetector
from backend.model_process.functions.plate import PlateDetector
from backend.model_process.functions.wheel import WheelDetector
from backend.model_process.functions.color import ColorDetector
from backend.model_process.functions.volume import VolumeDetector

logger = logging.getLogger(__name__)

class ModelOrchestrator:
    """
    Orchestrates the execution of AI models based on requested functions.
    Handles parallel execution and error containment.
    """
    def __init__(self):
        # Initialize detectors
        # Note: Heavy models (like YOLO in TruckDetector) might lazy load inside their detect methods
        self.truck_detector = TruckDetector()
        self.plate_detector = PlateDetector()
        self.wheel_detector = WheelDetector()
        self.color_detector = ColorDetector()
        self.volume_detector = VolumeDetector()

    async def process_image(self, frame: np.ndarray, functions: List[str]) -> Dict[str, Any]:
        """
        Run specified detection functions on a single image frame in parallel.
        
        Args:
            frame: Input image (BGR numpy array)
            functions: List of function names to run (e.g., ['plate', 'truck', 'color'])
            
        Returns:
            Dictionary with keys as function names and values as detection results.
        """
        if frame is None:
            logger.warning("ModelOrchestrator received None frame")
            return {f: {"error": "Empty frame"} for f in functions}

        tasks = []
        
        # Helper to run synchronous detect methods in thread pool
        async def run_sync_detect(name: str, detector: Any) -> tuple[str, Dict]:
            try:
                # Use to_thread to prevent blocking the event loop
                result = await asyncio.to_thread(detector.detect, frame)
                return name, result
            except Exception as e:
                logger.error(f"Error running {name} detection: {e}", exc_info=True)
                return name, {"detected": False, "error": str(e)}

        # Map function names to detectors
        # Supports various aliases for robustness
        for func in functions:
            func_lower = func.lower().strip()
            
            if func_lower in ["truck", "box", "truck_detect", "box_detect", "car", "car_detect"]:
                tasks.append(run_sync_detect("truck", self.truck_detector))
                
            elif func_lower in ["plate", "alpr", "plate_detect"]:
                tasks.append(run_sync_detect("plate", self.plate_detector))
                
            elif func_lower in ["wheel", "wheel_detect", "count_wheels"]:
                tasks.append(run_sync_detect("wheel", self.wheel_detector))
                
            elif func_lower in ["color", "color_detect"]:
                tasks.append(run_sync_detect("color", self.color_detector))
            
            # Volume is NOT handled here as it requires multiple images

        if not tasks:
            return {}

        # Run all selected tasks in parallel
        results_list = await asyncio.gather(*tasks)
        
        # Aggregate results
        results = {name: res for name, res in results_list}
        return results

    async def process_volume(
        self, 
        side_image_path: Path, 
        top_fg_image_path: Path, 
        top_bg_image_path: Path,
        side_calib_path: Path,
        top_calib_path: Path
    ) -> Dict[str, Any]:
        """
        Special orchestration for volume detection which requires specific file inputs.
        """
        try:
            # VolumeDetector is already async
            return await self.volume_detector.estimate_volume(
                side_image_path, 
                top_fg_image_path, 
                top_bg_image_path,
                side_calib_path, 
                top_calib_path
            )
        except Exception as e:
            logger.error(f"Error in process_volume: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

# Singleton instance
orchestrator = ModelOrchestrator()
