import requests
import cv2
import numpy as np
import logging
from typing import Dict, Any
from backend.model_process.config import MODEL_API_URL

logger = logging.getLogger(__name__)

class PlateDetector:
    ENDPOINT = "/alpr"
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect license plate via API.
        """
        if frame is None:
            return {"detected": False, "error": "Empty frame"}
        
        # Encode image
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success:
            return {"detected": False, "error": "Encoding failed"}
        
        files = {"file": ("image.jpg", encoded_image.tobytes(), "image/jpeg")}
        
        try:
            url = f"{MODEL_API_URL}{self.ENDPOINT}"
            resp = requests.post(url, files=files, timeout=30)
            
            if resp.status_code != 200:
                logger.error(f"API Error {resp.status_code}: {resp.text}")
                return {"detected": False, "error": f"API Error {resp.status_code}"}
                
            data = resp.json()
            # Response: { "plates": ["19A..."], "count": ... }
            plates = data.get("plates", [])
            
            if plates:
                return {
                    "detected": True, 
                    "plate": plates[0],  # Primary
                    "all_plates": plates,
                    "raw": data
                }
            
            return {"detected": False}
            
        except Exception as e:
            logger.error(f"Plate Detection Error: {e}")
            return {"detected": False, "error": str(e)}
