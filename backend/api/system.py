import platform
import psutil
import socket
from fastapi import APIRouter, Depends
from backend.api.user import get_current_user
from backend.schemas import User

router = APIRouter(prefix="/api/system", tags=["System"])

@router.get("/info")
def get_system_info(user: User = Depends(get_current_user)):
    # Basic specs
    info = {
        "pc_name": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "ip_address": socket.gethostbyname(socket.gethostname())
    }
    return info
