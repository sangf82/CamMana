"""
Logging Configuration for CamMana Application

Provides separate loggers for:
- App: Main application (GUI, process management)
- Backend: FastAPI server, API endpoints, workflow logic
- Frontend: Dev server output (development mode only)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Log directory
LOG_DIR = Path(__file__).parent.parent / "database" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Formatters
DETAILED_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
SIMPLE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def get_file_handler(log_name: str, detailed: bool = True) -> TimedRotatingFileHandler:
    """Create a rotating file handler for a specific log type."""
    log_file = LOG_DIR / f"{log_name}_{datetime.now().strftime('%Y-%m-%d')}.log"
    handler = TimedRotatingFileHandler(
        str(log_file), 
        when="midnight", 
        interval=1, 
        backupCount=30, 
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(DETAILED_FORMAT if detailed else SIMPLE_FORMAT))
    return handler


def get_console_handler(detailed: bool = False) -> logging.StreamHandler:
    """Create a console handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(SIMPLE_FORMAT if not detailed else DETAILED_FORMAT))
    return handler


def setup_app_logging():
    """Setup main application logger (used by app.py, GUI)."""
    logger = logging.getLogger("cammana")
    if logger.handlers:  # Already configured
        return logger
    
    logger.setLevel(logging.INFO)
    logger.addHandler(get_file_handler("app"))
    logger.addHandler(get_console_handler())
    logger.propagate = False
    return logger


def setup_backend_logging():
    """
    Setup backend logger for FastAPI, workflows, and data processing.
    This configures the root logger for the backend module.
    """
    # Backend root logger
    backend_logger = logging.getLogger("backend")
    if backend_logger.handlers:
        return backend_logger
    
    backend_logger.setLevel(logging.DEBUG)  # Capture all levels
    backend_logger.addHandler(get_file_handler("backend", detailed=True))
    backend_logger.addHandler(get_console_handler(detailed=True))
    backend_logger.propagate = False
    
    # Also configure uvicorn loggers to use our handler
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []  # Clear default handlers
        uv_logger.addHandler(get_file_handler("backend", detailed=True))
        uv_logger.addHandler(get_console_handler(detailed=False))
        uv_logger.propagate = False
    
    return backend_logger


def setup_frontend_logging():
    """Setup frontend logger for dev server output."""
    logger = logging.getLogger("frontend")
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_file_handler("frontend"))
    logger.addHandler(get_console_handler())
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger by name. Creates child logger of appropriate parent.
    
    Usage:
        from backend.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Message")
    """
    # Determine parent based on module path
    if name.startswith("backend"):
        parent = "backend"
    elif name.startswith("frontend"):
        parent = "frontend"
    else:
        parent = "cammana"
    
    # Ensure parent is configured
    if parent == "backend":
        setup_backend_logging()
    elif parent == "frontend":
        setup_frontend_logging()
    else:
        setup_app_logging()
    
    return logging.getLogger(name)


# Initialize on import
def init_all_loggers():
    """Initialize all loggers. Called once at application startup."""
    setup_app_logging()
    setup_backend_logging()
    setup_frontend_logging()
    
    # Log startup
    app_logger = logging.getLogger("cammana")
    app_logger.info("=" * 50)
    app_logger.info(f"CamMana Logging Initialized - {datetime.now()}")
    app_logger.info(f"Log Directory: {LOG_DIR}")
    app_logger.info("=" * 50)
