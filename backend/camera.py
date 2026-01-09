"""
ONVIF Camera Manager - Handles camera connection and PTZ controls
"""

import time
from typing import Optional
from dataclasses import dataclass
from onvif import ONVIFCamera


@dataclass
class CameraConfig:
    ip: str = "192.168.5.159"
    port: int = 8899
    user: str = "admin"
    password: str = ""


class ONVIFCameraManager:
    """Manages ONVIF camera connection and PTZ controls"""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.camera: Optional[ONVIFCamera] = None
        self.ptz_service = None
        self.media_service = None
        self.profile_token: Optional[str] = None
        self.stream_uri: Optional[str] = None
        self.connected = False
        
    def connect(self) -> dict:
        """Connect to ONVIF camera and initialize services with retry logic and time sync"""
        import datetime
        
        # Ports to try: Configured port first, then common ONVIF ports
        ports_to_try = [self.config.port]
        common_ports = [80, 8000, 8080, 8899]
        for p in common_ports:
            if p not in ports_to_try:
                ports_to_try.append(p)
                
        last_error = None
        
        for port in ports_to_try:
            try:
                # 1. Attempt Connection
                self.camera = ONVIFCamera(
                    self.config.ip, 
                    port, 
                    self.config.user, 
                    self.config.password
                )
                
                # Verify connection by creating a service (e.g., DeviceMgmt)
                # This ensures we are actually talking to the device
                self.devicemgmt = self.camera.create_devicemgmt_service()
                
                # If we are here, connection is successful
                # Update config with the working port
                self.config.port = port
                break
            except Exception as e:
                last_error = e
                self.camera = None
                continue
                
        if not self.camera:
            self.connected = False
            return {"success": False, "error": f"Connection failed on ports {ports_to_try}. Last error: {str(last_error)}"}

        try:
            # 2. Time Synchronization
            # Many cameras reject auth if time is skewed. We attempt to sync camera time to PC time.
            try:
                # Get camera time
                # cam_time = self.devicemgmt.GetSystemDateAndTime()
                # print(f"Camera Time: {cam_time}")
                
                # Set manual time to now (UTC)
                now = datetime.datetime.utcnow()
                dt_param = {
                    'DateTimeType': 'Manual',
                    'DaylightSavings': False,
                    'TimeZone': {
                        'TZ': 'GMT0' # Simple UTC
                    },
                    'UTCDateTime': {
                        'Time': {
                            'Hour': now.hour,
                            'Minute': now.minute,
                            'Second': now.second
                        },
                        'Date': {
                            'Year': now.year,
                            'Month': now.month,
                            'Day': now.day
                        }
                    }
                }
                self.devicemgmt.SetSystemDateAndTime(dt_param)
            except Exception as e:
                print(f"Time sync warning (non-fatal): {e}")

            
            # 3. Get Media Profiles (Dynamic)
            self.media_service = self.camera.create_media_service()
            profiles = self.media_service.GetProfiles()
            
            if not profiles:
                return {"success": False, "error": "No media profiles found"}
            
            # Find best profile (highest resolution)
            best_profile = None
            max_res = 0
            best_uri = None
            resolution = {"width": 0, "height": 0}
            
            for p in profiles:
                token = p.token
                
                try:
                    if p.VideoEncoderConfiguration:
                        w = p.VideoEncoderConfiguration.Resolution.Width
                        h = p.VideoEncoderConfiguration.Resolution.Height
                    else:
                        w, h = 0, 0
                except:
                    w, h = 0, 0
                
                # Get stream URI for this profile
                try:
                    obj = self.media_service.create_type('GetStreamUri')
                    obj.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                    obj.ProfileToken = token
                    res = self.media_service.GetStreamUri(obj)
                    uri = res.Uri
                    
                    # Inject credentials into RTSP URL if needed
                    # Some cameras result in http://.../rtsp, we want the RTSP URI usually
                    if self.config.user and "@" not in uri:
                        # Handle standard rtsp:// protocol
                        if uri.startswith("rtsp://"):
                            uri = uri.replace(
                                "rtsp://", 
                                f"rtsp://{self.config.user}:{self.config.password}@", 
                                1
                            )
                except:
                    uri = None
                
                if uri and (w * h) >= max_res: # Use >= to pick last if multiple same res (often newer/better)
                    max_res = w * h
                    best_profile = p
                    best_uri = uri
                    resolution = {"width": w, "height": h}
            
            if best_profile:
                self.profile_token = best_profile.token
                self.stream_uri = best_uri
            else:
                return {"success": False, "error": "Could not find suitable video profile"}
            
            # Get PTZ service
            try:
                self.ptz_service = self.camera.create_ptz_service()
            except Exception as e:
                self.ptz_service = None
            
            self.connected = True
            return {
                "success": True,
                "stream_uri": self.stream_uri,
                "resolution": resolution,
                "profile": best_profile.Name,
                "ptz_available": self.ptz_service is not None,
                "active_port": self.config.port
            }
            
        except Exception as e:
            self.connected = False
            return {"success": False, "error": str(e)}
    
    def disconnect(self) -> dict:
        """Disconnect from camera"""
        self.camera = None
        self.ptz_service = None
        self.media_service = None
        self.profile_token = None
        self.stream_uri = None
        self.connected = False
        return {"success": True}
    
    def get_stream_uri(self) -> Optional[str]:
        """Get RTSP stream URI"""
        return self.stream_uri
    
    def ptz_move(self, pan: float = 0, tilt: float = 0, zoom: float = 0, duration: float = 0.3) -> dict:
        """
        Move camera using continuous movement
        pan: -1.0 (left) to 1.0 (right)
        tilt: -1.0 (down) to 1.0 (up)
        zoom: -1.0 (out) to 1.0 (in)
        """
        if not self.ptz_service:
            return {"success": False, "error": "PTZ not available"}
            
        try:
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = self.profile_token
            request.Velocity = {
                'PanTilt': {'x': pan, 'y': tilt},
                'Zoom': {'x': zoom}
            }
            self.ptz_service.ContinuousMove(request)
            time.sleep(duration)
            self.ptz_service.Stop({
                'ProfileToken': self.profile_token, 
                'PanTilt': True, 
                'Zoom': True
            })
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def ptz_stop(self) -> dict:
        """Stop all PTZ movement"""
        if not self.ptz_service:
            return {"success": False, "error": "PTZ not available"}
        try:
            self.ptz_service.Stop({
                'ProfileToken': self.profile_token, 
                'PanTilt': True, 
                'Zoom': True
            })
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_up(self, speed: float = 0.5) -> dict:
        return self.ptz_move(tilt=speed)
    
    def move_down(self, speed: float = 0.5) -> dict:
        return self.ptz_move(tilt=-speed)
    
    def move_left(self, speed: float = 0.5) -> dict:
        return self.ptz_move(pan=-speed)
    
    def move_right(self, speed: float = 0.5) -> dict:
        return self.ptz_move(pan=speed)
    
    def zoom_in(self, speed: float = 0.5) -> dict:
        return self.ptz_move(zoom=speed)
    
    def zoom_out(self, speed: float = 0.5) -> dict:
        return self.ptz_move(zoom=-speed)
