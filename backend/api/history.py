"""History data API endpoints"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend import data_process
from backend.schemas import HistoryRecord

history_router = APIRouter(prefix="/api/history", tags=["history"])

@history_router.get("")
async def get_history(date: Optional[str] = None):
    """Get history data for a specific date (format: dd/mm/yyyy or dd_mm_yyyy)
    If no date provided, returns today's history
    """
    try:
        data = data_process.get_history_data(date=date)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@history_router.get("/dates")
async def get_history_dates():
    """Get list of all available history dates"""
    try:
        dates = data_process.get_available_history_dates()
        return {"success": True, "dates": dates}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@history_router.get("/range")
async def get_history_range(start_date: str, end_date: str):
    """Get history data for a date range (format: dd/mm/yyyy)"""
    try:
        data = data_process.get_history_date_range(start_date, end_date)
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@history_router.post("")
async def save_history(record: HistoryRecord, date: Optional[str] = None):
    """Save a single history record"""
    try:
        data_process.save_history_record(record, date=date)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@history_router.post("/bulk")
async def save_history_bulk(records: List[HistoryRecord], date: Optional[str] = None):
    """Save multiple history records, replacing the entire file"""
    try:
        data_process.save_history_data(records, date=date)
        return {"success": True, "count": len(records)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


class HistoryUpdateRequest(BaseModel):
    plate: str
    time_in: str
    status: Optional[str] = None
    verify: Optional[str] = None
    note: Optional[str] = None
    time_out: Optional[str] = None
    vol_measured: Optional[str] = None


@history_router.put("")
async def update_history(request: HistoryUpdateRequest, date: Optional[str] = None):
    """Update an existing history record by plate and time_in"""
    try:
        updates = {}
        if request.status is not None:
            updates['status'] = request.status
        if request.verify is not None:
            updates['verify'] = request.verify
        if request.note is not None:
            updates['note'] = request.note
        if request.time_out is not None:
            updates['time_out'] = request.time_out
        if request.vol_measured is not None:
            updates['vol_measured'] = request.vol_measured
        
        if not updates:
            return {"success": False, "error": "No updates provided"}
        
        updated = data_process.update_history_record(
            plate=request.plate,
            time_in=request.time_in,
            updates=updates,
            date=date
        )
        
        if updated:
            return {"success": True}
        else:
            return {"success": False, "error": "Record not found"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
