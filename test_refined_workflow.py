
import asyncio
import logging
import cv2
from pathlib import Path
from backend.workflow.checkin import get_checkin_service
from backend.workflow.checkout import get_checkout_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_verification():
    # 1. Setup paths
    base_dir = Path("s:/projects/CamMana")
    img_dir = base_dir / "database/car_history/27-01-2026/7264198a-46e1-4e1d-8779-c0c785a8d094_in_14-08-55"
    
    if not img_dir.exists():
        logger.error(f"Image directory not found: {img_dir}")
        return

    side_img = img_dir / "Cam_2_color_detect_wheel_detect.jpg"
    top_img = img_dir / "Cam_1_car_detect_plate_detect.jpg"

    # 2. Test Check-In (Refined API)
    logger.info("=== Testing Refined Check-In (API alignment) ===")
    cis = get_checkin_service()
    images_in = [
        {"cam_name": "Side_Cam", "path": side_img, "functions": ["color", "wheel"]},
        {"cam_name": "Plate_Cam", "path": top_img, "functions": ["plate"]}
    ]
    
    checkin_data = await cis.process_checkin(images_in, location_id="test_location")
    logger.info(f"Check-In Result: {checkin_data}")

    # 3. Test Check-Out (Refined API + Inpainting)
    logger.info("\n=== Testing Refined Check-Out (Volume + Inpainting) ===")
    cos = get_checkout_service()

    uuid_val = checkin_data.uuid
    images_out = [
        {"position": "side", "path": side_img, "functions": ["wheel_detect"]},
        {"position": "top", "path": top_img, "functions": ["volume_top_down"]}
    ]
    
    checkout_data = await cos.process_checkout(images_out, location_id="test_location")
    logger.info(f"Check-Out Result: {checkout_data}")

    # Verify cleaned background exists
    cleaned_bg = Path("cleaned_output") / f"cleaned_{uuid_val}.jpg"
    if cleaned_bg.exists():
        logger.info(f"VERIFIED: Cleaned background generated at {cleaned_bg}")
    else:
        logger.warning("FAILED: Cleaned background not generated.")

if __name__ == "__main__":
    asyncio.run(run_verification())
