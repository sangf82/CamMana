"""
YOLO Truck/Car Detector using ONNX Runtime

This is a lightweight implementation that doesn't require PyTorch.
Uses ONNX Runtime for inference (~50MB vs ~2GB for PyTorch).
"""

from typing import Dict, Any, Optional, List
import numpy as np
import logging
from pathlib import Path
import cv2

from backend.settings import settings

logger = logging.getLogger(__name__)

# COCO class names for vehicle detection
COCO_CLASSES = {
    2: "car",
    5: "bus",
    7: "truck"
}
TARGET_CLASSES = list(COCO_CLASSES.keys())


class TruckDetector:
    """YOLO-based vehicle detector using ONNX Runtime"""
    
    def __init__(self, confidence: float = 0.25):
        self.confidence = confidence
        self.session = None
        self.input_name = None
        self.input_shape = None
        
    def _load_model(self) -> bool:
        """Load ONNX model lazily"""
        if self.session is not None:
            return True

        try:
            import onnxruntime as ort
            
            # Try to find ONNX model
            model_path = settings.models_dir / "car_detect" / "yolo11n.onnx"
            
            # If ONNX doesn't exist, try to convert from .pt
            if not model_path.exists():
                pt_path = settings.models_dir / "car_detect" / "yolo11n.pt"
                if pt_path.exists():
                    logger.warning(f"ONNX model not found. Please export: python -c \"from ultralytics import YOLO; YOLO('{pt_path}').export(format='onnx')\"")
                    return False
                else:
                    logger.error("No YOLO model found. Download yolo11n.onnx to models/car_detect/")
                    return False
            
            # Create ONNX Runtime session
            providers = ['CPUExecutionProvider']
            # Try GPU if available
            if ort.get_device() == 'GPU':
                providers.insert(0, 'CUDAExecutionProvider')
            
            self.session = ort.InferenceSession(str(model_path), providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape  # [1, 3, H, W]
            
            logger.info(f"Loaded ONNX model: {model_path.name}")
            return True
            
        except ImportError:
            logger.error("onnxruntime not installed. Run: uv add onnxruntime")
            return False
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            return False

    def _preprocess(self, frame: np.ndarray) -> tuple[np.ndarray, float, float]:
        """Preprocess frame for YOLO inference"""
        # Get target size from model (usually 640x640)
        # Handle dynamic dimensions (could be None, string, or int)
        def get_dim(val, default=640):
            if isinstance(val, int) and val > 0:
                return val
            return default
        
        target_h = get_dim(self.input_shape[2] if len(self.input_shape) > 2 else None, 640)
        target_w = get_dim(self.input_shape[3] if len(self.input_shape) > 3 else None, 640)
        
        h, w = frame.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        # Resize
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Pad to target size
        pad_w = (target_w - new_w) // 2
        pad_h = (target_h - new_h) // 2
        padded = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h+new_h, pad_w:pad_w+new_w] = resized
        
        # Convert to float and normalize
        blob = padded.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)  # HWC -> CHW
        blob = np.expand_dims(blob, 0)  # Add batch dimension
        
        return blob, scale, (pad_w, pad_h)

    def _postprocess(self, outputs: np.ndarray, scale: float, pad: tuple, orig_shape: tuple) -> List[Dict]:
        """Process YOLO output to get detections"""
        # YOLO output shape: [1, 84, 8400] for YOLOv8/11
        # 84 = 4 (bbox) + 80 (classes)
        # Need to transpose to [8400, 84]
        output = outputs[0]  # Remove batch: [84, 8400]
        predictions = output.T  # Transpose: [8400, 84]
        
        detections = []
        
        for pred in predictions:
            # Get class scores (skip first 4 bbox values)
            class_scores = pred[4:]
            class_id = np.argmax(class_scores)
            confidence = class_scores[class_id]
            
            # Filter by confidence and target classes
            if confidence < self.confidence or class_id not in TARGET_CLASSES:
                continue
            
            # Get bbox (center format)
            cx, cy, w, h = pred[:4]
            
            # Convert to corner format
            x1 = cx - w / 2
            y1 = cy - h / 2
            x2 = cx + w / 2
            y2 = cy + h / 2
            
            # Remove padding and scale back to original size
            pad_w, pad_h = pad
            x1 = (x1 - pad_w) / scale
            y1 = (y1 - pad_h) / scale
            x2 = (x2 - pad_w) / scale
            y2 = (y2 - pad_h) / scale
            
            # Clip to image bounds
            orig_h, orig_w = orig_shape[:2]
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))
            
            detections.append({
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "confidence": float(confidence),
                "class": COCO_CLASSES[class_id],
                "class_id": int(class_id)
            })
        
        # NMS - keep only best detection
        if detections:
            detections.sort(key=lambda x: x["confidence"], reverse=True)
            return [detections[0]]  # Return best only
        
        return []

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
        if not self._load_model():
            return {"detected": False, "error": "Model not loaded"}

        try:
            # Preprocess
            blob, scale, pad = self._preprocess(frame)
            
            # Inference
            outputs = self.session.run(None, {self.input_name: blob})
            
            # Postprocess
            detections = self._postprocess(outputs[0], scale, pad, frame.shape)
            
            if detections:
                best = detections[0]
                return {"detected": True, **best}
            
            return {"detected": False}

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return {"detected": False, "error": str(e)}


# Singleton instance
_detector: Optional[TruckDetector] = None

def get_detector(confidence: float = 0.25) -> TruckDetector:
    """Get or create singleton detector instance"""
    global _detector
    if _detector is None:
        _detector = TruckDetector(confidence)
    return _detector
