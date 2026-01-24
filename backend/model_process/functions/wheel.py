import requests
import cv2
import numpy as np
import logging
from typing import Dict, Any
from backend.model_process.config import MODEL_API_URL

logger = logging.getLogger(__name__)

class WheelDetector:
    ENDPOINT = "/count_wheels"
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        if frame is None:
            return {"detected": False, "error": "Empty frame"}
        
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success: return {"detected": False, "error": "Encoding failed"}
        
        files = {"file": ("image.jpg", encoded_image.tobytes(), "image/jpeg")}
        
        try:
            url = f"{MODEL_API_URL}{self.ENDPOINT}"
            resp = requests.post(url, files=files, timeout=10)
            
            if resp.status_code != 200:
                return {"detected": False, "error": f"API Error {resp.status_code}"}
            
            data = resp.json()
            # { "wheel_count": 4, ... }
            count = data.get("wheel_count", 0)
            
            # Logic: Side view detects one side. Total = side * 2.
            total_wheels = count * 2
            
            if count > 0:
                return {
                    "detected": True,
                    "wheel_count_side": count,
                    "wheel_count_total": total_wheels,
                    "raw": data
                }
            return {"detected": False, "wheel_count_total": 0}
            
        except Exception as e:
            logger.error(f"Wheel Detection Error: {e}")
            return {"detected": False, "error": str(e)}
