"""Car Detection Module - YOLO11n for real-time vehicle detection (all angles)"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

# Model is stored in project root: models/car_detect/
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "car_detect"
PYTORCH_MODEL_PATH = MODEL_DIR / "yolo11n.pt"

def setup_model():
    """Download YOLO11n model"""
    from ultralytics import YOLO
    import shutil
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO("yolo11n.pt")
    if Path("yolo11n.pt").exists():
        shutil.move("yolo11n.pt", PYTORCH_MODEL_PATH)
    elif not PYTORCH_MODEL_PATH.exists():
        model.save(str(PYTORCH_MODEL_PATH))
    print(f"[Setup] Model saved to: {PYTORCH_MODEL_PATH}")

class CarDetector:
    # COCO vehicle classes - expanded for better detection from all angles
    VEHICLE_CLASSES = {
        2: "car",
        3: "motorcycle", 
        5: "bus",
        7: "truck"
    }
    
    def __init__(self, model_path: Optional[str] = None, confidence: float = 0.3, max_detections: int = 1, detect_trucks: bool = True):
        """
        Args:
            confidence: Lower threshold (0.3) to detect vehicles from front/back angles
            detect_trucks: If True, detect cars, trucks, and buses
        """
        from ultralytics import YOLO
        if model_path:
            self.model_path = Path(model_path)
        elif PYTORCH_MODEL_PATH.exists():
            self.model_path = PYTORCH_MODEL_PATH
        else:
            self.model_path = "yolo11n.pt"
        self.model = YOLO(str(self.model_path))
        self.confidence = confidence
        self.max_detections = max_detections
        # Include bus (5) for better detection of large vehicles from front view
        self.classes = [2, 5, 7] if detect_trucks else [2]
    
    def detect(self, frame: np.ndarray, enhance: bool = True) -> Dict[str, Any]:
        """
        Detect vehicles in frame. Works for front, back, and side views.
        
        Args:
            frame: BGR image
            enhance: If True, apply preprocessing for better front-face detection
        """
        # Preprocess frame for better detection
        if enhance:
            processed = self._preprocess(frame)
        else:
            processed = frame
        
        # Run detection with lower IOU threshold for overlapping boxes
        results = self.model(
            processed, 
            stream=False, 
            classes=self.classes, 
            max_det=self.max_detections, 
            conf=self.confidence,
            iou=0.5,  # Allow some overlap
            verbose=False
        )
        result = results[0]
        
        if len(result.boxes) == 0:
            # Try again with augmented image if no detection
            if enhance:
                return self._detect_with_augmentation(frame)
            return {"detected": False, "bbox": None, "confidence": 0.0, "class_name": None, "class_id": None, "annotated_frame": frame}
        
        box = result.boxes[0]
        bbox = box.xyxy[0].cpu().numpy().astype(int).tolist()
        confidence = float(box.conf[0].cpu().numpy())
        class_id = int(box.cls[0].cpu().numpy())
        
        # Use original frame for annotation (not preprocessed)
        annotated = frame.copy()
        x1, y1, x2, y2 = bbox
        color = (34, 197, 94)  # Green
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
        label = f"{self.VEHICLE_CLASSES.get(class_id, 'vehicle').upper()} {confidence*100:.0f}%"
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(annotated, (x1, y1 - 30), (x1 + w + 10, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return {
            "detected": True, 
            "bbox": bbox, 
            "confidence": confidence, 
            "class_name": self.VEHICLE_CLASSES.get(class_id, "vehicle"),
            "class_id": class_id, 
            "annotated_frame": annotated
        }
    
    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Enhance frame for better vehicle detection"""
        # Increase contrast slightly
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    def _detect_with_augmentation(self, frame: np.ndarray) -> Dict[str, Any]:
        """Try detection with slight brightness/contrast augmentation"""
        # Try with increased brightness
        bright = cv2.convertScaleAbs(frame, alpha=1.2, beta=20)
        results = self.model(bright, stream=False, classes=self.classes, max_det=self.max_detections, conf=self.confidence * 0.8, verbose=False)
        
        if len(results[0].boxes) > 0:
            box = results[0].boxes[0]
            bbox = box.xyxy[0].cpu().numpy().astype(int).tolist()
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())
            
            annotated = frame.copy()
            x1, y1, x2, y2 = bbox
            color = (34, 197, 94)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            label = f"{self.VEHICLE_CLASSES.get(class_id, 'vehicle').upper()} {confidence*100:.0f}%"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated, (x1, y1 - 30), (x1 + w + 10, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            return {"detected": True, "bbox": bbox, "confidence": confidence, 
                    "class_name": self.VEHICLE_CLASSES.get(class_id, "vehicle"), "class_id": class_id, "annotated_frame": annotated}
        
        return {"detected": False, "bbox": None, "confidence": 0.0, "class_name": None, "class_id": None, "annotated_frame": frame}
    
    def detect_and_crop(self, frame: np.ndarray, padding: int = 10) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        detection = self.detect(frame)
        if not detection["detected"]: return None, detection
        x1, y1, x2, y2 = detection["bbox"]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1 - padding), max(0, y1 - padding)
        x2, y2 = min(w, x2 + padding), min(h, y2 + padding)
        return frame[y1:y2, x1:x2], detection

class StreamCarDetector:
    def __init__(self, capture_dir: str = "database/saved_image", confidence: float = 0.3, cooldown_seconds: float = 5.0):
        self.detector = CarDetector(confidence=confidence, detect_trucks=True)
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.cooldown_seconds = cooldown_seconds
        self.last_capture_time = None
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        detection = self.detector.detect(frame)
        result = {**detection, "captured": False, "capture_path": None}
        if detection["detected"]:
            now = datetime.now()
            should_capture = True
            if self.last_capture_time:
                if (now - self.last_capture_time).total_seconds() < self.cooldown_seconds:
                    should_capture = False
            if should_capture:
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                filepath = self.capture_dir / f"car_capture_{timestamp}.jpg"
                cv2.imwrite(str(filepath), frame)
                result["captured"] = True
                result["capture_path"] = str(filepath)
                self.last_capture_time = now
        return result

def test_with_video(video_source: str = "0"):
    detector = CarDetector(confidence=0.3)
    cap = cv2.VideoCapture(0 if video_source == "0" else video_source)
    if not cap.isOpened(): return
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        result = detector.detect(frame)
        cv2.imshow("Detection", result["annotated_frame"])
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup": setup_model()
        elif sys.argv[1] == "test": test_with_video(sys.argv[2] if len(sys.argv) > 2 else "0")
