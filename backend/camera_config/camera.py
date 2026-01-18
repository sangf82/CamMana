"""ONVIF Camera Manager - Handles camera connection and PTZ controls"""
import time
import datetime
from typing import Optional
from dataclasses import dataclass
from onvif import ONVIFCamera
from backend import config

@dataclass
class CameraConfig:
    ip: str = "192.168.5.159"
    port: int = 8899
    user: str = config.CAMERA_DEFAULT_USER
    password: str = config.CAMERA_DEFAULT_PASSWORD
    name: str = "Camera"
    tag: Optional[str] = None

class ONVIFCameraManager:
    def __init__(self, config: CameraConfig):
        self.config = config
        self.camera: Optional[ONVIFCamera] = None
        self.ptz_service = None
        self.media_service = None
        self.profile_token: Optional[str] = None
        self.stream_uri: Optional[str] = None
        self.connected = False
        
    def connect(self) -> dict:
        ports_to_try = [self.config.port] + [p for p in [80, 8000, 8080, 8899] if p != self.config.port]
        last_error = None
        
        for port in ports_to_try:
            try:
                self.camera = ONVIFCamera(self.config.ip, port, self.config.user, self.config.password)
                self.devicemgmt = self.camera.create_devicemgmt_service()
                self.config.port = port
                break
            except Exception as e:
                last_error = e
                self.camera = None
                
        if not self.camera:
            self.connected = False
            return {"success": False, "error": f"Connection failed: {str(last_error)}"}

        try:
            # Time sync
            try:
                now = datetime.datetime.utcnow()
                self.devicemgmt.SetSystemDateAndTime({
                    'DateTimeType': 'Manual', 'DaylightSavings': False, 'TimeZone': {'TZ': 'GMT0'},
                    'UTCDateTime': {'Time': {'Hour': now.hour, 'Minute': now.minute, 'Second': now.second},
                                   'Date': {'Year': now.year, 'Month': now.month, 'Day': now.day}}
                })
            except: pass
            
            self.media_service = self.camera.create_media_service()
            profiles = self.media_service.GetProfiles()
            if not profiles:
                return {"success": False, "error": "No media profiles found"}
            
            # Find highest resolution profile
            best_profile, max_res, best_uri = None, 0, None
            resolution = {"width": 0, "height": 0}
            
            for p in profiles:
                try:
                    w = p.VideoEncoderConfiguration.Resolution.Width if p.VideoEncoderConfiguration else 0
                    h = p.VideoEncoderConfiguration.Resolution.Height if p.VideoEncoderConfiguration else 0
                except: w, h = 0, 0
                
                try:
                    obj = self.media_service.create_type('GetStreamUri')
                    obj.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                    obj.ProfileToken = p.token
                    uri = self.media_service.GetStreamUri(obj).Uri
                    if self.config.user and "@" not in uri and uri.startswith("rtsp://"):
                        uri = uri.replace("rtsp://", f"rtsp://{self.config.user}:{self.config.password}@", 1)
                except: uri = None
                
                if uri and (w * h) >= max_res:
                    max_res, best_profile, best_uri = w * h, p, uri
                    resolution = {"width": w, "height": h}
            
            if not best_profile:
                return {"success": False, "error": "Could not find suitable video profile"}
            
            self.profile_token = best_profile.token
            self.stream_uri = best_uri
            
            # Try to set 30 FPS
            try:
                if best_profile.VideoEncoderConfiguration:
                    enc = best_profile.VideoEncoderConfiguration
                    if hasattr(enc, 'RateControl') and enc.RateControl.FrameRateLimit < 30:
                        enc.RateControl.FrameRateLimit = 30
                        self.media_service.SetVideoEncoderConfiguration({'Configuration': enc, 'ForcePersistence': True})
            except: pass
            
            try: self.ptz_service = self.camera.create_ptz_service()
            except: self.ptz_service = None
            
            self.connected = True
            return {"success": True, "stream_uri": self.stream_uri, "resolution": resolution,
                    "profile": best_profile.Name, "ptz_available": self.ptz_service is not None, "active_port": self.config.port}
        except Exception as e:
            self.connected = False
            return {"success": False, "error": str(e)}
    
    def disconnect(self) -> dict:
        self.camera = self.ptz_service = self.media_service = None
        self.profile_token = self.stream_uri = None
        self.connected = False
        return {"success": True}
    
    def get_stream_uri(self) -> Optional[str]:
        return self.stream_uri
    
    def ptz_move(self, pan: float = 0, tilt: float = 0, zoom: float = 0, duration: float = 0.3) -> dict:
        if not self.ptz_service:
            return {"success": False, "error": "PTZ not available"}
        try:
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = self.profile_token
            request.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': zoom}}
            self.ptz_service.ContinuousMove(request)
            time.sleep(duration)
            self.ptz_service.Stop({'ProfileToken': self.profile_token, 'PanTilt': True, 'Zoom': True})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def ptz_stop(self) -> dict:
        if not self.ptz_service:
            return {"success": False, "error": "PTZ not available"}
        try:
            self.ptz_service.Stop({'ProfileToken': self.profile_token, 'PanTilt': True, 'Zoom': True})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_up(self, speed: float = 0.5) -> dict: return self.ptz_move(tilt=speed)
    def move_down(self, speed: float = 0.5) -> dict: return self.ptz_move(tilt=-speed)
    def move_left(self, speed: float = 0.5) -> dict: return self.ptz_move(pan=-speed)
    def move_right(self, speed: float = 0.5) -> dict: return self.ptz_move(pan=speed)
    def zoom_in(self, speed: float = 0.5) -> dict: return self.ptz_move(zoom=speed)
    def zoom_out(self, speed: float = 0.5) -> dict: return self.ptz_move(zoom=-speed)
