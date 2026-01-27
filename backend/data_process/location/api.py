from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
import logging

from .logic import LocationLogic
from backend.data_process.user.api import get_current_user
from backend.schemas import User as UserSchema
from backend.sync_process.sync.proxy import is_client_mode, proxy_get, proxy_post, proxy_put, proxy_delete

logger = logging.getLogger(__name__)

class LocationBase(BaseModel):
    name: Optional[str] = None
    tag: Optional[str] = None
    # backward compat
    location_name: Optional[str] = None
    location_tag: Optional[str] = None

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    tag: Optional[str] = None
    location_name: Optional[str] = None
    location_tag: Optional[str] = None

class LocationResponse(BaseModel):
    id: str
    name: str
    tag: str

router = APIRouter(prefix="/api/locations", tags=["Locations"])
logic = LocationLogic()

@router.get("")
async def get_locations(request: Request, user: UserSchema = Depends(get_current_user)):
    """Get all locations. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("Client mode: Fetching locations from master")
        result = await proxy_get("/api/locations", token=token)
        if result is not None:
            # Filter by user permissions
            if user.role == "admin" or user.allowed_gates == "*":
                return result
            allowed = [g.strip() for g in user.allowed_gates.split(',')]
            return [l for l in result if l.get('name') in allowed]
    
    all_locs = logic.get_locations()
    if user.role == "admin" or user.allowed_gates == "*":
        return all_locs
    
    allowed = [g.strip() for g in user.allowed_gates.split(',')]
    return [l for l in all_locs if l['name'] in allowed]

@router.post("")
async def add_location(request: Request, loc: LocationBase):
    """Add a new location. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("Client mode: Adding location via master")
        result = await proxy_post("/api/locations", loc.dict(), token=token)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    try:
        return logic.add_location(loc.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{loc_id}")
async def update_location(request: Request, loc_id: str, loc: LocationUpdate):
    """Update a location. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"Client mode: Updating location {loc_id} via master")
        result = await proxy_put(f"/api/locations/{loc_id}", loc.dict(exclude_unset=True), token=token)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    try:
        updated = logic.update_location(loc_id, loc.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Location not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{loc_id}")
async def delete_location(request: Request, loc_id: str):
    """Delete a location. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"Client mode: Deleting location {loc_id} via master")
        success = await proxy_delete(f"/api/locations/{loc_id}", token=token)
        if success:
            return {"message": "Deleted successfully"}
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    success = logic.delete_location(loc_id)
    if not success:
         raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Deleted successfully"}

