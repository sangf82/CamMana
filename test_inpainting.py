
import asyncio
import logging
from pathlib import Path
from backend.utils.inpainting import generate_seamless_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_inpainting():
    input_img = Path("database/car_history/27-01-2026/7264198a-46e1-4e1d-8779-c0c785a8d094_in_14-08-55/Cam_1_car_detect_plate_detect.jpg")
    output_img = Path("cleaned_output/test_cleaned.jpg")
    
    if not input_img.exists():
        logger.error(f"Input image not found: {input_img}")
        return

    logger.info(f"Testing inpainting on {input_img}...")
    success = await generate_seamless_background(input_img, output_img)
    
    if success:
        logger.info(f"Inpainting successful! Saved to {output_img}")
    else:
        logger.error("Inpainting failed.")

if __name__ == "__main__":
    asyncio.run(test_inpainting())
