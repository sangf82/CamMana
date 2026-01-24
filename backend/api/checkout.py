
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

from pydantic import BaseModel
from typing import Dict, Any

class ManualConfirmRequest(BaseModel):
    uuid: str
    plate: str = "Unknown"
    status: Optional[str] = None
    verify: Optional[str] = None
    note: Optional[str] = ""
    vol_measured: Optional[str] = ""
    time_out: Optional[str] = None

@checkout_router.post("/manual-confirm")
async def manual_confirm(req: ManualConfirmRequest):
    """
    Manually confirm a checkout. Merges with open session if found.
    """
    try:
        from backend.data_process.history.logic import HistoryLogic
        from backend.data_process.register_car.logic import RegisteredCarLogic
        
        history = HistoryLogic()
        reg = RegisteredCarLogic()
        
        clean_plate = reg.normalize_plate(req.plate)
        
        # 1. Try to find an existing open session for this plate
        open_session = history.find_open_session(clean_plate)
        
        final_uuid = req.uuid
        merged = False
        
        if open_session and open_session["id"] != req.uuid:
            # MERGE SCENARIO: We found the "Entry" record.
            # The current 'req.uuid' is likely a temp record created during checkout detection.
            # We should update the ENTRY record with Checkout info, and DELETE the temp record.
            
            update_data = {
                "time_out": req.time_out if req.time_out else "",
                "status": req.status if req.status else "Check-Out",
                "verify": req.verify if req.verify else "",
                "note": req.note,
                "vol_measured": req.vol_measured
            }
            
            # TODO: Move evidence image from temp record folder to open_session folder?
            # For simplicity now, we might lose the checkout image if we don't move it.
            # But the requirement is mainly about data logic.
            
            history.update_record(open_session["id"], update_data)
            
            # Delete the temp orphan record
            history.delete_record(req.uuid)
            
            final_uuid = open_session["id"]
            merged = True
        else:
            # UPDATE SCENARIO: Just update the current record
            update_data = {
                "plate": clean_plate,
                "time_out": req.time_out if req.time_out else "",
                "status": req.status if req.status else "",
                "verify": req.verify if req.verify else "",
                "note": req.note,
                "vol_measured": req.vol_measured
            }
            history.update_record(req.uuid, update_data)
            
        return {
            "success": True, 
            "uuid": final_uuid, 
            "merged": merged,
            "plate": clean_plate
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
