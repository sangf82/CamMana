"""
ONVIF Camera Streaming Application with PTZ Control
Streams video from Botslab Indoor 2E camera using Streamlit UI
"""

import os
import sys

# ========================================================================
# SUPPRESS FFMPEG STDERR LOGS (must be before cv2 import)
# ========================================================================
_original_stderr_fd = os.dup(2)
_devnull_fd = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull_fd, 2)
os.close(_devnull_fd)

os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;2048000"

import cv2

os.dup2(_original_stderr_fd, 2)
os.close(_original_stderr_fd)

import streamlit as st
import numpy as np
from PIL import Image
from datetime import datetime
from pathlib import Path
import time
from onvif import ONVIFCamera


# Camera configuration - FIXED: Use correct ONVIF port and credentials
CAMERA_IP = "192.168.100.197"
ONVIF_PORT = 8899  # Botslab uses port 8899 for ONVIF
CAMERA_USER = "admin"  # Default user for Botslab
CAMERA_PASS = ""  # Empty password
CAPTURED_IMG_DIR = Path("captured_img")


class SuppressStderr:
    """Context manager to suppress stderr output (for ffmpeg noise)"""
    def __enter__(self):
        self.devnull_fd = os.open(os.devnull, os.O_WRONLY)
        self.saved_fd = os.dup(2)
        os.dup2(self.devnull_fd, 2)
        return self

    def __exit__(self, *args):
        os.dup2(self.saved_fd, 2)
        os.close(self.saved_fd)
        os.close(self.devnull_fd)


class ONVIFCameraManager:
    """Manages ONVIF camera connection and PTZ controls"""
    
    def __init__(self, ip: str, port: int = 8899, user: str = "admin", password: str = ""):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.camera = None
        self.ptz_service = None
        self.media_service = None
        self.profile_token = None
        self.stream_uri = None
        
    def connect(self) -> bool:
        """Connect to ONVIF camera and initialize services"""
        try:
            # Connect to camera
            self.camera = ONVIFCamera(
                self.ip, 
                self.port, 
                self.user, 
                self.password
            )
            
            # Get media service and profiles
            self.media_service = self.camera.create_media_service()
            profiles = self.media_service.GetProfiles()
            
            if not profiles:
                st.error("No media profiles found on camera")
                return False
            
            # Find best profile (highest resolution)
            best_profile = None
            max_res = 0
            best_uri = None
            
            for p in profiles:
                token = p.token
                name = p.Name
                
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
                    if self.user and "@" not in uri:
                        uri = uri.replace("rtsp://", f"rtsp://{self.user}:{self.password}@", 1)
                except:
                    uri = None
                
                if uri and (w * h) > max_res:
                    max_res = w * h
                    best_profile = p
                    best_uri = uri
            
            if best_profile:
                self.profile_token = best_profile.token
                self.stream_uri = best_uri
                w = best_profile.VideoEncoderConfiguration.Resolution.Width
                h = best_profile.VideoEncoderConfiguration.Resolution.Height
                st.success(f"Selected profile: {best_profile.Name} ({w}x{h})")
            else:
                st.error("Could not find suitable video profile")
                return False
            
            # Get PTZ service
            try:
                self.ptz_service = self.camera.create_ptz_service()
            except Exception as e:
                st.warning(f"PTZ service not available: {e}")
                self.ptz_service = None
            
            return True
            
        except Exception as e:
            st.error(f"Failed to connect to camera: {e}")
            return False
    
    def get_stream_uri(self) -> str:
        """Get RTSP stream URI"""
        return self.stream_uri
    
    def ptz_move(self, pan: float = 0, tilt: float = 0, zoom: float = 0):
        """
        Move camera using continuous movement
        pan: -1.0 (left) to 1.0 (right)
        tilt: -1.0 (down) to 1.0 (up)
        zoom: -1.0 (out) to 1.0 (in)
        """
        if not self.ptz_service:
            return
            
        try:
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = self.profile_token
            request.Velocity = {
                'PanTilt': {'x': pan, 'y': tilt},
                'Zoom': {'x': zoom}
            }
            self.ptz_service.ContinuousMove(request)
            time.sleep(0.3)
            self.ptz_service.Stop({
                'ProfileToken': self.profile_token, 
                'PanTilt': True, 
                'Zoom': True
            })
        except Exception as e:
            st.error(f"PTZ error: {e}")
    
    def ptz_stop(self):
        """Stop all PTZ movement"""
        if not self.ptz_service:
            return
        try:
            self.ptz_service.Stop({
                'ProfileToken': self.profile_token, 
                'PanTilt': True, 
                'Zoom': True
            })
        except Exception:
            pass
    
    def zoom_in(self, speed: float = 0.5):
        """Zoom in"""
        self.ptz_move(zoom=speed)
    
    def zoom_out(self, speed: float = 0.5):
        """Zoom out"""
        self.ptz_move(zoom=-speed)
    
    def move_up(self, speed: float = 0.5):
        """Tilt up"""
        self.ptz_move(tilt=speed)
    
    def move_down(self, speed: float = 0.5):
        """Tilt down"""
        self.ptz_move(tilt=-speed)
    
    def move_left(self, speed: float = 0.5):
        """Pan left"""
        self.ptz_move(pan=-speed)
    
    def move_right(self, speed: float = 0.5):
        """Pan right"""
        self.ptz_move(pan=speed)


class VideoStreamer:
    """Handles RTSP video streaming using OpenCV with FFmpeg"""
    
    def __init__(self, rtsp_uri: str):
        self.rtsp_uri = rtsp_uri
        self.cap = None
        self.fail_count = 0
        self.max_fails = 30
        
    def start(self) -> bool:
        """Start video capture with optimized settings"""
        if self.cap is not None:
            self.cap.release()
        
        with SuppressStderr():
            self.cap = cv2.VideoCapture(self.rtsp_uri, cv2.CAP_FFMPEG)
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            # Read initial frames to stabilize stream
            for _ in range(10):
                self.cap.read()
        
        return self.cap.isOpened()
    
    def read_frame(self):
        """Read a frame from the stream with reconnection logic"""
        if self.cap is None or not self.cap.isOpened():
            return None
        
        with SuppressStderr():
            ret, frame = self.cap.read()
        
        if not ret:
            self.fail_count += 1
            if self.fail_count >= self.max_fails:
                # Attempt reconnection
                self.cap.release()
                time.sleep(0.5)
                self.start()
                self.fail_count = 0
            return None
        
        self.fail_count = 0
        # Convert BGR to RGB for Streamlit
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    def get_frame_size(self):
        """Get current frame size"""
        if self.cap:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return width, height
        return None, None
    
    def stop(self):
        """Stop video capture"""
        if self.cap:
            self.cap.release()
            self.cap = None


def capture_image(frame: np.ndarray, save_dir: Path) -> str:
    """Save current frame as image"""
    save_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = save_dir / f"capture_{timestamp}.jpg"
    
    img = Image.fromarray(frame)
    img.save(filename, quality=95)
    
    return str(filename)


def init_session_state():
    """Initialize Streamlit session state"""
    if 'camera_manager' not in st.session_state:
        st.session_state.camera_manager = None
    if 'video_streamer' not in st.session_state:
        st.session_state.video_streamer = None
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    if 'streaming' not in st.session_state:
        st.session_state.streaming = False
    if 'last_frame' not in st.session_state:
        st.session_state.last_frame = None


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="ONVIF Camera Control",
        page_icon="📷",
        layout="wide"
    )
    
    init_session_state()
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .stButton > button {
            width: 100%;
            height: 50px;
            font-size: 20px;
        }
        div[data-testid="stHorizontalBlock"] > div {
            display: flex;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("📷 ONVIF Camera Streaming")
    st.markdown(f"**Camera:** `{CAMERA_IP}:{ONVIF_PORT}` (user: `{CAMERA_USER}`)")
    
    # Sidebar for controls
    with st.sidebar:
        st.header("🎮 Controls")
        
        # Connection controls
        st.subheader("Connection")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔌 Connect", use_container_width=True):
                with st.spinner("Connecting to camera..."):
                    camera_manager = ONVIFCameraManager(
                        CAMERA_IP, ONVIF_PORT, CAMERA_USER, CAMERA_PASS
                    )
                    if camera_manager.connect():
                        st.session_state.camera_manager = camera_manager
                        st.session_state.connected = True
                        
                        # Initialize video streamer
                        stream_uri = camera_manager.get_stream_uri()
                        st.session_state.video_streamer = VideoStreamer(stream_uri)
                        st.success("Connected!")
                        st.rerun()
                    else:
                        st.error("Connection failed!")
        
        with col2:
            if st.button("❌ Disconnect", use_container_width=True):
                if st.session_state.video_streamer:
                    st.session_state.video_streamer.stop()
                st.session_state.camera_manager = None
                st.session_state.video_streamer = None
                st.session_state.connected = False
                st.session_state.streaming = False
                st.rerun()
        
        # Stream controls
        if st.session_state.connected:
            st.divider()
            st.subheader("Stream")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Start", use_container_width=True):
                    if st.session_state.video_streamer.start():
                        st.session_state.streaming = True
                        st.rerun()
                    else:
                        st.error("Failed to start stream")
            
            with col2:
                if st.button("⏹️ Stop", use_container_width=True):
                    st.session_state.video_streamer.stop()
                    st.session_state.streaming = False
                    st.rerun()
            
            # PTZ Controls
            st.divider()
            st.subheader("🕹️ PTZ Control")
            
            camera_manager = st.session_state.camera_manager
            
            # Movement speed slider
            speed = st.slider("Movement Speed", 0.1, 1.0, 0.5, 0.1)
            
            # Directional controls (3x3 grid)
            col1, col2, col3 = st.columns(3)
            
            with col2:
                if st.button("⬆️", key="up", use_container_width=True):
                    camera_manager.move_up(speed)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⬅️", key="left", use_container_width=True):
                    camera_manager.move_left(speed)
            with col2:
                if st.button("⏹", key="stop", use_container_width=True):
                    camera_manager.ptz_stop()
            with col3:
                if st.button("➡️", key="right", use_container_width=True):
                    camera_manager.move_right(speed)
            
            col1, col2, col3 = st.columns(3)
            with col2:
                if st.button("⬇️", key="down", use_container_width=True):
                    camera_manager.move_down(speed)
            
            # Zoom controls
            st.divider()
            st.subheader("🔍 Zoom")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Zoom In", use_container_width=True):
                    camera_manager.zoom_in(speed)
            with col2:
                if st.button("🔎 Zoom Out", use_container_width=True):
                    camera_manager.zoom_out(speed)
            
            # Capture controls
            st.divider()
            st.subheader("📸 Capture")
            
            if st.button("📷 Capture Image", use_container_width=True):
                if st.session_state.last_frame is not None:
                    filename = capture_image(
                        st.session_state.last_frame, 
                        CAPTURED_IMG_DIR
                    )
                    st.success(f"Saved: {filename}")
                else:
                    st.warning("No frame available to capture")
    
    # Main video display area
    if st.session_state.connected:
        # Stream info
        if st.session_state.video_streamer:
            stream_uri = st.session_state.camera_manager.get_stream_uri()
            st.info(f"📡 Stream URI: `{stream_uri}`")
        
        # Video display
        if st.session_state.streaming:
            video_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Streaming loop
            while st.session_state.streaming:
                frame = st.session_state.video_streamer.read_frame()
                
                if frame is not None:
                    st.session_state.last_frame = frame
                    video_placeholder.image(
                        frame, 
                        channels="RGB",
                        use_container_width=True
                    )
                    
                    # Display frame info
                    width, height = st.session_state.video_streamer.get_frame_size()
                    status_placeholder.caption(
                        f"Resolution: {width}x{height} | "
                        f"Time: {datetime.now().strftime('%H:%M:%S')}"
                    )
                
                time.sleep(0.033)  # ~30 FPS
        else:
            st.info("👆 Click 'Start' in the sidebar to begin streaming")
    else:
        st.warning("📡 Click 'Connect' in the sidebar to connect to the camera")
        
        # Show connection instructions
        st.markdown("""
        ### Instructions
        1. Make sure the camera is powered on and connected to the network
        2. Verify the camera IP address is `192.168.100.197`
        3. Click **Connect** in the sidebar
        4. Once connected, click **Start** to begin streaming
        5. Use the **PTZ controls** to move and zoom the camera
        6. Click **Capture Image** to save the current frame
        """)


if __name__ == "__main__":
    main()
