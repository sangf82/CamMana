"""
CamMana Configuration Module

This module provides backwards-compatible access to configuration values.
All configuration is now centralized in settings.py using pydantic-settings.
"""
from backend.settings import settings, get_settings, Settings

# =============================================================================
# Path Exports (backwards compatibility)
# =============================================================================
BACKEND_DIR = settings.backend_dir
PROJECT_ROOT = settings.project_root
DATA_ROOT = settings.data_root
DATA_DIR = settings.data_dir
LOGS_DIR = settings.logs_dir

# Ensure directories exist on import
settings.ensure_directories()

# =============================================================================
# API Configuration (backwards compatibility)
# =============================================================================
HOST = settings.host
PORT = settings.port
API_TITLE = settings.api_title
API_VERSION = settings.api_version
API_DESCRIPTION = settings.api_description

# =============================================================================
# Camera Configuration (backwards compatibility)
# =============================================================================
CAMERA_DEFAULT_USER = settings.camera_default_user
CAMERA_DEFAULT_PASSWORD = settings.camera_default_password

# =============================================================================
# Debug/Development Mode
# =============================================================================
DEBUG = settings.debug

# =============================================================================
# Re-export Settings for direct use
# =============================================================================
__all__ = [
    'settings',
    'get_settings',
    'Settings',
    'BACKEND_DIR',
    'PROJECT_ROOT', 
    'DATA_ROOT',
    'DATA_DIR',
    'LOGS_DIR',
    'HOST',
    'PORT',
    'API_TITLE',
    'API_VERSION',
    'API_DESCRIPTION',
    'CAMERA_DEFAULT_USER',
    'CAMERA_DEFAULT_PASSWORD',
    'DEBUG',
]

