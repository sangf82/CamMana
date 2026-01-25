import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PTZController:
    def __init__(self, connection_obj):
        # Expects a CameraConnection object (from connection.py)
        self.conn = connection_obj
        self._ptz_config = None
        self._ptz_node = None
        self._velocity_space = None
        self._position_space = None

    def _ensure_ptz(self) -> bool:
        return self.conn.connected and self.conn.ptz_service is not None

    def _get_ptz_configuration(self):
        """Get PTZ configuration and node for the current profile."""
        if self._ptz_config:
            return self._ptz_config
        
        try:
            # Get PTZ configuration
            configs = self.conn.ptz_service.GetConfigurations()
            if configs:
                self._ptz_config = configs[0]
                logger.info(f"PTZ Config: {self._ptz_config.Name if hasattr(self._ptz_config, 'Name') else 'Unknown'}")
                
                # Get PTZ Node to find supported spaces
                if hasattr(self._ptz_config, 'NodeToken'):
                    try:
                        self._ptz_node = self.conn.ptz_service.GetNode({'NodeToken': self._ptz_config.NodeToken})
                        if self._ptz_node:
                            # Extract supported spaces
                            if hasattr(self._ptz_node, 'SupportedPTZSpaces'):
                                spaces = self._ptz_node.SupportedPTZSpaces
                                # Get velocity space for ContinuousMove
                                if hasattr(spaces, 'ContinuousPanTiltVelocitySpace') and spaces.ContinuousPanTiltVelocitySpace:
                                    self._velocity_space = spaces.ContinuousPanTiltVelocitySpace[0].URI
                                    logger.info(f"Velocity Space: {self._velocity_space}")
                                # Get relative space
                                if hasattr(spaces, 'RelativePanTiltTranslationSpace') and spaces.RelativePanTiltTranslationSpace:
                                    self._position_space = spaces.RelativePanTiltTranslationSpace[0].URI
                                    logger.info(f"Position Space: {self._position_space}")
                    except Exception as e:
                        logger.warning(f"Could not get PTZ node: {e}")
                
                return self._ptz_config
        except Exception as e:
            logger.warning(f"Could not get PTZ configuration: {e}")
        return None

    def move(self, pan: float = 0, tilt: float = 0, zoom: float = 0, duration: float = 0.5) -> Dict[str, Any]:
        if not self._ensure_ptz():
             return {"success": False, "error": "PTZ not available"}
        
        # Get configuration first
        self._get_ptz_configuration()
        
        # Try multiple methods in order of compatibility
        methods = [
            self._try_continuous_move_simple,
            self._try_relative_move,
            self._try_continuous_move_with_space,
        ]
        
        for method in methods:
            result = method(pan, tilt, zoom, duration)
            if result.get("success"):
                return result
            logger.debug(f"{method.__name__} failed, trying next...")
        
        return {"success": False, "error": "All PTZ methods failed for this camera"}

    def _try_continuous_move_simple(self, pan: float, tilt: float, zoom: float, duration: float) -> Dict[str, Any]:
        """Try simple ContinuousMove without spaces (works for some cameras)."""
        try:
            # Simple request without namespace/space specifications
            self.conn.ptz_service.ContinuousMove({
                'ProfileToken': self.conn.profile_token,
                'Velocity': {
                    'PanTilt': {'x': pan * 0.5, 'y': tilt * 0.5},
                    'Zoom': {'x': zoom * 0.5}
                }
            })
            time.sleep(duration)
            self.stop()
            return {"success": True}
        except Exception as e:
            logger.debug(f"Simple ContinuousMove failed: {e}")
            return {"success": False, "error": str(e)}

    def _try_continuous_move_with_space(self, pan: float, tilt: float, zoom: float, duration: float) -> Dict[str, Any]:
        """Try ContinuousMove with explicit space URIs."""
        try:
            velocity = {'x': pan * 0.5, 'y': tilt * 0.5}
            if self._velocity_space:
                velocity['space'] = self._velocity_space
            
            self.conn.ptz_service.ContinuousMove({
                'ProfileToken': self.conn.profile_token,
                'Velocity': {
                    'PanTilt': velocity,
                    'Zoom': {'x': zoom * 0.5}
                }
            })
            time.sleep(duration)
            self.stop()
            return {"success": True}
        except Exception as e:
            logger.debug(f"ContinuousMove with space failed: {e}")
            return {"success": False, "error": str(e)}

    def _try_relative_move(self, pan: float, tilt: float, zoom: float, duration: float) -> Dict[str, Any]:
        """Try RelativeMove (more compatible with some cameras)."""
        try:
            scale = 0.05  # Small step for relative move
            translation = {'x': pan * scale, 'y': tilt * scale}
            if self._position_space:
                translation['space'] = self._position_space
            
            self.conn.ptz_service.RelativeMove({
                'ProfileToken': self.conn.profile_token,
                'Translation': {
                    'PanTilt': translation,
                    'Zoom': {'x': zoom * scale}
                }
            })
            time.sleep(duration)
            return {"success": True}
        except Exception as e:
            logger.debug(f"RelativeMove failed: {e}")
            return {"success": False, "error": str(e)}

    def stop(self) -> Dict[str, Any]:
        if not self._ensure_ptz():
             return {"success": False, "error": "PTZ not available"}
        try:
            self.conn.ptz_service.Stop({
                'ProfileToken': self.conn.profile_token,
                'PanTilt': True,
                'Zoom': True
            })
            return {"success": True}
        except Exception as e:
            logger.error(f"PTZ stop error: {e}")
            return {"success": False, "error": str(e)}

    def goto_preset(self, preset_token: str, speed: float = 0.5) -> Dict[str, Any]:
        """Go to a preset position."""
        if not self._ensure_ptz():
             return {"success": False, "error": "PTZ not available"}
        try:
            self.conn.ptz_service.GotoPreset({
                'ProfileToken': self.conn.profile_token,
                'PresetToken': preset_token,
                'Speed': {'PanTilt': {'x': speed, 'y': speed}, 'Zoom': {'x': speed}}
            })
            return {"success": True}
        except Exception as e:
            logger.error(f"GotoPreset error: {e}")
            return {"success": False, "error": str(e)}

    def get_presets(self) -> Dict[str, Any]:
        """Get available presets."""
        if not self._ensure_ptz():
             return {"success": False, "error": "PTZ not available", "presets": []}
        try:
            presets = self.conn.ptz_service.GetPresets({'ProfileToken': self.conn.profile_token})
            preset_list = [{'token': p.token, 'name': p.Name} for p in presets] if presets else []
            return {"success": True, "presets": preset_list}
        except Exception as e:
            logger.error(f"GetPresets error: {e}")
            return {"success": False, "error": str(e), "presets": []}
