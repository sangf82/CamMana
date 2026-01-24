from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .logic import LocationLogic

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

@router.get("", response_model=List[LocationResponse])
def get_locations():
    return logic.get_locations()

@router.post("", response_model=LocationResponse)
def add_location(loc: LocationBase):
    try:
        # Pass dict, Logic handles key mapping
        return logic.add_location(loc.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{loc_id}", response_model=LocationResponse)
def update_location(loc_id: str, loc: LocationUpdate):
    try:
        updated = logic.update_location(loc_id, loc.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Location not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{loc_id}")
def delete_location(loc_id: str):
    success = logic.delete_location(loc_id)
    if not success:
         raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Deleted successfully"}
