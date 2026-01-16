"""
Vehicle Color Detection Function

Analyzes the dominant color of a vehicle from an image.
Migrated from backend/detect_car/info_detect.py
"""

from typing import Dict, Any
import numpy as np
import cv2

class ColorDetectionFunction:
    """Vehicle color detection using K-means clustering"""
    
    # Function Metadata
    FUNCTION_ID = "color_detect"
    FUNCTION_NAME = "Nhận diện màu xe"
    DESCRIPTION = "Phân tích màu sắc chủ đạo của phương tiện"
    INPUT_SOURCE = "side_cam"  # Side view better for color
    PARALLEL_GROUP = 2  # Can run in parallel with plate/wheel
    
    # Color definitions (BGR format)
    COLOR_RANGES = {
        'white': ([200, 200, 200], [255, 255, 255]),
        'black': ([0, 0, 0], [50, 50, 50]),
        'gray': ([51, 51, 51], [199, 199, 199]),
        'red': ([0, 0, 100], [80, 80, 255]),
        'blue': ([100, 0, 0], [255, 80, 80]),
        'green': ([0, 100, 0], [80, 255, 80]),
        'yellow': ([0, 200, 200], [80, 255, 255]),
        'brown': ([0, 50, 100], [80, 150, 200]),
        'silver': ([150, 150, 150], [220, 220, 220])
    }
    
    def __init__(self):
        """Initialize color detector"""
        pass
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect primary color of vehicle in frame.
        
        Args:
            frame: Input image (numpy array, BGR format)
            
        Returns:
            {
                "success": bool,
                "primary_color": str,  # e.g., "white", "black"
                "confidence": float,
                "color_distribution": Dict[str, float]  # Optional
            }
        """
        try:
            # Resize for faster processing
            small = cv2.resize(frame, (frame.shape[1] // 4, frame.shape[0] // 4))
            
            # Convert to RGB for color analysis
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            
            # Flatten image to list of pixels
            pixels = rgb.reshape(-1, 3).astype(np.float32)
            
            # Use K-means to find dominant colors
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
            k = 3  # Find top 3 colors
            
            _, labels, centers = cv2.kmeans(
                pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
            )
            
            # Count pixels per cluster
            unique, counts = np.unique(labels, return_counts=True)
            
            # Get dominant color (most pixels)
            dominant_idx = np.argmax(counts)
            dominant_color_bgr = centers[dominant_idx].astype(int)
            
            # Convert back to BGR for color matching
            dominant_color_rgb = dominant_color_bgr[[2, 1, 0]]  # RGB to BGR
            
            # Match to predefined colors
            matched_color = self._match_color(dominant_color_rgb)
            
            # Calculate confidence based on cluster dominance
            confidence = counts[dominant_idx] / np.sum(counts)
            
            return {
                "success": True,
                "primary_color": matched_color,
                "confidence": float(confidence),
                "rgb_value": dominant_color_rgb.tolist()
            }
            
        except Exception as e:
            return {
                "success": False,
                "primary_color": None,
                "error": f"Color detection failed: {str(e)}"
            }
    
    def _match_color(self, bgr_color: np.ndarray) -> str:
        """Match BGR color to predefined color name"""
        min_distance = float('inf')
        matched_name = 'unknown'
        
        for color_name, (lower, upper) in self.COLOR_RANGES.items():
            lower = np.array(lower)
            upper = np.array(upper)
            
            # Check if color is within range
            if np.all(bgr_color >= lower) and np.all(bgr_color <= upper):
                # Calculate distance to center of range
                center = (lower + upper) / 2
                distance = np.linalg.norm(bgr_color - center)
                
                if distance < min_distance:
                    min_distance = distance
                    matched_name = color_name
        
        # If no match, use simple heuristic
        if matched_name == 'unknown':
            if np.mean(bgr_color) < 50:
                matched_name = 'black'
            elif np.mean(bgr_color) > 200:
                matched_name = 'white'
            elif np.std(bgr_color) < 20:
                matched_name = 'gray'
            else:
                # Check which channel is dominant
                if bgr_color[2] > bgr_color[1] and bgr_color[2] > bgr_color[0]:
                    matched_name = 'red'
                elif bgr_color[0] > bgr_color[1] and bgr_color[0] > bgr_color[2]:
                    matched_name = 'blue'
                elif bgr_color[1] > bgr_color[0] and bgr_color[1] > bgr_color[2]:
                    matched_name = 'green'
        
        return matched_name
    
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
def detect_colors(frame: np.ndarray) -> Dict[str, Any]:
    """Legacy function interface"""
    detector = ColorDetectionFunction()
    return detector.detect(frame)
