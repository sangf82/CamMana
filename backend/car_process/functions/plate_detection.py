"""
License Plate Detection Function

Uses OCR to extract license plate numbers from vehicle images.
Migrated from backend/detect_car/info_detect.py
"""

from typing import Dict, Any, List
import numpy as np
import cv2

class PlateDetectionFunction:
    """License plate recognition using PaddleOCR"""
    
    # Function Metadata
    FUNCTION_ID = "plate_detect"
    FUNCTION_NAME = "Nhận diện biển số"
    DESCRIPTION = "Tự động trích xuất biển số xe từ hình ảnh"
    INPUT_SOURCE = "front_cam"
    PARALLEL_GROUP = 2  # Can run in parallel with color/wheel
    
    def __init__(self):
        """Initialize plate detector"""
        self._ocr = None  # Lazy load
    
    def _load_ocr(self):
        """Lazy load PaddleOCR"""
        if self._ocr is not None:
            return
        
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                show_log=False,
                use_gpu=False
            )
        except ImportError:
            print("[PlateDetection] PaddleOCR not available")
            self._ocr = None
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect license plate in a frame.
        
        Args:
            frame: Input image (numpy array)
            
        Returns:
            {
                "success": bool,
                "plates": List[str],  # e.g., ["29A-12345"]
                "confidence": float,
                "positions": List[bbox]  # Optional bounding boxes
            }
        """
        self._load_ocr()
        
        if self._ocr is None:
            return {
                "success": False,
                "plates": [],
                "error": "OCR not available"
            }
        
        try:
            # Preprocess image for better OCR
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Run OCR
            result = self._ocr.ocr(enhanced, cls=True)
            
            if not result or not result[0]:
                return {
                    "success": True,
                    "plates": [],
                    "confidence": 0.0
                }
            
            # Extract plate-like text patterns
            plates = []
            confidences = []
            positions = []
            
            for line in result[0]:
                text = line[1][0]  # Detected text
                conf = line[1][1]  # Confidence
                bbox = line[0]     # Bounding box
                
                # Filter for plate-like patterns
                # Vietnamese plates: 29A-12345, 30G-123.45, etc.
                cleaned = text.replace(' ', '').replace('-', '').replace('.', '')
                
                # Simple validation: contains both letters and numbers
                has_letter = any(c.isalpha() for c in cleaned)
                has_number = any(c.isdigit() for c in cleaned)
                
                if has_letter and has_number and len(cleaned) >= 6:
                    plates.append(text)
                    confidences.append(conf)
                    positions.append(bbox)
            
            if plates:
                return {
                    "success": True,
                    "plates": plates,
                    "confidence": max(confidences),
                    "positions": positions
                }
            else:
                return {
                    "success": True,
                    "plates": [],
                    "confidence": 0.0
                }
            
        except Exception as e:
            return {
                "success": False,
                "plates": [],
                "error": f"Plate detection failed: {str(e)}"
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
def detect_plate(frame: np.ndarray) -> Dict[str, Any]:
    """Legacy function interface"""
    detector = PlateDetectionFunction()
    return detector.detect(frame)
