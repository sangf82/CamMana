"""Vehicle Information Detection - External API calls for ALPR, Color, Wheel detection"""
import requests
import cv2
import numpy as np
from typing import Dict, Any
from io import BytesIO

API_BASE_URL = "https://thpttl12t1--truck-api-fastapi-app.modal.run"

def detect_plate(image: np.ndarray) -> Dict[str, Any]:
    try:
        _, buffer = cv2.imencode('.jpg', image)
        response = requests.post(f"{API_BASE_URL}/alpr", files={"file": ("image.jpg", BytesIO(buffer.tobytes()), "image/jpeg")}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "plates": data.get("plates", []), "count": data.get("count", 0), "raw_results": data.get("raw_results", "")}
        return {"success": False, "plates": [], "count": 0, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "plates": [], "count": 0, "error": str(e)}

def detect_colors(image: np.ndarray) -> Dict[str, Any]:
    try:
        _, buffer = cv2.imencode('.jpg', image)
        response = requests.post(f"{API_BASE_URL}/detect_colors", files={"file": ("image.jpg", BytesIO(buffer.tobytes()), "image/jpeg")}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            detections = data.get("detections", [])
            primary_color = None
            if detections:
                sorted_dets = sorted(detections, key=lambda x: x.get("confidence", 0), reverse=True)
                primary_color = sorted_dets[0].get("color") if sorted_dets else None
            return {"success": True, "detections": detections, "primary_color": primary_color}
        return {"success": False, "detections": [], "primary_color": None, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "detections": [], "primary_color": None, "error": str(e)}

def count_wheels(image: np.ndarray) -> Dict[str, Any]:
    try:
        _, buffer = cv2.imencode('.jpg', image)
        response = requests.post(f"{API_BASE_URL}/count_wheels", files={"file": ("image.jpg", BytesIO(buffer.tobytes()), "image/jpeg")}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "wheel_count": data.get("wheel_count", 0), "detections": data.get("detections", [])}
        return {"success": False, "wheel_count": 0, "detections": [], "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "wheel_count": 0, "detections": [], "error": str(e)}

def analyze_vehicle(image: np.ndarray, detect_plate_number: bool = True, detect_color: bool = False, count_wheel: bool = False) -> Dict[str, Any]:
    result = {"success": True, "plate": None, "color": None, "wheel_count": None}
    if detect_plate_number:
        plate_result = detect_plate(image)
        result["plate"] = plate_result["plates"][0] if plate_result["success"] and plate_result["plates"] else None
        result["plate_details"] = plate_result
    if detect_color:
        color_result = detect_colors(image)
        result["color"] = color_result.get("primary_color")
        result["color_details"] = color_result
    if count_wheel:
        wheel_result = count_wheels(image)
        result["wheel_count"] = wheel_result.get("wheel_count")
        result["wheel_details"] = wheel_result
    return result

class CameraMode:
    PLATE_DETECTION = "plate"
    VERIFICATION = "verify"
    DISABLED = "disabled"
