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
    # Try to get detailed CPU name
    cpu_name = platform.processor()  # Fallback
    network_category = "Unknown"
    
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            winreg.CloseKey(key)
        except:
            pass
            
        try:
            # Check network profile (Private/Public) via PowerShell
            ps_cmd = 'Get-NetConnectionProfile | Select-Object -ExpandProperty NetworkCategory'
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
            network_category = result.stdout.strip()
        except:
            pass
            
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_name = line.split(":")[1].strip()
                        break
        except:
            pass
    
    return {
        "pc_name": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "processor": cpu_name,
        "cpu_count": psutil.cpu_count(logical=True),
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "ip_address": get_lan_ip(),
        "network_category": network_category
    }


@system_router.get("/firewall/status")
def check_firewall_status():
    """Detailed check of network accessibility status (Windows only)."""
    if platform.system() != "Windows":
        return {"supported": False, "message": "Firewall management only supported on Windows"}
    
    try:
        # 1. Check TCP rule
        tcp_result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={FIREWALL_RULE_NAME}"],
            capture_output=True, text=True, timeout=5
        )
        tcp_exists = "Rule Name:" in tcp_result.stdout
        
        # 2. Check ICMP (Ping) rule
        icmp_result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=CamMana Ping"],
            capture_output=True, text=True, timeout=5
        )
        icmp_exists = "Rule Name:" in icmp_result.stdout
        
        # 3. Check Network Profile (check all adapters, prefer the non-Public one)
        ps_profile = 'Get-NetConnectionProfile | Select-Object -ExpandProperty NetworkCategory'
        profile_result = subprocess.run(["powershell", "-Command", ps_profile], capture_output=True, text=True, timeout=5)
        categories = [c.strip() for c in profile_result.stdout.strip().split('\n') if c.strip()]
        # Prefer Private > DomainAuthenticated > Public > Unknown
        if 'Private' in categories:
            network_category = 'Private'
        elif 'DomainAuthenticated' in categories:
            network_category = 'DomainAuthenticated'
        elif 'Public' in categories:
            network_category = 'Public'
        elif categories:
            network_category = categories[0]
        else:
            network_category = 'Unknown'

        return {
            "supported": True,
            "tcp_rule": tcp_exists,
            "icmp_rule": icmp_exists,
            "network_category": network_category,
            "rule_exists": tcp_exists, # legacy support
            "message": "Hệ thống đã sẵn sàng" if (tcp_exists and network_category == "Private") else "Cần cấu hình hạ tầng"
        }
    except Exception as e:
        return {
            "supported": True,
            "error": str(e),
            "message": "CORE: System Exception"
        }


@system_router.post("/firewall/open")
def open_firewall():
    """
    Perform a 'Deep Clean' and re-open firewall ports + set profile to Private.
    Requires admin privileges - will prompt UAC dialog.
    """
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="Only supported on Windows")
    
    try:
        port = settings.port
        
        # PowerShell block for Deep Clean and Refresh
        ps_script = f"""
        # 1. Remove any stale rules
        Remove-NetFirewallRule -DisplayName '{FIREWALL_RULE_NAME}' -ErrorAction SilentlyContinue
        Remove-NetFirewallRule -DisplayName 'CamMana Ping' -ErrorAction SilentlyContinue
        
        # 2. Add fresh TCP Port 8000 rule
        New-NetFirewallRule -DisplayName '{FIREWALL_RULE_NAME}' -Direction Inbound -LocalPort {port} -Protocol TCP -Action Allow -Profile Any
        
        # 3. Add ICMP (Ping) rule
        New-NetFirewallRule -DisplayName 'CamMana Ping' -Direction Inbound -Protocol ICMPv4 -Action Allow -Profile Any
        
        # 4. Set Network Profile to Private (for ALL adapters)
        Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue
        """
        
        # Wrap in Start-Process for elevation
        wrapped_cmd = f'Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command {ps_script}" -Verb RunAs -Wait -WindowStyle Hidden'
        
        print(f"Executing Deep Network Fix: {wrapped_cmd}")
        
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", wrapped_cmd],
            timeout=60
        )
        
        # Final Verification
        final_check = check_firewall_status()
        if final_check.get("tcp_rule"):
            return {
                "success": True,
                "message": f"Đã cấu hình hạ tầng mạng thành công. Profile: {final_check.get('network_category')}",
                "details": final_check
            }
        else:
            return {
                "success": False,
                "message": "Không thể cấu hình. Vui lòng đảm bảo bạn đã nhấn 'Yes' trên cửa sổ Admin.",
                "hint": "Nếu bạn dùng Antivirus thứ 3 (BKAV, McAfee, v.v.), hãy tắt nó tạm thời hoặc thêm Port 8000 vào vùng tin cậy."
            }
            
    except Exception as e:
        print(f"firewall exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
