import cv2
import numpy as np
import logging
import httpx
from typing import Dict, Any
from backend.model_process.config import MODEL_API_URL

logger = logging.getLogger(__name__)

class ColorDetector:
    ENDPOINT = "/detect_colors"
    
    async def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect vehicle color via async API.
        """
        if frame is None:
            return {"detected": False, "error": "Empty frame"}
        
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success: return {"detected": False, "error": "Encoding failed"}
        
        files = {"file": ("image.jpg", encoded_image.tobytes(), "image/jpeg")}
        headers = {"accept": "application/json"}
        
        try:
            url = f"{MODEL_API_URL}{self.ENDPOINT}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, files=files, headers=headers)
            
            if resp.status_code != 200:
                logger.error(f"Color API error {resp.status_code}: {resp.text}")
                return {"detected": False, "error": f"API Error {resp.status_code}"}
            
            data = resp.json()
            # { "detections": [ { "color": "Black", "confidence": ... } ] }
            
            if isinstance(data, str):
                primary_color = data
                return {
                    "detected": True,
                    "primary_color": primary_color,
                    "all_detections": [{"color": primary_color, "confidence": 1.0}],
                    "raw": data
                }

            detections = data.get("detections", [])
            primary_color = "Unknown"
            
            if detections:
                # Get best confidence detection
                best = max(detections, key=lambda x: x.get("confidence", 0))
                primary_color = best.get("color", "Unknown")
                
                return {
                    "detected": True,
                    "primary_color": primary_color,
                    "all_detections": detections,
                    "raw": data
                }
            
            return {"detected": False, "primary_color": "Unknown"}
            
        except Exception as e:
            logger.error(f"Color Detection Error: {e}")
            return {"detected": False, "error": str(e)}
