
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import logging

from backend.api.user import get_current_user
from backend.schemas import User as UserSchema

from backend.data_process.history.logic import HistoryLogic
from backend.data_process.sync.proxy import is_client_mode, proxy_get, proxy_post, proxy_put
from backend.schemas import HistoryRecord

logger = logging.getLogger(__name__)

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

@router.get("/dates")
async def get_available_dates():
    """
    Get available history dates.
    When in client mode, fetches from master node.
    """
    if is_client_mode():
        logger.info("Client mode: Fetching history dates from master")
        result = await proxy_get("/api/history/dates")
        if result is not None:
            return result
        logger.warning("Failed to fetch dates from master, falling back to local")
    
    return logic.get_available_dates()

@router.get("")
async def get_history(
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format"),
    user: UserSchema = Depends(get_current_user)
):
    """
    Get history records. If date is None, returns today's records.
    When in client mode, fetches from master node.
    """
    if is_client_mode():
        logger.info(f"Client mode: Fetching history for date {date} from master")
        endpoint = "/api/history" if not date else f"/api/history?date={date}"
        result = await proxy_get(endpoint)
        if result is not None:
            return result
        logger.warning("Failed to fetch history from master, falling back to local")
    
    all_records = logic.get_records(date)
    return all_records

@router.post("")
async def add_history_record(record: Dict[str, Any]):
    """
    Add a new history record.
    When in client mode, proxies to master node.
    """
    if is_client_mode():
        logger.info("Client mode: Adding history record via master")
        result = await proxy_post("/api/history", record)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
        
    try:
        new_record = logic.add_record(record)
        return new_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{record_id}")
async def update_history_record(record_id: str, update_data: Dict[str, Any]):
    """
    Update a history record.
    When in client mode, proxies to master node.
    """
    if is_client_mode():
        logger.info(f"Client mode: Updating history record {record_id} via master")
        result = await proxy_put(f"/api/history/{record_id}", update_data)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    updated = logic.update_record(record_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")
    return updated

