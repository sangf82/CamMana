"""
Detection Service - Orchestrates car detection with IoU-based deduplication

Migrated to backend/car_process/core/
Updated to use new function modules.
"""
import cv2
import json
import time
import threading
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

# Updated imports - use new car_process modules
from backend.car_process.functions import (
    CarDetectionFunction,
    detect_plate,
    detect_colors,
    count_wheels
)
import backend.data_process as storage

IOU_THRESHOLD = 0.70
AUTO_DETECTION_INTERVAL = 0.5
MAX_VIDEO_DURATION = 5.0
CAPTURE_DIR = Path("database/car_history")

@dataclass
class DetectionState:
    last_bbox: Optional[list] = None
    last_detection_time: float = 0.0
    is_auto_running: bool = False
    auto_thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    video_writer: Optional[cv2.VideoWriter] = None
    video_start_time: float = 0.0
    current_capture_dir: Optional[Path] = None

class DetectionService:
    def __init__(self):
        # Use new CarDetectionFunction
        self.detector = CarDetectionFunction(confidence=0.3, detect_trucks=True)
        self.states: Dict[str, DetectionState] = {}
        self._streamers: Dict[str, Any] = {}
        self._camera_tags: Dict[str, str] = {}
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    
    def register_camera(self, camera_id: str, streamer: Any, tag: Optional[str] = None):
        self._streamers[camera_id] = streamer
        if tag: self._camera_tags[camera_id] = tag
        if camera_id not in self.states: self.states[camera_id] = DetectionState()
    
    def unregister_camera(self, camera_id: str):
        self.stop_auto_detection(camera_id)
        self._streamers.pop(camera_id, None)
        self._camera_tags.pop(camera_id, None)
        self.states.pop(camera_id, None)
    
    def set_camera_tag(self, camera_id: str, tag: str):
        if tag not in ('front_cam', 'side_cam', None):
            raise ValueError(f"Invalid tag: {tag}")
        self._camera_tags[camera_id] = tag
    
    def get_paired_camera(self, camera_id: str) -> Optional[str]:
        current_tag = self._camera_tags.get(camera_id)
        if not current_tag: return None
        target_tag = 'side_cam' if current_tag == 'front_cam' else 'front_cam'
        for cid, tag in self._camera_tags.items():
            if tag == target_tag and cid != camera_id: return cid
        return None
    
    def detect(self, camera_id: str) -> Dict[str, Any]:
        # Only allow detection on front_cam tagged cameras
        camera_tag = self._camera_tags.get(camera_id)
        if camera_tag != 'front_cam':
            return {"success": False, "error": "Detection only works on front_cam tagged cameras"}
        
        streamer = self._streamers.get(camera_id)
        if not streamer or not streamer.is_streaming:
            return {"success": False, "error": "Camera not streaming"}
        frame = streamer.last_frame
        if frame is None:
            return {"success": False, "error": "No frame available"}
        try:
            result = self.detector.detect(frame)
            h, w = frame.shape[:2]
            return {"success": True, "detected": result["detected"], "bbox": result["bbox"],
                    "confidence": result["confidence"], "class_name": result["class_name"],
                    "class_id": result["class_id"], "frame_width": w, "frame_height": h}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def capture_with_detection(self, front_cam_id: str, force: bool = False) -> Dict[str, Any]:
        # Only allow detection on front_cam tagged cameras
        camera_tag = self._camera_tags.get(front_cam_id)
        if camera_tag != 'front_cam':
            return {"success": False, "error": "Detection only works on front_cam tagged cameras"}
        
        streamer = self._streamers.get(front_cam_id)
        if not streamer or not streamer.is_streaming:
            return {"success": False, "error": "Camera not streaming"}
        
        # Use high-resolution frame for capture (better for plate reading)
        frame = streamer.get_capture_frame() if hasattr(streamer, 'get_capture_frame') else streamer.last_frame
        if frame is None:
            frame = streamer.last_frame
        if frame is None:
            return {"success": False, "error": "No frame available"}
        
        try:
            result = self.detector.detect(frame)
            if not result["detected"] or not result["bbox"]:
                return {"success": False, "skipped": True, "reason": "No vehicle detected"}
            
            current_bbox = result["bbox"]
            current_time = time.time()
            state = self.states.get(front_cam_id, DetectionState())
            
            # IoU check
            if not force and state.last_bbox:
                iou = self._calculate_iou(current_bbox, state.last_bbox)
                time_diff = current_time - state.last_detection_time
                if iou > IOU_THRESHOLD and time_diff < 30:
                    storage.log_detection_event(front_cam_id, 'skipped_iou', {'iou': round(iou, 3), 'time_diff': round(time_diff, 1)})
                    return {"success": False, "skipped": True, "reason": f"Same car (IoU: {iou:.2f})", "detected": True, "bbox": current_bbox}
            
            state.last_bbox = current_bbox
            state.last_detection_time = current_time
            self.states[front_cam_id] = state
            
            # Create capture folder
            timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            capture_folder = CAPTURE_DIR / f"car_at_{timestamp}"
            capture_folder.mkdir(parents=True, exist_ok=True)
            
            # Save front image with bbox
            enhanced_front = self._enhance_image(frame)
            x1, y1, x2, y2 = current_bbox
            cv2.rectangle(enhanced_front, (x1, y1), (x2, y2), (34, 197, 94), 3)
            label = f"{result['class_name'].upper()} {result['confidence']*100:.0f}%"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(enhanced_front, (x1, y1 - 25), (x1 + w + 10, y1), (34, 197, 94), -1)
            cv2.putText(enhanced_front, label, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            front_path = capture_folder / "front.jpg"
            cv2.imwrite(str(front_path), enhanced_front)
            
            # Prepare side camera frame (high-res for better analysis)
            side_cam_id = self.get_paired_camera(front_cam_id)
            side_frame = None
            side_path = None
            
            if side_cam_id:
                side_streamer = self._streamers.get(side_cam_id)
                if side_streamer and side_streamer.is_streaming:
                    # Use high-res capture if available
                    side_frame = side_streamer.get_capture_frame() if hasattr(side_streamer, 'get_capture_frame') else side_streamer.last_frame
                    if side_frame is None:
                        side_frame = side_streamer.last_frame
                    if side_frame is not None:
                        side_frame = side_frame.copy()
                        enhanced_side = self._enhance_image(side_frame)
                        side_path = capture_folder / "side.jpg"
                        cv2.imwrite(str(side_path), enhanced_side)
            
            # Run detections in PARALLEL - plate from front, color/wheels from side
            plate_result = {"success": False, "plates": []}
            color_result = {"success": False, "primary_color": None}
            wheel_result = {"success": False, "wheel_count": None}
            
            def detect_plate_task():
                return detect_plate(frame)
            
            def detect_side_task():
                if side_frame is not None:
                    return {
                        "color": detect_colors(side_frame),
                        "wheel": count_wheels(side_frame)
                    }
                return {"color": {"success": False, "primary_color": None}, "wheel": {"success": False, "wheel_count": None}}
            
            # Execute both detections in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                plate_future = executor.submit(detect_plate_task)
                side_future = executor.submit(detect_side_task)
                
                # Get results (non-blocking, runs in parallel)
                try:
                    plate_result = plate_future.result(timeout=10)
                except Exception as e:
                    plate_result = {"success": False, "plates": [], "error": str(e)}
                
                try:
                    side_results = side_future.result(timeout=10)
                    color_result = side_results["color"]
                    wheel_result = side_results["wheel"]
                except Exception as e:
                    color_result = {"success": False, "primary_color": None, "error": str(e)}
                    wheel_result = {"success": False, "wheel_count": None, "error": str(e)}
            
            plate_number = plate_result.get("plates", [None])[0] if plate_result.get("success") else None
            
            with open(capture_folder / "plate.json", 'w') as f: json.dump(plate_result, f, indent=2)
            with open(capture_folder / "color.json", 'w') as f: json.dump(color_result, f, indent=2)
            with open(capture_folder / "wheel.json", 'w') as f: json.dump(wheel_result, f, indent=2)
            
            # Save to DB
            detection_data = {
                'folder_path': str(capture_folder), 'timestamp': timestamp, 'plate_number': plate_number,
                'primary_color': color_result.get("primary_color"), 'wheel_count': wheel_result.get("wheel_count"),
                'front_cam_id': front_cam_id, 'side_cam_id': side_cam_id, 'confidence': result["confidence"],
                'bbox': current_bbox, 'class_name': result["class_name"]
            }
            record_id = storage.save_captured_car(detection_data)
            storage.log_detection_event(front_cam_id, 'captured', {'record_id': record_id, 'plate': plate_number})
            
            return {
                "success": True, "record_id": record_id, "folder_path": str(capture_folder), "timestamp": timestamp,
                "detected": True, "class_name": result["class_name"], "confidence": result["confidence"],
                "bbox": current_bbox, "plate": plate_number, "color": color_result.get("primary_color"),
                "wheel_count": wheel_result.get("wheel_count"),
                "files": {"front": str(front_path), "side": str(side_path) if side_path else None,
                          "plate_json": str(capture_folder / "plate.json"), "color_json": str(capture_folder / "color.json"),
                          "wheel_json": str(capture_folder / "wheel.json")}
            }
        except Exception as e:
            storage.log_detection_event(front_cam_id, 'error', {'error': str(e)})
            return {"success": False, "error": str(e)}
    
    def start_auto_detection(self, camera_id: str, callback: Optional[Callable] = None):
        state = self.states.get(camera_id)
        if not state:
            state = DetectionState()
            self.states[camera_id] = state
        if state.is_auto_running:
            return {"success": False, "error": "Auto detection already running"}
        
        state.stop_event.clear()
        state.is_auto_running = True
        
        def detection_loop():
            while not state.stop_event.is_set():
                try:
                    result = self.capture_with_detection(camera_id)
                    if callback: callback(result)
                except Exception as e:
                    print(f"[Detection] Error: {e}")
                state.stop_event.wait(AUTO_DETECTION_INTERVAL)
            state.is_auto_running = False
        
        state.auto_thread = threading.Thread(target=detection_loop, daemon=True)
        state.auto_thread.start()
        return {"success": True, "message": "Auto detection started"}
    
    def stop_auto_detection(self, camera_id: str):
        state = self.states.get(camera_id)
        if state and state.is_auto_running:
            state.stop_event.set()
            if state.auto_thread: state.auto_thread.join(timeout=2)
            state.is_auto_running = False
        return {"success": True, "message": "Auto detection stopped"}
    
    def is_auto_detection_running(self, camera_id: str) -> bool:
        state = self.states.get(camera_id)
        return state.is_auto_running if state else False
    
    def start_video_recording(self, camera_id: str, output_path: Path):
        streamer = self._streamers.get(camera_id)
        if not streamer or not streamer.is_streaming: return False
        state = self.states.get(camera_id, DetectionState())
        frame = streamer.last_frame
        if frame is None: return False
        
        h, w = frame.shape[:2]
        state.video_writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), 15.0, (w, h))
        state.video_start_time = time.time()
        state.current_capture_dir = output_path.parent
        self.states[camera_id] = state
        
        def record_loop():
            while state.video_writer and (time.time() - state.video_start_time) < MAX_VIDEO_DURATION:
                if streamer.last_frame is not None: state.video_writer.write(streamer.last_frame)
                time.sleep(1/15)
            self.stop_video_recording(camera_id)
        
        threading.Thread(target=record_loop, daemon=True).start()
        return True
    
    def stop_video_recording(self, camera_id: str):
        state = self.states.get(camera_id)
        if state and state.video_writer:
            state.video_writer.release()
            state.video_writer = None
    
    def _calculate_iou(self, box1: list, box2: list) -> float:
        x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
        x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0
    
    def _enhance_image(self, image: np.ndarray) -> np.ndarray:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(image, -1, kernel)

# Singleton instance
_detection_service: Optional[DetectionService] = None

def get_detection_service() -> DetectionService:
    global _detection_service
    if _detection_service is None:
        _detection_service = DetectionService()
    return _detection_service

__all__ = ['DetectionService', 'get_detection_service', 'DetectionState']
