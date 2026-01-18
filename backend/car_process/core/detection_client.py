import httpx
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# External API Configuration - could be moved to centralized config
API_BASE_URL = "https://thpttl12t1--truck-api-fastapi-app.modal.run"
API_TIMEOUT = 30.0

class DetectionClient:
    """Client for interactions with the external Vehicle Detection API"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=API_TIMEOUT)
        return self._client
        
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _post_file(self, endpoint: str, file_path: Path) -> Dict[str, Any]:
        """Helper to post a file to an endpoint"""
        try:
            if not file_path.exists():
                return {"error": "File not found"}
                
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "image/jpeg")}
                response = await self.client.post(
                    f"{API_BASE_URL}{endpoint}",
                    files=files
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            # Normalize error format across all endpoints
            return {"error": str(e), "details": "API request failed"}

    async def detect_plate(self, image_path: Path) -> Dict[str, Any]:
        """Detect license plate from image"""
        result = await self._post_file("/alpr", image_path)
        # Ensure consistent fallback structure
        if "error" in result and "plates" not in result:
             result["plates"] = []
             result["count"] = 0
        return result

    async def detect_color(self, image_path: Path) -> Dict[str, Any]:
        """Detect vehicle colors from image"""
        result = await self._post_file("/detect_colors", image_path)
        if "error" in result and "detections" not in result:
            result["detections"] = []
        return result

    async def detect_wheels(self, image_path: Path) -> Dict[str, Any]:
        """Count vehicle wheels from image"""
        result = await self._post_file("/count_wheels", image_path)
        if "error" in result:
            if "wheel_count" not in result:
                result["wheel_count"] = 0
            if "detections" not in result:
                result["detections"] = []
        return result
    
    async def run_all_detections(self, front_image: Path, side_image: Path):
        """Run all detections in parallel"""
        return await asyncio.gather(
            self.detect_plate(front_image),
            self.detect_color(side_image),
            self.detect_wheels(side_image)
        )
