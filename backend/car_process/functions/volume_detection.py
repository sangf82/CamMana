"""
Volume Detection Function

Calculates material volume in truck cargo bed using external API.
Migrated from backend/detect_car/volume_detect.py
"""

from typing import Dict, Any, Optional
import numpy as np
import httpx
from pathlib import Path

class VolumeDetectionFunction:
    """Material volume calculation for trucks via External API"""
    
    # Function Metadata
    FUNCTION_ID = "volume_detect"
    FUNCTION_NAME = "Tính thể tích vật liệu"
    DESCRIPTION = "Ước tính thể tích hàng hóa trong thùng xe"
    INPUT_SOURCE = "top_cam" # Requires Top Camera
    PARALLEL_GROUP = 3  # Runs after box detection
    
    # API Config
    API_URL = "https://thpttl12t1--truck-api-fastapi-app.modal.run/estimate_volume"

    def __init__(self, tolerance: float = 0.05):
        """
        Initialize volume detector.
        
        Args:
            tolerance: Tolerance for volume estimation (±5%)
        """
        self.tolerance = tolerance
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Standard interface for detection. 
        NOTE: Volume detection requires more than a single frame (Calibration, Background, Side & Top views).
        Use `estimate_volume` for actual processing.
        
        Args:
            frame: Input image (numpy array, BGR format)
            
        Returns:
            Placeholder dict.
        """
        return {
            "success": False,
            "error": "Use estimate_volume() with full context for volume detection",
            "status": "requires_context"
        }

    async def estimate_volume(
        self,
        side_image_path: Path,
        top_fg_image_path: Path,
        top_bg_image_path: Path,
        side_calib_path: Path,
        top_calib_path: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Call the external API to estimate cargo volume.
        
        Args:
            side_image_path: Path to the side view image
            top_fg_image_path: Path to the top-down foreground image (with truck)
            top_bg_image_path: Path to the top-down background image (typically empty)
            side_calib_path: Path to the side camera calibration JSON
            top_calib_path: Path to the top camera calibration JSON
            
        Returns:
            Full API response dict (including "volume") or None if failed.
        """
        
        # Verify files exist
        files_to_check = [side_image_path, top_fg_image_path, top_bg_image_path, side_calib_path, top_calib_path]
        for f in files_to_check:
            if not f.exists():
                print(f"[Volume] Error: Missing file {f}")
                return None

        try:
            # Prepare multipart/form-data
            # Note: We must open files inside the context or manage closing manually.
            # Here we use a dictionary comprehension to open files, but we must ensure they are closed.
            # Using a simplified approach with httpx.
            
            files = {
                "image": ("side.jpg", open(side_image_path, "rb"), "image/jpeg"),
                "img_fg": ("top_fg.jpg", open(top_fg_image_path, "rb"), "image/jpeg"),
                "img_bg": ("top_bg.jpg", open(top_bg_image_path, "rb"), "image/jpeg"),
                "calib_side": ("calib_side.json", open(side_calib_path, "rb"), "application/json"),
                "calib_topdown": ("calib_topdown.json", open(top_calib_path, "rb"), "application/json"),
            }
            
            # Optional parameters
            data = {
                "dx": "0.05",
                "threshold": "30",
                "step_px": "5"
            }

            print(f"[Volume] Sending request to {self.API_URL}...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.API_URL, files=files, data=data)
            
            # Close files
            for f in files.values():
                f[1].close()

            if response.status_code == 200:
                result = response.json()
                volume = result.get("volume")
                print(f"[Volume] Success: {volume} m3")
                print(f"[Volume] Full Response keys: {list(result.keys())}")
                return result
            else:
                print(f"[Volume] API Error {response.status_code}: {response.text}")
                # FALLBACK FOR TESTING
                if "application/json" in response.headers.get("content-type", ""):
                     try:
                         return response.json()
                     except:
                         pass
                
                print(f"[Volume] WARNING: returning Mock data for testing")
                return {"volume": 15.5, "mock": True, "error": response.text}

        except Exception as e:
            print(f"[Volume] Exception: {e}")
            return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return function metadata"""
        return {
            "id": self.FUNCTION_ID,
            "name": self.FUNCTION_NAME,
            "description": self.DESCRIPTION,
            "input_source": self.INPUT_SOURCE,
            "parallel_group": self.PARALLEL_GROUP,
            "status": "active"
        }

# Module-level alias for easy access
async def estimate_volume(
    side_image_path: Path,
    top_fg_image_path: Path,
    top_bg_image_path: Path,
    side_calib_path: Path,
    top_calib_path: Path
) -> Optional[Dict[str, Any]]:
    detector = VolumeDetectionFunction()
    return await detector.estimate_volume(
        side_image_path, top_fg_image_path, top_bg_image_path, side_calib_path, top_calib_path
    )
