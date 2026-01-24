
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from backend.data_process.history.logic import HistoryLogic
from backend.schemas import HistoryRecord

router = APIRouter(prefix="/api/history", tags=["History"])
logic = HistoryLogic()

class HistoryResponse(BaseModel):
    id: str
    plate: str
    location: str
    time_in: str
    time_out: str
    vol_std: str
    vol_measured: str
    status: str
    verify: str
    note: str
    folder_path: str

@router.get("/dates", response_model=List[str])
def get_available_dates():
    return logic.get_available_dates()

@router.get("", response_model=List[Dict[str, Any]])
def get_history(date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format")):
    """
    Get history records. If date is None, returns today's records.
    """
    return logic.get_records(date)

@router.post("", response_model=Dict[str, str])
def add_history_record(record: Dict[str, Any]):
    try:
        new_record = logic.add_record(record)
        return new_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{record_id}", response_model=Dict[str, str])
def update_history_record(record_id: str, update_data: Dict[str, Any]):
    updated = logic.update_record(record_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")
    return updated
