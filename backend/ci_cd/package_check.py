"""
Package Check - Verify required packages are installed

Checks for all required dependencies and reports missing packages.
"""

import importlib
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Required packages with their import names
REQUIRED_PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("httpx", "httpx"),
    ("PIL", "pillow"),
    ("ultralytics", "ultralytics"),
    ("onnxruntime", "onnxruntime"),
    ("jose", "python-jose"),
    ("passlib", "passlib"),
    ("bcrypt", "bcrypt"),
    ("zeroconf", "zeroconf"),
    ("fpdf", "fpdf2"),
    ("PySide6", "PySide6"),
    ("onvif", "onvif-zeep"),
    ("dotenv", "python-dotenv"),
]


def check_packages() -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Check if all required packages are installed.
    
    Returns:
        Tuple of (all_ok, list of results)
    """
    results = []
    all_ok = True
    
    for import_name, package_name in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, "__version__", "unknown")
            results.append({
                "package": package_name,
                "import_name": import_name,
                "installed": True,
                "version": version
            })
        except ImportError:
            all_ok = False
            results.append({
                "package": package_name,
                "import_name": import_name,
                "installed": False,
                "version": None
            })
            logger.warning(f"Missing package: {package_name}")
    
    return all_ok, results


def install_missing_packages(missing: List[str]) -> bool:
    """
    Attempt to install missing packages.
    
    Args:
        missing: List of package names to install
        
    Returns:
        True if all installed successfully
    """
    import subprocess
    import sys
    
    for package in missing:
        try:
            logger.info(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                logger.error(f"Failed to install {package}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing {package}: {e}")
            return False
    
    return True


def run_package_check(auto_install: bool = False) -> Dict[str, Any]:
    """
    Run package check and optionally install missing packages.
    
    Args:
        auto_install: If True, attempt to install missing packages
        
    Returns:
        Check result dictionary
    """
    all_ok, results = check_packages()
    
    missing = [r["package"] for r in results if not r["installed"]]
    
    if missing and auto_install:
        logger.info(f"Attempting to install {len(missing)} missing packages...")
        install_ok = install_missing_packages(missing)
        if install_ok:
            # Re-check after install
            all_ok, results = check_packages()
            missing = [r["package"] for r in results if not r["installed"]]
    
    return {
        "check": "packages",
        "success": all_ok,
        "missing": missing,
        "details": results
    }
