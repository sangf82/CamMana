
import asyncio
import logging
import cv2
import numpy as np
from pathlib import Path
from backend.utils.inpainting import MaskGenerator, Inpainter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_inpainting():
    input_path = Path("database/car_history/27-01-2026/7264198a-46e1-4e1d-8779-c0c785a8d094_in_14-08-55/Cam_1_car_detect_plate_detect.jpg")
    
    img = cv2.imread(str(input_path))
    if img is None:
        logger.error("Image not found")
        return
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Test Masking with hardcoded bbox
    # Estimated for the toy truck in the sample image
    toy_bbox = {"x": 250, "y": 150, "w": 300, "h": 500}
    mg = MaskGenerator()
    await mg.init_session()
    mask = await mg.generate_mask(img_rgb, bbox=toy_bbox)
    
    cv2.imwrite("cleaned_output/debug_mask.jpg", mask)
    logger.info("Saved debug_mask.jpg")
    
    # 2. Test Inpainting Fallback
    inp = Inpainter()
    await inp.init_session() # This should fail for LaMa and set session to None
    
    # Force OpenCV inpaint (it's already the fallback if session is None)
    # Dilate mask
    kernel = np.ones((15, 15), np.uint8)
    mask_dilated = cv2.dilate(mask, kernel, iterations=3)
    cv2.imwrite("cleaned_output/debug_mask_dilated.jpg", mask_dilated)
    
    # result_rgb = inp.inpaint(img_rgb, mask_dilated)
    # Use cv2.inpaint directly for debug
    result_bgr = cv2.inpaint(img, mask_dilated, 3, cv2.INPAINT_TELEA)
    
    cv2.imwrite("cleaned_output/debug_result.jpg", result_bgr)
    logger.info("Saved debug_result.jpg")

if __name__ == "__main__":
    asyncio.run(debug_inpainting())
