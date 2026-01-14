"""History data API endpoints"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import data_process

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
async def save_history(record: Dict[str, Any], date: Optional[str] = None):
    """Save a single history record"""
    try:
        data_process.save_history_record(record, date=date)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@history_router.post("/bulk")
async def save_history_bulk(records: List[Dict[str, Any]], date: Optional[str] = None):
    """Save multiple history records, replacing the entire file"""
    try:
        data_process.save_history_data(records, date=date)
        return {"success": True, "count": len(records)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
