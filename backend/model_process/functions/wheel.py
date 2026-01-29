import cv2
import numpy as np
import logging
import httpx
from typing import Dict, Any
from backend.model_process.config import MODEL_API_URL

logger = logging.getLogger(__name__)

class WheelDetector:
    ENDPOINT = "/count_wheels"
    
    async def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect wheels via async API.
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
                logger.error(f"Wheel API error {resp.status_code}: {resp.text}")
                return {"detected": False, "error": f"API Error {resp.status_code}"}
            
            data = resp.json()

            # Handle error field in response
            if isinstance(data, dict) and "detail" in data:
                logger.error(f"Wheel API detail error: {data['detail']}")
                return {"detected": False, "error": data["detail"]}

            # { "wheel_count": 4, ... } or "4"
            if isinstance(data, (int, str)):
                try: count = int(data)
                except: count = 0
            else:
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
            error_msg = str(e) if str(e) else f"{type(e).__name__}: No details"
            logger.error(f"Wheel Detection Error: {error_msg}", exc_info=True)
            return {"detected": False, "error": error_msg}
