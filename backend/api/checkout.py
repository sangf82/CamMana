
import tempfile
import shutil
import cv2
import asyncio
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional

from backend.workflow.checkout import get_checkout_service

checkout_router = APIRouter(prefix="/api/checkout", tags=["check-out"])

@checkout_router.post("/process")
async def process_checkout(
    front_image: UploadFile = File(...),
    location_id: str = Form(...),
):
    """
    Process vehicle check-out. Matches plate with open sessions.
    """
    try:
        service = get_checkout_service()
        
        # Save temp image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            shutil.copyfileobj(front_image.file, tmp)
            tmp_path = Path(tmp.name)
            
        result = await service.process_checkout(
            front_image_path=tmp_path,
            location_id=location_id
        )
        
        # Cleanup
        tmp_path.unlink(missing_ok=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
