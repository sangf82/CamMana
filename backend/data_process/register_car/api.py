from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import io
import logging

from backend.api.user import get_current_user
from backend.schemas import User as UserSchema
from backend.data_process.sync.proxy import is_client_mode, proxy_get, proxy_post, proxy_put, proxy_delete
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

@router.get("")
async def get_cars():
    """
    Get all registered cars. 
    When in client mode, fetches data from master node.
    """
    # If in client mode, proxy the request to master
    if is_client_mode():
        logger.info("Client mode: Fetching registered cars from master")
        master_data = await proxy_get("/api/registered_cars")
        if master_data is not None:
            return master_data
        else:
            logger.warning("Failed to fetch from master, falling back to local data")
    
    # Local data (master mode or fallback)
    return logic.get_all_cars()

@router.post("")
async def add_car(car: CarBase, user: UserSchema = Depends(get_current_user)):
    """
    Add a new registered car.
    When in client mode, proxies to master node.
    """
    # If user has 'can_add_vehicles' enabled, it means they MUST provide the set code
    # Unless they are admin
    if user.role != "admin" and user.can_add_vehicles:
        if not car.admin_code or car.admin_code != user.vehicle_add_code:
             raise HTTPException(status_code=403, detail="Mã xác nhận Admin không chính xác")
             
    try:
        data = car.dict()
        data.pop('admin_code', None) # Remove before saving to CSV
        
        # If in client mode, proxy to master
        if is_client_mode():
            logger.info("Client mode: Adding car via master")
            result = await proxy_post("/api/registered_cars", data)
            if result is not None:
                return result
            else:
                raise HTTPException(status_code=503, detail="Cannot connect to master node")
        
        return logic.add_car(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{car_id}")
async def update_car(car_id: str, car: CarUpdate):
    """
    Update a registered car.
    When in client mode, proxies to master node.
    """
    # If in client mode, proxy to master
    if is_client_mode():
        logger.info(f"Client mode: Updating car {car_id} via master")
        result = await proxy_put(f"/api/registered_cars/{car_id}", car.dict(exclude_unset=True))
        if result is not None:
            return result
        else:
            raise HTTPException(status_code=503, detail="Cannot connect to master node")
        
    updated = logic.update_car(car_id, car.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Car not found")
    return updated

@router.delete("/{car_id}")
async def delete_car(car_id: str):
    """
    Delete a registered car.
    When in client mode, proxies to master node.
    """
    # If in client mode, proxy to master
    if is_client_mode():
        logger.info(f"Client mode: Deleting car {car_id} via master")
        success = await proxy_delete(f"/api/registered_cars/{car_id}")
        if success:
            return {"message": "Deleted successfully"}
        else:
            raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
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
