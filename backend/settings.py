"""
CamMana Settings Module

Centralized configuration using pydantic-settings for environment-based configuration
with validation and type safety.
"""
import os
import sys
from pathlib import Path
from typing import Optional
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ==========================================================================
    # Server Configuration
    # ==========================================================================
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode with hot-reload")
    
    # ==========================================================================
    # API Settings
    # ==========================================================================
    api_title: str = Field(default="cam_mana", description="API title")
    api_version: str = Field(default="2.0.0", description="API version")
    api_description: str = Field(
        default="ONVIF Camera Control & Streaming API",
        description="API description"
    )
    
    # ==========================================================================
    # Data Paths
    # ==========================================================================
    cammana_data_dir: Optional[str] = Field(
        default=None,
        description="Root directory for all data. If not set, uses ./database"
    )
    
    # ==========================================================================
    # Camera Defaults
    # ==========================================================================
    camera_default_user: str = Field(default="admin", description="Default camera username")
    camera_default_password: str = Field(default="", description="Default camera password")
    
    # ==========================================================================
    # External AI API
    # ==========================================================================
    ai_api_url: str = Field(
        default="https://thpttl12t1--truck-api-fastapi-app.modal.run",
        description="Modal.run API endpoint for AI functions"
    )
    
    # ==========================================================================
    # Authentication
    # ==========================================================================
    jwt_secret_key: str = Field(
        default="cammana-dev-secret-key-change-in-production",
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=1440,
        description="JWT token expiration in minutes (default 24 hours)"
    )
    
    # ==========================================================================
    # Sync Settings
    # ==========================================================================
    sync_auto_advertise: bool = Field(
        default=True,
        description="Auto-start Zeroconf advertising in Master mode"
    )
    
    # ==========================================================================
    # Computed Paths (not from environment)
    # ==========================================================================
    @property
    def backend_dir(self) -> Path:
        """Path to backend directory."""
        return Path(__file__).parent
    
    @property
    def project_root(self) -> Path:
        """Path to project root directory."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return Path(sys.executable).parent
        return self.backend_dir.parent
    
    @property
    def data_root(self) -> Path:
        """Root directory for all data storage."""
        if self.cammana_data_dir:
            path = Path(self.cammana_data_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return self.project_root / "database"
    
    @property
    def data_dir(self) -> Path:
        """CSV data directory."""
        path = self.data_root / "csv_data"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def logs_dir(self) -> Path:
        """Logs directory."""
        path = self.data_root / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def car_history_dir(self) -> Path:
        """Car history images directory."""
        path = self.data_root / "car_history"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def backgrounds_dir(self) -> Path:
        """Background images directory."""
        path = self.data_root / "backgrounds"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def calibration_dir(self) -> Path:
        """Calibration data directory."""
        path = self.data_root / "calibration"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def captured_img_dir(self) -> Path:
        """Captured images directory."""
        path = self.data_root / "captured_img"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def report_dir(self) -> Path:
        """Reports directory."""
        path = self.data_root / "report"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def models_dir(self) -> Path:
        """AI models directory."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - models bundled in _MEIPASS
            return Path(sys._MEIPASS) / "backend" / "model_process" / "models"  # type: ignore[attr-defined]
        return self.backend_dir / "model_process" / "models"
    
    @property
    def sync_config_path(self) -> Path:
        """Sync configuration file path."""
        return self.data_root / "sync_config.json"
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        # Access all path properties to trigger mkdir
        _ = self.data_dir
        _ = self.logs_dir
        _ = self.car_history_dir
        _ = self.backgrounds_dir
        _ = self.calibration_dir
        _ = self.captured_img_dir
        _ = self.report_dir


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access for backwards compatibility
settings = get_settings()
