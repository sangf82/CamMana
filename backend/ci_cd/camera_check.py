"""
Camera Check - Verify camera connectivity and streaming

Tests ONVIF connections and RTSP streams.
"""

import logging
import socket
from typing import Dict, Any, List, Optional

from backend.settings import settings

logger = logging.getLogger(__name__)


def check_network_port(ip: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a network port is reachable.
    
    Args:
        ip: IP address to check
        port: Port number
        timeout: Connection timeout in seconds
        
    Returns:
        True if port is open
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_onvif_camera(ip: str, port: int, username: str, password: str) -> Dict[str, Any]:
    """
    Test ONVIF connection to a camera.
    
    Args:
        ip: Camera IP address
        port: ONVIF port (usually 80 or 8899)
        username: Camera username
        password: Camera password
        
    Returns:
        Check result dictionary
    """
    result = {
        "ip": ip,
        "port": port,
        "network_reachable": False,
        "onvif_connected": False,
        "device_info": None,
        "stream_uri": None,
        "error": None,
    }
    
    # Check network connectivity
    result["network_reachable"] = check_network_port(ip, port)
    
    if not result["network_reachable"]:
        result["error"] = f"Cannot reach {ip}:{port}"
        return result
    
    try:
        from onvif import ONVIFCamera
        
        # Try ONVIF connection
        cam = ONVIFCamera(ip, port, username, password)
        
        # Get device info
        devicemgmt = cam.create_devicemgmt_service()
        device_info = devicemgmt.GetDeviceInformation()
        if device_info:
            result["device_info"] = {
                "manufacturer": getattr(device_info, "Manufacturer", "Unknown"),
                "model": getattr(device_info, "Model", "Unknown"),
                "firmware": getattr(device_info, "FirmwareVersion", "Unknown"),
            }
            result["onvif_connected"] = True
        
        # Try to get stream URI
        try:
            media = cam.create_media_service()
            profiles = media.GetProfiles()
            if profiles:
                stream_setup = {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}
                stream_uri = media.GetStreamUri({"StreamSetup": stream_setup, "ProfileToken": profiles[0].token})
                if stream_uri:
                    result["stream_uri"] = getattr(stream_uri, "Uri", None)
        except Exception as e:
            logger.debug(f"Could not get stream URI: {e}")
        
    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"ONVIF check failed for {ip}:{port}: {e}")
    
    return result


def run_camera_check(cameras: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Run camera connectivity checks.
    
    Args:
        cameras: List of camera configs to check. If None, loads from CSV.
        
    Returns:
        Check result dictionary
    """
    from backend.camera.logic import CameraLogic
    
    results = []
    
    if cameras is None:
        try:
            cam_logic = CameraLogic()
            cameras = cam_logic.get_cameras()
        except Exception as e:
            logger.error(f"Failed to load cameras: {e}")
            return {
                "check": "cameras",
                "success": False,
                "error": str(e),
                "details": []
            }
    
    for cam in cameras:
        ip = cam.get("ip")
        if not ip:
            continue
            
        port = int(cam.get("port", 80))
        username = cam.get("username", settings.camera_default_user)
        password = cam.get("password", settings.camera_default_password)
        
        result = check_onvif_camera(ip, port, username, password)
        result["name"] = cam.get("name", "Unknown")
        result["id"] = cam.get("id")
        results.append(result)
    
    # Overall success if at least one camera is connected (or no cameras configured)
    connected_count = sum(1 for r in results if r["onvif_connected"])
    
    return {
        "check": "cameras",
        "success": len(results) == 0 or connected_count > 0,
        "total_cameras": len(results),
        "connected": connected_count,
        "details": results
    }
