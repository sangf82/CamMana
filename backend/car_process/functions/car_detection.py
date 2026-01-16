"""
Vehicle Detection Function

Uses YOLO to detect cars, trucks, and buses in video frames.
Migrated from backend/detect_car/car_detect.py
"""

from typing import Dict, Any, Optional
import cv2
import numpy as np
from pathlib import Path

class CarDetectionFunction:
    """YOLO-based vehicle detection"""
    
    # Function Metadata
    FUNCTION_ID = "car_detect"
    FUNCTION_NAME = "Nhận diện xe (Real-time)"
    DESCRIPTION = "Phát hiện phương tiện từ luồng video trực tiếp"
    INPUT_SOURCE = "front_cam"
    PARALLEL_GROUP = 1  # Must run first
    
    def __init__(self, confidence: float = 0.3, detect_trucks: bool = True):
        """
        Initialize car detector.
        
        Args:
            confidence: Minimum confidence threshold (0.0-1.0)
            detect_trucks: Whether to detect trucks in addition to cars
        """
        self.confidence = confidence
        self.detect_trucks = detect_trucks
        self._model = None  # Lazy load
        self._class_names = None
    
    def _load_model(self):
        """Lazy load YOLO model"""
        if self._model is not None:
            return
        
        try:
            # Try to import ultralytics YOLO
            from ultralytics import YOLO
            model_path = Path(__file__).parent.parent.parent / "models" / "yolov8n.pt"
            
            if not model_path.exists():
                # Use default pretrained model
                self._model = YOLO('yolov8n.pt')
            else:
                self._model = YOLO(str(model_path))
            
            # COCO class names
            self._class_names = self._model.names
            
        except ImportError:
            # Fallback: use OpenCV DNN with pre-trained model
            print("[CarDetection] Ultralytics not available, using OpenCV DNN fallback")
            self._model = None
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect vehicles in a frame.
        
        Args:
            frame: Input image (numpy array, RGB or BGR)
            
        Returns:
            {
                "success": bool,
                "detected": bool,
                "bbox": [x1, y1, x2, y2] or None,
                "confidence": float or None,
                "class_name": str or None,  # "car", "truck", "bus"
                "class_id": int or None
            }
        """
        self._load_model()
        
        if self._model is None:
            return {
                "success": False,
                "detected": False,
                "error": "Model not loaded"
            }
        
        try:
            # Run inference
            results = self._model(frame, verbose=False, conf=self.confidence)
            
            if len(results) == 0 or len(results[0].boxes) == 0:
                return {
                    "success": True,
                    "detected": False,
                    "bbox": None,
                    "confidence": None,
                    "class_name": None,
                    "class_id": None
                }
            
            # Get first detection (highest confidence)
            boxes = results[0].boxes
            
            # Filter by vehicle classes (car=2, truck=7, bus=5 in COCO)
            vehicle_classes = [2, 5, 7] if self.detect_trucks else [2]
            
            vehicle_detections = []
            for i, box in enumerate(boxes):
                class_id = int(box.cls[0])
                if class_id in vehicle_classes:
                    vehicle_detections.append({
                        "bbox": box.xyxy[0].cpu().numpy().astype(int).tolist(),
                        "confidence": float(box.conf[0]),
                        "class_id": class_id,
                        "class_name": self._class_names[class_id]
                    })
            
            if not vehicle_detections:
                return {
                    "success": True,
                    "detected": False,
                    "bbox": None,
                    "confidence": None,
                    "class_name": None,
                    "class_id": None
                }
            
            # Return highest confidence detection
            best_detection = max(vehicle_detections, key=lambda d: d["confidence"])
            
            return {
                "success": True,
                "detected": True,
                "bbox": best_detection["bbox"],
                "confidence": best_detection["confidence"],
                "class_name": best_detection["class_name"],
                "class_id": best_detection["class_id"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "detected": False,
                "error": f"Detection failed: {str(e)}"
            }
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return function metadata for configuration"""
        return {
            "id": self.FUNCTION_ID,
            "name": self.FUNCTION_NAME,
            "description": self.DESCRIPTION,
            "input_source": self.INPUT_SOURCE,
            "parallel_group": self.PARALLEL_GROUP
        }


# Backward compatibility alias
CarDetector = CarDetectionFunction
