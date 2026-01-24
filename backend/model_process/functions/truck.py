from typing import Dict, Any, Optional
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TruckDetector:
    def __init__(self, confidence: float = 0.5):
        self.confidence = confidence
        self.model = None
        self.class_names = None
        
    def _load_model(self):
        if self.model is not None:
            return

        try:
            from ultralytics import YOLO
            # Configurable model path?
            # Using standard yolov8n.pt for now
            self.model = YOLO('yolov8n.pt')
            self.class_names = self.model.names
        except ImportError:
            logger.error("Ultralytics not installed. Truck detection unavailable.")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect trucks/cars in frame.
        Returns: {
            "detected": bool,
            "bbox": [x1, y1, x2, y2],
            "confidence": float,
            "class": str
        }
        """
        self._load_model()
        if self.model is None:
            return {"detected": False, "error": "Model not loaded"}

        try:
            # Inference
            results = self.model(frame, verbose=False, conf=self.confidence)
            
            if not results or len(results[0].boxes) == 0:
                return {"detected": False}

            # Filter for Truck/Car
            # COCO: 2=car, 5=bus, 7=truck
            target_classes = [2, 5, 7]
            
            best_det = None
            max_conf = -1
            
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                if cls_id in target_classes:
                    conf = float(box.conf[0])
                    if conf > max_conf:
                        max_conf = conf
                        best_det = {
                            "bbox": box.xyxy[0].cpu().numpy().astype(int).tolist(),
                            "confidence": conf,
                            "class": self.class_names[cls_id],
                            "class_id": cls_id
                        }
            
            if best_det:
                return {"detected": True, **best_det}
            
            return {"detected": False}

        except Exception as e:
            logger.error(f"Truck detection error: {e}")
            return {"detected": False, "error": str(e)}
