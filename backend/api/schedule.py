"""Schedule management API endpoints - DEPRECATED

Schedule functionality has been removed.
These endpoints return empty data for backward compatibility.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

schedule_router = APIRouter(prefix="/api", tags=["schedule"])

@schedule_router.get("/schedule")
async def get_schedule():
    """Get schedule data - DEPRECATED
    
    Schedule functionality has been removed.
    Returns empty array for backward compatibility.
    """
    return []

@schedule_router.post("/schedule/upload")
async def upload_schedule():
    """Upload schedule - DEPRECATED
    
    Schedule functionality has been removed.
    Returns success for backward compatibility.
    """
    return {"success": True, "message": "Schedule functionality has been removed"}
