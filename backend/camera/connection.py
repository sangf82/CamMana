import datetime
from typing import Optional, Dict, Any
from onvif import ONVIFCamera
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CameraConnectionConfig:
    ip: str
    port: int # Legacy/Default port
    user: str
    password: str
    onvif_port: Optional[int] = None
    rtsp_port: int = 554
    transport_mode: str = "tcp"
    channel_id: Optional[int] = None
    stream_type: str = "main"

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
        self.model = "Unknown"

    def connect(self) -> Dict[str, Any]:
        # 1. Determine Port Sequence
        if self.config.onvif_port:
            ports_to_try = [self.config.onvif_port]
            mode = "Manual (Advanced)"
        else:
            ports_to_try = [self.config.port] + [p for p in [80, 8000, 8080, 8899] if p != self.config.port]
            mode = "Auto-detect"
            
        last_error = "Unknown error"
        
        # 2. Device Management Connection
        for port in ports_to_try:
            try:
                logger.info(f"Connecting to {self.config.ip}:{port} ({mode})")
                self.camera = ONVIFCamera(self.config.ip, port, self.config.user, self.config.password)
                self.camera.create_devicemgmt_service()
                
                # Fetch Device Info
                try:
                    info = self.camera.devicemgmt.GetDeviceInformation()
                    self.model = f"{info.Manufacturer} {info.Model}"
                except: pass
                
                self.config.onvif_port = port
                break
            except Exception as e:
                last_error = str(e)
                self.camera = None
        
        if not self.camera:
            self.connected = False
            return {
                "success": False, 
                "error": f"Connection failed on {mode} mode. Last error: {last_error}",
                "mode": mode
            }

        try:
            # 3. Media Service & Profile Extraction
            self.media_service = self.camera.create_media_service()
            profiles = self.media_service.GetProfiles()
            if not profiles:
                 return {"success": False, "error": "Handshake successful but no media profiles found."}
            
            # 4. Stream URI Selection (NVR/Direct + Main/Sub)
            # NVR Logic: If channel_id is provided, look for specific profiles or append channel param
            # For now, we search for the best match based on stream_type (main/sub)
            
            selected_profile = None
            if self.config.stream_type == "main":
                # Find Highest Resolution
                max_res = 0
                for p in profiles:
                    try:
                        res = p.VideoEncoderConfiguration.Resolution
                        if (res.Width * res.Height) >= max_res:
                            max_res = res.Width * res.Height
                            selected_profile = p
                    except: pass
            else:
                # Find Substream (Lowest Resolution)
                min_res = float('inf')
                for p in profiles:
                    try:
                        res = p.VideoEncoderConfiguration.Resolution
                        if (res.Width * res.Height) <= min_res:
                            min_res = res.Width * res.Height
                            selected_profile = p
                    except: pass
            
            # Fallback to first profile
            if not selected_profile:
                selected_profile = profiles[0]

            # 5. Get Stream URI
            obj = self.media_service.create_type('GetStreamUri')
            obj.StreamSetup = {
                'Stream': 'RTP-Unicast', 
                'Transport': {'Protocol': 'RTSP'}
            }
            obj.ProfileToken = selected_profile.token
            
            try:
                uri = self.media_service.GetStreamUri(obj).Uri
            except Exception as e:
                return {"success": False, "error": f"Failed to get Stream URI: {str(e)}"}
            
            # Inject Credentials into URI
            if self.config.user and "@" not in uri and uri.startswith("rtsp://"):
                uri = uri.replace("rtsp://", f"rtsp://{self.config.user}:{self.config.password}@", 1)

            # NVR Channel Adjustment
            if self.config.channel_id is not None:
                # Many NVRs use ?channel=X or similar
                if "?" in uri:
                    uri += f"&channel={self.config.channel_id}"
                else:
                    uri += f"?channel={self.config.channel_id}"
                
                # Handle subtype for main/sub if not already in URI
                subtype = 0 if self.config.stream_type == "main" else 1
                if "subtype=" not in uri:
                    uri += f"&subtype={subtype}"

            self.stream_uri = uri
            self.profile_token = selected_profile.token
            
            try:
                res = selected_profile.VideoEncoderConfiguration.Resolution
                self.resolution = {"width": res.Width, "height": res.Height}
            except: pass
            
            # 6. PTZ Service
            try:
                self.ptz_service = self.camera.create_ptz_service()
            except: 
                self.ptz_service = None
                
            self.connected = True
            return {
                "success": True, 
                "stream_uri": self.stream_uri,
                "resolution": self.resolution,
                "model": self.model,
                "ptz_available": self.ptz_service is not None,
                "onvif_port": self.config.onvif_port,
                "mode": mode
            }

        except Exception as e:
            self.connected = False
            return {"success": False, "error": f"Post-connection error: {str(e)}"}

    def disconnect(self):
        self.camera = None
        self.media_service = None
        self.ptz_service = None
        self.connected = False
