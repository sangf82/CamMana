# Car Detection Package
from backend.detect_car.car_detect import CarDetector, StreamCarDetector
from backend.detect_car.detection_service import DetectionService, get_detection_service
from backend.detect_car.info_detect import detect_plate, detect_colors, count_wheels, analyze_vehicle, CameraMode

__all__ = ['CarDetector', 'StreamCarDetector', 'DetectionService', 'get_detection_service', 
           'detect_plate', 'detect_colors', 'count_wheels', 'analyze_vehicle', 'CameraMode']
