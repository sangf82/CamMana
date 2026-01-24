from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .logic import CameraTypeLogic

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

@router.get("", response_model=List[CameraTypeResponse])
def get_types():
    return logic.get_types()

@router.post("", response_model=CameraTypeResponse)
def add_type(cam_type: CameraTypeBase):
    return logic.add_type(cam_type.dict())

@router.put("/{id}", response_model=CameraTypeResponse)
def update_type(id: str, cam_type: CameraTypeUpdate):
    updated = logic.update_type(id, cam_type.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Type not found")
    return updated

@router.delete("/{id}")
def delete_type(id: str):
    success = logic.delete_type(id)
    if not success:
         raise HTTPException(status_code=404, detail="Type not found")
    return {"message": "Deleted successfully"}
