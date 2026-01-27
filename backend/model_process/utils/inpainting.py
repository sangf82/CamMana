
import os
import logging
import numpy as np
import cv2
import httpx
from pathlib import Path
from PIL import Image
import onnxruntime as ort
from typing import Optional, Dict

from backend.settings import settings

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages downloading and caching of model weights."""
    LAMA_URL = "https://github.com/advimman/lama/raw/main/lama.onnx" # Placeholder, actual link needed or provided
    U2NETP_URL = "https://github.com/xuebinqin/U-2-Net/raw/master/u2netp.onnx" # Placeholder

    @staticmethod
    async def download_model(url: str, dest_path: Path):
        if dest_path.exists():
            return
        
        logger.info(f"Downloading model from {url} to {dest_path}...")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        logger.info(f"Model downloaded successfully.")

class Inpainter:
    _instance = None
    _session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Inpainter, cls).__new__(cls)
        return cls._instance

    async def init_session(self):
        if self._session is not None:
            return
        
        model_path = settings.models_dir / "inpainting" / "lama.onnx"
        if not model_path.exists():
            logger.warning(f"LaMa model not found at {model_path}. Using cv2.inpaint as fallback.")
            return

        logger.info("Initializing LaMa inpainting session...")
        try:
            opts = ort.SessionOptions()
            opts.enable_mem_pattern = False
            self._session = ort.InferenceSession(str(model_path), sess_options=opts, providers=['CPUExecutionProvider'])
        except Exception as e:
            logger.error(f"Failed to load LaMa model: {e}. Using fallback.")
            self._session = None

    def inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Inpaint image using LaMa ONNX or OpenCV fallback.
        image: RGB numpy array
        mask: 1-ch gray numpy array (255 for hole)
        """
        if self._session is None:
            # OpenCV Fallback
            # Convert to BGR for opencv if needed, but inpaint works on channels
            # result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
            # Actually, opencv handles RGB/BGR the same for inpaint
            return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)

        # Preprocessing...
        # Assuming model accepts dynamic or 512x512. LaMa is usually 512x512.
        h, w = image.shape[:2]
        img_resized = cv2.resize(image, (512, 512)).astype(np.float32) / 255.0
        mask_resized = cv2.resize(mask, (512, 512)).astype(np.float32) / 255.0
        mask_resized[mask_resized > 0] = 1.0

        # Input: [1, 3, 512, 512] and [1, 1, 512, 512]
        img_input = img_resized.transpose(2, 0, 1)[None]
        mask_input = mask_resized[None, None]

        inputs = {
            self._session.get_inputs()[0].name: img_input,
            self._session.get_inputs()[1].name: mask_input
        }
        
        outputs = self._session.run(None, inputs)
        result = outputs[0][0].transpose(1, 2, 0)
        result = (result * 255.0).clip(0, 255).astype(np.uint8)

        # Postprocessing: Resize back and blend? 
        # For background removal, we usually just want the full result.
        return cv2.resize(result, (w, h))

class MaskGenerator:
    _instance = None
    _session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MaskGenerator, cls).__new__(cls)
        return cls._instance

    async def init_session(self):
        if self._session is not None:
            return
        
        model_path = settings.models_dir / "masking" / "u2netp.onnx"
        if not model_path.exists():
            logger.warning(f"Masking model not found at {model_path}. Please ensure u2netp.onnx is present.")
            return

        logger.info("Initializing u2netp masking session...")
        self._session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])

    async def generate_mask(self, image: np.ndarray, bbox: Optional[Dict] = None) -> np.ndarray:
        """
        Generate mask. If bbox is provided, use it. Else use u2netp.
        bbox format: {"x":.., "y":.., "w":.., "h":..}
        """
        h, w = image.shape[:2]
        
        if bbox:
            mask = np.zeros((h, w), dtype=np.uint8)
            x, y, bw, bh = int(bbox['x']), int(bbox['y']), int(bbox['w']), int(bbox['h'])
            cv2.rectangle(mask, (x, y), (x + bw, y + bh), 255, -1)
            # Dilate bbox slightly
            kernel = np.ones((15, 15), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=2)
            return mask

        if self._session is None:
            # Fallback: simple center mask if everything fails? No, return empty.
            return np.zeros((h, w), dtype=np.uint8)

        # U2NETP logic...
        img_resized = cv2.resize(image, (320, 320)).astype(np.float32)
        img_resized = (img_resized - 127.5) / 127.5
        img_input = img_resized.transpose(2, 0, 1)[None]

        outputs = self._session.run(None, {self._session.get_inputs()[0].name: img_input})
        mask_raw = outputs[0][0, 0]
        mask = (mask_raw * 255).astype(np.uint8)
        mask = cv2.threshold(mask, 50, 255, cv2.THRESH_BINARY)[1] # Lower threshold
        
        return cv2.resize(mask, (w, h))

async def generate_seamless_background(image_path: Path, output_path: Path, truck_bbox: Optional[Dict] = None):
    """
    Automated background generator.
    truck_bbox: optional bounding box from a detector.
    """
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"Failed to read image from {image_path}")
            return False
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    mg = MaskGenerator()
    await mg.init_session()
    mask = await mg.generate_mask(img_rgb, bbox=truck_bbox)

    # Dilate mask to ensure edges are covered
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=3)

        inp = Inpainter()
        await inp.init_session()
        result_rgb = inp.inpaint(img_rgb, mask)

        result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
        success = cv2.imwrite(str(output_path), result_bgr)
        
        if success:
            logger.info(f"Background image saved successfully to {output_path}")
        else:
            logger.error(f"Failed to save background image to {output_path}")
        
        return success
    except Exception as e:
        logger.error(f"Error in generate_seamless_background: {e}", exc_info=True)
        return False

