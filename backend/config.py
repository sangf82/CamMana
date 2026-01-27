import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Project Paths ---
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "database" / "csv_data"
LOGS_DIR = PROJECT_ROOT / "database" / "logs"

# --- API Configuration ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
API_TITLE = os.getenv("API_TITLE", "cam_mana")
API_VERSION = os.getenv("API_VERSION", "2.0.0")
API_DESCRIPTION = "ONVIF Camera Control & Streaming API"

# --- Camera Configuration ---
CAMERA_DEFAULT_USER = os.getenv("CAMERA_DEFAULT_USER", "admin")
CAMERA_DEFAULT_PASSWORD = os.getenv("CAMERA_DEFAULT_PASSWORD", "")
