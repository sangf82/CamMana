"""Detection and captured cars API endpoints"""
from typing import Optional
from fastapi import APIRouter

from backend import data_process

detection_router = APIRouter(prefix="/api", tags=["detection"])

@detection_router.get("/captured_cars")
async def get_captured_cars(limit: int = 50, date: Optional[str] = None):
    """Get captured cars records"""
    return data_process.get_captured_cars(date=date, limit=limit)

@detection_router.get("/captured_cars/search")
async def search_captured_cars(plate: str, date: Optional[str] = None):
    """Search captured cars by plate number"""
    return data_process.search_by_plate(plate, date=date)

@detection_router.get("/detection_logs")
async def get_detection_logs(camera_id: Optional[str] = None, date: Optional[str] = None, limit: int = 100):
    """Get detection logs"""
    return data_process.get_detection_logs(camera_id=camera_id, date=date, limit=limit)
