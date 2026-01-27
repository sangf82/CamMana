"""
System API Endpoints

Provides endpoints for:
- System information (PC name, IP, specs)
- Firewall management (Windows)
"""

import os
import platform
import psutil
import socket
import subprocess
from fastapi import APIRouter, Depends, HTTPException

from backend.data_process.user.api import get_current_user
from backend.schemas import User
from backend.settings import settings

system_router = APIRouter(prefix="/api/system", tags=["System"])

FIREWALL_RULE_NAME = "CamMana Backend"


def get_lan_ip() -> str:
    """Get the best LAN IP address for this machine."""
    # Priority 1: Try active gateway interface
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
        if not IP.startswith('169.254'):
            return IP
    except Exception:
        pass
    finally:
        s.close()

    # Priority 2: Iterate interfaces (prefer private ranges)
    interfaces = psutil.net_if_addrs()
    preferred_prefixes = ('192.168.', '10.', '172.')
    
    for _, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                if any(ip.startswith(pref) for pref in preferred_prefixes):
                    return ip

    # Priority 3: Any non-loopback, non-APIPA
    for _, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                if not ip.startswith('127.') and not ip.startswith('169.254'):
                    return ip
                    
    # Fallback to hostname
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if not host_ip.startswith('169.254'):
            return host_ip
    except:
        pass

    return "127.0.0.1"


@system_router.get("/info")
def get_system_info():
    """Get system information - no auth required for sync discovery."""
    return {
        "pc_name": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "ip_address": get_lan_ip()
    }


@system_router.get("/firewall/status")
def check_firewall_status():
    """Check if firewall rule for CamMana exists (Windows only)."""
    if platform.system() != "Windows":
        return {"supported": False, "message": "Firewall management only supported on Windows"}
    
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={FIREWALL_RULE_NAME}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        rule_exists = "Rule Name:" in result.stdout and FIREWALL_RULE_NAME in result.stdout
        
        return {
            "supported": True,
            "rule_exists": rule_exists,
            "rule_name": FIREWALL_RULE_NAME,
            "message": "Đã mở firewall" if rule_exists else "CONFIG: Rule Not Found"
        }
    except Exception as e:
        return {
            "supported": True,
            "rule_exists": False,
            "error": str(e),
            "message": "CORE: System Exception"
        }


@system_router.post("/firewall/open")
def open_firewall(user: User = Depends(get_current_user)):
    """
    Add firewall rule to allow CamMana backend connections.
    Requires admin privileges - will prompt UAC dialog.
    """
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Only supported on Windows")
    
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Requires admin role")
    
    try:
        port = settings.port
        
        # PowerShell command to add firewall rule with elevation
        cmd = f'netsh advfirewall firewall add rule name="{FIREWALL_RULE_NAME}" dir=in action=allow protocol=TCP localport={port} profile=any'
        elevated_cmd = f'Start-Process cmd -ArgumentList \'/c {cmd}\' -Verb RunAs -Wait -WindowStyle Hidden'
        
        print(f"Executing firewall open command: {elevated_cmd}")
        
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", elevated_cmd],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if result.returncode != 0:
            print(f"Firewall automation error: {result.stderr}")
        
        # Check if rule was added successfully
        check_result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={FIREWALL_RULE_NAME}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        rule_exists = "Rule Name:" in check_result.stdout and FIREWALL_RULE_NAME in check_result.stdout
        
        if rule_exists:
            return {
                "success": True,
                "message": f"Đã mở tường lửa cho cổng {port}",
                "rule_name": FIREWALL_RULE_NAME
            }
        else:
            return {
                "success": False,
                "message": "Không thể thêm quy tắc. Có thể bạn đã hủy yêu cầu UAC hoặc lỗi quyền truy cập.",
                "hint": "Vui lòng chấp nhận yêu cầu quyền Admin khi được hỏi hoặc thử chạy backend dưới quyền Administrator."
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Hết thời gian chờ. Đã hủy yêu cầu?"
        }
    except Exception as e:
        print(f"firewall exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
