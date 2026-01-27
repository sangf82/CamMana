from enum import Enum
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field

# Enums
class CameraStatus(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    CONNECTING = "Connecting"
    ERROR = "Error"

# Shared Models
class CameraConnectRequest(BaseModel):
    ip: str
    port: int = 8899
    user: str = "admin"
    password: str = ""
    name: str = "Camera"
    tag: Optional[str] = None
    detection_mode: str = "disabled"

class PTZMoveRequest(BaseModel):
    speed: float = 0.5

class UpdateDetectionModeRequest(BaseModel):
    detection_mode: str

class UpdateCameraTagRequest(BaseModel):
    tag: Optional[str]

# Camera Models
class CameraBase(BaseModel):
    name: Optional[str] = "Camera"
    ip: Optional[str] = None
    port: int = 8899
    user: str = "admin"
    password: str = ""
    location: Optional[str] = ""
    location_id: Optional[str] = ""
    type: Optional[str] = ""
    status: str = "Offline"
    tag: Optional[str] = None
    username: str = "admin"
    brand: Optional[str] = ""
    cam_id: Optional[str] = ""
    stream_uri: Optional[str] = None
    snapshot_uri: Optional[str] = None
    profile_token: Optional[str] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    detection_mode: str = "disabled"

class CameraCreate(CameraBase):
    id: Optional[Union[str, int, float]] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    location: Optional[str] = None
    location_id: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    tag: Optional[str] = None
    username: Optional[str] = None
    brand: Optional[str] = None
    cam_id: Optional[str] = None
    stream_uri: Optional[str] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    detection_mode: Optional[str] = None

class Camera(CameraBase):
    id: Union[str, int, float] # Handles timestamp-based IDs which might be read as diverse types

# History Models
class HistoryRecord(BaseModel):
    id: Optional[str] = None
    plate: str
    location: str
    time_in: str
    time_out: str = "---"
    vol_std: str = ""
    vol_measured: str = ""
    status: str = ""
    verify: str = ""
    note: str = ""
    folder_path: str = ""

# Registered Car Models
class RegisteredCar(BaseModel):
    car_id: Optional[str] = None
    car_plate: str
    car_brand: str = ""
    car_model: str = "" # Added to match typical needs
    car_owner: str = ""
    car_color: str = ""
    car_wheel: str = ""
    car_dimension: str = ""
    car_volume: str = ""
    car_note: str = ""
    car_register_date: str = ""
    car_update_date: str = ""

# Other Models
class LogRecord(BaseModel):
    timestamp: str
    camera_id: str
    event_type: str
    details: Union[str, Dict[str, Any], None] = None

class Location(BaseModel):
    id: str
    name: str
    tag: str

class CameraType(BaseModel):
    id: str
    name: str
    functions: str

class CapturedCar(BaseModel):
    id: Optional[str] = None
    timestamp: str
    folder_path: str = ""
    plate_number: str = ""
    primary_color: str = ""
    wheel_count: Union[int, str] = ""
    front_cam_id: str = ""
    side_cam_id: str = ""
    confidence: Union[float, str] = ""
    class_name: str = ""
    bbox: Optional[Union[List[Any], str]] = None
    volume: Union[float, str] = ""

class ExecuteDetectionRequest(BaseModel):
    force: bool = False

# User Models
class User(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    role: str = "operator"  # admin, operator
    allowed_gates: Optional[str] = "*"  # comma-separated list or "*"
    can_manage_cameras: bool = False
    can_add_vehicles: bool = False
    vehicle_add_code: Optional[str] = ""
    created_at: str = ""

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "operator"
    allowed_gates: Optional[str] = "*"
    can_manage_cameras: bool = False
    can_add_vehicles: bool = False
    vehicle_add_code: Optional[str] = ""

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    allowed_gates: Optional[str] = None
    can_manage_cameras: Optional[bool] = None
    can_add_vehicles: Optional[bool] = None
    vehicle_add_code: Optional[str] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[User] = None

class TokenData(BaseModel):
    username: Optional[str] = None

# Sync Models
class SyncNode(BaseModel):
    id: str
    ip: str
    name: str
    status: str = "offline"
    last_sync: str = ""

class SyncPayload(BaseModel):
    type: str  # history, camera, registered_car
    action: str  # create, update, delete
    data: Dict[str, Any]
    timestamp: str
