from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import io
import logging

from backend.api.user import get_current_user
from backend.schemas import User as UserSchema
from .logic import RegisteredCarLogic

logger = logging.getLogger(__name__)

# Pydantic models
# Using generic names for frontend compatibility or updating frontend?
# Since the goal is to fix "cannot load", likely backend was inconsistent.
# I will use schemas.RegisteredCar derived models or similar.

class CarBase(BaseModel):
    car_plate: str
    car_owner: str = ""
    car_brand: str = ""
    car_model: str = ""
    car_color: str = ""
    car_note: str = ""
    car_wheel: str = ""
    car_volume: Optional[str] = ""
    admin_code: Optional[str] = ""
    
    # Alias for frontend? 
    # If the frontend sends 'plate_number', we can use aliases or just fix the frontend.
    # The Prompt doesn't ask to fix frontend, but "loading data". 
    # If I change API keys, I might break frontend sends.
    # But currently the backend API used keys that logic DID NOT SUPPORT (e.g. owner).
    # So I WAS breaking data save. 
    # I will support aliasing if needed, but for now Standardize on Backend Keys.
    
class CarUpdate(BaseModel):
    car_owner: Optional[str] = None
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    car_color: Optional[str] = None
    car_note: Optional[str] = None
    car_wheel: Optional[str] = None
    car_volume: Optional[str] = None

class CarResponse(CarBase):
    car_id: str
    car_register_date: str = ""
    car_update_date: str = ""

router = APIRouter(prefix="/api/registered_cars", tags=["Registered Cars"])
logic = RegisteredCarLogic()

@router.get("", response_model=List[CarResponse])
def get_cars():
    # Logic returns dict with car_ keys. Response model matches car_ keys.
    return logic.get_all_cars()

@router.post("", response_model=CarResponse)
def add_car(car: CarBase, user: UserSchema = Depends(get_current_user)):
    # If user has 'can_add_vehicles' enabled, it means they MUST provide the set code
    # Unless they are admin
    if user.role != "admin" and user.can_add_vehicles:
        if not car.admin_code or car.admin_code != user.vehicle_add_code:
             raise HTTPException(status_code=403, detail="Mã xác nhận Admin không chính xác")
             
    try:
        data = car.dict()
        data.pop('admin_code', None) # Remove before saving to CSV
        return logic.add_car(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{car_id}", response_model=CarResponse)
def update_car(car_id: str, car: CarUpdate):
    updated = logic.update_car(car_id, car.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Car not found")
    return updated

@router.delete("/{car_id}")
def delete_car(car_id: str):
    success = logic.delete_car(car_id)
    if not success:
        raise HTTPException(status_code=404, detail="Car not found")
    return {"message": "Deleted successfully"}

@router.post("/import")
async def import_cars(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            # Detect encoding? utf-8 usually.
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(400, "Invalid file format. Use CSV or XLSX.")
        
        # Convert to list of dicts
        # Replace NaN with empty string
        df = df.fillna("")
        data = df.to_dict(orient='records')
        
        stats = logic.import_cars(data)
        return {"message": "Import completed", "stats": stats}
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@router.get("/health")
def health_check():
    return logic.health_check()
