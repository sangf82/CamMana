import datetime
from typing import Optional, Dict, Any
from onvif import ONVIFCamera
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CameraConnectionConfig:
    ip: str
    port: int
    user: str
    password: str

class CameraConnection:
    def __init__(self, config: CameraConnectionConfig):
        self.config = config
        self.camera: Optional[ONVIFCamera] = None
        self.media_service = None
        self.ptz_service = None
        self.profile_token: Optional[str] = None
        self.stream_uri: Optional[str] = None
        self.connected = False
        self.resolution = {"width": 0, "height": 0}

    def connect(self) -> Dict[str, Any]:
        ports_to_try = [self.config.port] + [p for p in [80, 8000, 8080, 8899] if p != self.config.port]
        last_error = None
        
        # 1. Device Connection
        for port in ports_to_try:
            try:
                self.camera = ONVIFCamera(self.config.ip, port, self.config.user, self.config.password)
                self.config.port = port
                # Verify capabilities
                self.camera.create_devicemgmt_service()
                break
            except Exception as e:
                last_error = e
                self.camera = None
        
        if not self.camera:
            self.connected = False
            return {"success": False, "error": f"Connection failed: {str(last_error)}"}

        try:
            # 2. Media Service & Profile
            self.media_service = self.camera.create_media_service()
            profiles = self.media_service.GetProfiles()
            if not profiles:
                 return {"success": False, "error": "No media profiles found"}
            
            # Find Best Profile (Highest Res)
            best_profile = None
            max_res = 0
            best_uri = None
            
            for p in profiles:
                try:
                    res = p.VideoEncoderConfiguration.Resolution
                    w, h = res.Width, res.Height
                except: w, h = 0, 0
                
                # Get Stream URI
                try:
                    obj = self.media_service.create_type('GetStreamUri')
                    obj.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                    obj.ProfileToken = p.token
                    uri = self.media_service.GetStreamUri(obj).Uri
                    
                    # Inject Auth
                    if self.config.user and "@" not in uri and uri.startswith("rtsp://"):
                        uri = uri.replace("rtsp://", f"rtsp://{self.config.user}:{self.config.password}@", 1)
                except: uri = None
                
                if uri and (w * h) >= max_res:
                    max_res = w * h
                    best_profile = p
                    best_uri = uri
                    self.resolution = {"width": w, "height": h}
            
            if not best_profile:
                 return {"success": False, "error": "No suitable profile found"}

            self.profile_token = best_profile.token
            self.stream_uri = best_uri
            
            # 3. PTZ Service Check
            try:
                self.ptz_service = self.camera.create_ptz_service()
            except: 
                self.ptz_service = None
                
            self.connected = True
            return {
                "success": True, 
                "stream_uri": self.stream_uri,
                "resolution": self.resolution,
                "ptz_available": self.ptz_service is not None,
                "active_port": self.config.port
            }

        except Exception as e:
            self.connected = False
            return {"success": False, "error": str(e)}

    def disconnect(self):
        self.camera = None
        self.media_service = None
        self.ptz_service = None
        self.connected = False
