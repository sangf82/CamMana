"""
Wheel Detection Function

Counts the number of wheels/axles on a vehicle.
Migrated from backend/detect_car/info_detect.py
"""

from typing import Dict, Any
import numpy as np
import cv2

class WheelDetectionFunction:
    """Wheel counting using edge detection and circular Hough transform"""
    
    # Function Metadata
    FUNCTION_ID = "wheel_detect"
    FUNCTION_NAME = "Nhận diện số bánh"
    DESCRIPTION = "Đếm số bánh và nhận diện loại trục xe"
    INPUT_SOURCE = "side_cam"  # Side view best for wheel counting
    PARALLEL_GROUP = 2  # Can run in parallel with plate/color
    
    def __init__(self):
        """Initialize wheel detector"""
        pass
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Count wheels in a vehicle image.
        
        Args:
            frame: Input image (numpy array, BGR format)
            
        Returns:
            {
                "success": bool,
                "wheel_count": int,  # e.g., 4, 6, 10
                "axle_count": int,   # Optional
                "confidence": float
            }
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            
            # Detect circles using Hough transform
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=50,
                param1=100,
                param2=30,
                minRadius=20,
                maxRadius=100
            )
            
            if circles is None:
                # Fallback: estimate based on vehicle size
                height, width = frame.shape[:2]
                
                # Simple heuristic: if width > height, likely side view
                if width > height * 1.5:
                    # Estimate based on image width
                    if width > 800:
                        wheel_count = 6  # Truck
                    else:
                        wheel_count = 4  # Car
                else:
                    wheel_count = 4  # Default to car
                
                return {
                    "success": True,
                    "wheel_count": wheel_count,
                    "confidence": 0.5,
                    "method": "estimation"
                }
            
            # Filter and count circles
            circles = np.round(circles[0, :]).astype(int)
            
            # Filter circles that might be wheels
            # (based on position, size similarity)
            valid_circles = []
            height, width = frame.shape[:2]
            
            for (x, y, r) in circles:
                # Wheels typically in bottom half of image
                if y > height * 0.4:
                    valid_circles.append((x, y, r))
            
            wheel_count = len(valid_circles)
            
            # Estimate axle count (pairs of wheels)
            axle_count = max(1, wheel_count // 2)
            
            # Calculate confidence based on detection quality
            confidence = min(1.0, len(valid_circles) / 4.0)
            
            return {
                "success": True,
                "wheel_count": wheel_count if wheel_count > 0 else 4,
                "axle_count": axle_count,
                "confidence": float(confidence),
                "method": "detection"
            }
            
        except Exception as e:
            return {
                "success": False,
                "wheel_count": None,
                "error": f"Wheel detection failed: {str(e)}"
            }
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return function metadata"""
        return {
            "id": self.FUNCTION_ID,
            "name": self.FUNCTION_NAME,
            "description": self.DESCRIPTION,
            "input_source": self.INPUT_SOURCE,
            "parallel_group": self.PARALLEL_GROUP
        }


# Backward compatibility alias
def count_wheels(frame: np.ndarray) -> Dict[str, Any]:
    """Legacy function interface"""
    detector = WheelDetectionFunction()
    return detector.detect(frame)
