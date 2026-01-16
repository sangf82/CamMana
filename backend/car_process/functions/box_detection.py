"""
Box Detection Function

Estimates truck cargo box dimensions (length, width, height).
Placeholder for future implementation.
"""

from typing import Dict, Any
import numpy as np

class BoxDetectionFunction:
    """Truck box dimension estimation"""
    
    # Function Metadata
    FUNCTION_ID = "box_detect"
    FUNCTION_NAME = "Kích thước thùng xe"
    DESCRIPTION = "Tính toán dài x rộng x cao của thùng xe"
    INPUT_SOURCE = "side_cam"
    PARALLEL_GROUP = 3  # Runs after basic detections
    
    def __init__(self):
        """Initialize box detector"""
        pass
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect truck box dimensions.
        
        Args:
            frame: Input image (numpy array, BGR format)
            
        Returns:
            {
                "success": bool,
                "length_m": float,
                "width_m": float,
                "height_m": float,
                "volume_m3": float
            }
        """
        # TODO: Implement using depth estimation or stereo vision
        return {
            "success": False,
            "error": "Box detection not yet implemented",
            "status": "coming_soon"
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return function metadata"""
        return {
            "id": self.FUNCTION_ID,
            "name": self.FUNCTION_NAME,
            "description": self.DESCRIPTION,
            "input_source": self.INPUT_SOURCE,
            "parallel_group": self.PARALLEL_GROUP,
            "status": "coming_soon"
        }
