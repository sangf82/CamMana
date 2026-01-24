import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PTZController:
    def __init__(self, connection_obj):
        # Expects a CameraConnection object (from connection.py)
        self.conn = connection_obj

    def _ensure_ptz(self) -> bool:
        return self.conn.connected and self.conn.ptz_service is not None

    def move(self, pan: float = 0, tilt: float = 0, zoom: float = 0, duration: float = 0.3) -> Dict[str, Any]:
        if not self._ensure_ptz():
             return {"success": False, "error": "PTZ not available"}
        
        try:
            req = self.conn.ptz_service.create_type('ContinuousMove')
            req.ProfileToken = self.conn.profile_token
            req.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': zoom}}
            
            self.conn.ptz_service.ContinuousMove(req)
            time.sleep(duration)
            self.conn.ptz_service.Stop({'ProfileToken': self.conn.profile_token, 'PanTilt': True, 'Zoom': True})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self) -> Dict[str, Any]:
        if not self._ensure_ptz():
             return {"success": False, "error": "PTZ not available"}
        try:
            self.conn.ptz_service.Stop({'ProfileToken': self.conn.profile_token, 'PanTilt': True, 'Zoom': True})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
