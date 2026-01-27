import platform
import psutil
import socket
import subprocess
import os
from fastapi import APIRouter, Depends, HTTPException
from backend.api.user import get_current_user
from backend.schemas import User

router = APIRouter(prefix="/api/system", tags=["System"])

FIREWALL_RULE_NAME = "CamMana Backend"

@router.get("/info")
def get_system_info():
    """Get system information - no auth required for sync discovery."""
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

@router.get("/firewall/status")
def check_firewall_status():
    """Check if firewall rule for CamMana exists (Windows only)."""
    if platform.system() != "Windows":
        return {"supported": False, "message": "Firewall management only supported on Windows"}
    
    try:
        # Check if the rule exists
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
            "message": "Đã có quy tắc tường lửa" if rule_exists else "Chưa có quy tắc tường lửa cho CamMana"
        }
    except Exception as e:
        return {
            "supported": True,
            "rule_exists": False,
            "error": str(e)
        }

@router.post("/firewall/open")
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
        # Create a PowerShell script to add the rule with elevation
        port = os.getenv("PORT", "8000")
        
        # PowerShell command to run elevated
        ps_command = f'''
        $rule = Get-NetFirewallRule -DisplayName "{FIREWALL_RULE_NAME}" -ErrorAction SilentlyContinue
        if (-not $rule) {{
            New-NetFirewallRule -DisplayName "{FIREWALL_RULE_NAME}" -Direction Inbound -Protocol TCP -LocalPort {port} -Action Allow -Profile Any
            Write-Output "SUCCESS: Firewall rule added"
        }} else {{
            Write-Output "EXISTS: Rule already exists"
        }}
        '''
        
        # Use Start-Process with -Verb RunAs to trigger UAC
        elevated_cmd = f'Start-Process powershell -ArgumentList \'-ExecutionPolicy Bypass -Command "{ps_command.replace(chr(10), " ")}"\'  -Verb RunAs -Wait'
        
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", elevated_cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        
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
                "message": "Không thể thêm quy tắc. Có thể bạn đã hủy yêu cầu UAC.",
                "hint": "Vui lòng chấp nhận yêu cầu quyền Admin khi được hỏi"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Hết thời gian chờ. Đã hủy yêu cầu?"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

