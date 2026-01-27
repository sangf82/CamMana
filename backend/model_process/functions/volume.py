
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import httpx
from backend.model_process.config import MODEL_API_URL

logger = logging.getLogger(__name__)

class VolumeDetector:
    ENDPOINT = "/estimate_volume"
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def estimate_volume(
        self,
        side_image_path: Path,
        top_fg_image_path: Path,
        top_bg_image_path: Path,
        side_calib_path: Path,
        top_calib_path: Path,
        dx: float = 0.05,
        threshold: int = 30,
        step_px: int = 5
    ) -> Dict[str, Any]:
        """
        Estimate volume using Top and Side views + Calibration.
        """
        
        # Validate existence
        files_map = {
            "side_img": side_image_path,
            "top_fg": top_fg_image_path,
            "top_bg": top_bg_image_path,
            "calib_side": side_calib_path,
            "calib_top": top_calib_path
        }
        
        for name, path in files_map.items():
            if not path.exists():
                error_msg = f"Missing file for volume detection: {name} -> {path}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

        url = f"{MODEL_API_URL}{self.ENDPOINT}"
        headers = {"accept": "application/json"}
        
        try:
            # Open files
            file_handles = []
            try:
                files = {
                    "image": ("side.jpg", open(side_image_path, "rb"), "image/jpeg"),
                    "img_fg": ("top_fg.jpg", open(top_fg_image_path, "rb"), "image/jpeg"),
                    "img_bg": ("top_bg.jpg", open(top_bg_image_path, "rb"), "image/jpeg"),
                    "calib_side": ("calib_side.json", open(side_calib_path, "rb"), "application/json"),
                    "calib_topdown": ("calib_topdown.json", open(top_calib_path, "rb"), "application/json"),
                }
                
                for _, (_, f_obj, _) in files.items():
                    file_handles.append(f_obj)

                data = {
                    "dx": str(dx),
                    "threshold": str(threshold),
                    "step_px": str(step_px)
                }

                logger.info(f"Sending volume estimation request to {url}")
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, files=files, data=data, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    vol = result.get("volume")
                    
                    # Handle case where volume is returned as string or number
                    if isinstance(vol, str):
                        try: vol = float(vol)
                        except: vol = 0.0
                        
                    logger.info(f"Volume estimation success: {vol} m3")
                    return {
                        "success": True,
                        "volume": vol,
                        "raw": result
                    }
                else:
                    logger.error(f"Volume API Error {response.status_code}: {response.text}")
                    return {
                        "success": False, 
                        "error": f"API Error {response.status_code}",
                        "details": response.text
                    }

            finally:
                for f in file_handles:
                    f.close()


        except Exception as e:
            logger.exception("Volume detection exception")
            return {"success": False, "error": str(e)}
