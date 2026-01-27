from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from .logic import CameraTypeLogic
from backend.sync_process.sync.proxy import is_client_mode, proxy_get, proxy_post, proxy_put, proxy_delete

logger = logging.getLogger(__name__)

class CameraTypeBase(BaseModel):
    name: str
    functions: List[str]

class CameraTypeUpdate(BaseModel):
    name: Optional[str] = None
    functions: Optional[List[str]] = None

class CameraTypeResponse(CameraTypeBase):
    id: str

router = APIRouter(prefix="/api/camera_types", tags=["Camera Types"])
logic = CameraTypeLogic()

@router.get("")
async def get_types():
    """Get all camera types. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info("Client mode: Fetching camera types from master")
        result = await proxy_get("/api/camera_types")
        if result is not None:
            return result
    
    return logic.get_types()

@router.post("")
async def add_type(cam_type: CameraTypeBase):
    """Add a new camera type. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info("Client mode: Adding camera type via master")
        result = await proxy_post("/api/camera_types", cam_type.dict())
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    return logic.add_type(cam_type.dict())

@router.put("/{id}")
async def update_type(id: str, cam_type: CameraTypeUpdate):
    """Update a camera type. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info(f"Client mode: Updating camera type {id} via master")
        result = await proxy_put(f"/api/camera_types/{id}", cam_type.dict(exclude_unset=True))
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    updated = logic.update_type(id, cam_type.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Type not found")
    return updated

@router.delete("/{id}")
async def delete_type(id: str):
    """Delete a camera type. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info(f"Client mode: Deleting camera type {id} via master")
        success = await proxy_delete(f"/api/camera_types/{id}")
        if success:
            return {"message": "Deleted successfully"}
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    success = logic.delete_type(id)
    if not success:
         raise HTTPException(status_code=404, detail="Type not found")
    return {"message": "Deleted successfully"}

