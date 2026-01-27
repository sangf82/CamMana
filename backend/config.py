import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Project Paths ---
BACKEND_DIR = Path(__file__).parent

# Determine if running as packaged exe or from source
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    APPLICATION_PATH = Path(sys.executable).parent
    PROJECT_ROOT = APPLICATION_PATH
else:
    # Running from source
    PROJECT_ROOT = BACKEND_DIR.parent

# Allow user to configure data directory via environment variable or use default
DATA_ROOT = os.getenv("CAMMANA_DATA_DIR", None)
if DATA_ROOT:
    DATA_ROOT = Path(DATA_ROOT)
    # Create data directory structure if it doesn't exist
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "csv_data").mkdir(exist_ok=True)
    (DATA_ROOT / "logs").mkdir(exist_ok=True)
    (DATA_ROOT / "car_history").mkdir(exist_ok=True)
    (DATA_ROOT / "backgrounds").mkdir(exist_ok=True)
    (DATA_ROOT / "calibration").mkdir(exist_ok=True)
    (DATA_ROOT / "captured_img").mkdir(exist_ok=True)
    (DATA_ROOT / "report").mkdir(exist_ok=True)
else:
    # Use default location next to executable or in project
    DATA_ROOT = PROJECT_ROOT / "database"
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

DATA_DIR = DATA_ROOT / "csv_data"
LOGS_DIR = DATA_ROOT / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# --- API Configuration ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
API_TITLE = os.getenv("API_TITLE", "cam_mana")
API_VERSION = os.getenv("API_VERSION", "2.0.0")
API_DESCRIPTION = "ONVIF Camera Control & Streaming API"

# --- Camera Configuration ---
CAMERA_DEFAULT_USER = os.getenv("CAMERA_DEFAULT_USER", "admin")
CAMERA_DEFAULT_PASSWORD = os.getenv("CAMERA_DEFAULT_PASSWORD", "")
