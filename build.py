"""
Build script for CamMana Windows Application
Creates a standalone .exe file with all dependencies bundled
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path


def build():
    """Build the CamMana Windows application"""
    
    project_dir = Path(__file__).parent
    frontend_dir = project_dir / "frontend"
    out_dir = frontend_dir / "out"
    dist_dir = project_dir / "dist"
    models_dir = project_dir / "backend" / "model_process" / "models"
    
    print("=" * 60)
    print("🔨 Building CamMana Windows Application")
    print("=" * 60)
    
    # Step 0: Ensure PyInstaller is installed
    print("\n🔍 Step 0: Ensuring PyInstaller is available...")
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("❌ PyInstaller not found. Installing via uv...")
        result = subprocess.run(
            ["uv", "pip", "install", "pyinstaller>=6.0.0"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to install PyInstaller: {result.stderr}")
            print("\n💡 Try manually: uv pip install pyinstaller")
            sys.exit(1)
        print("✅ PyInstaller installed")
    
    # Step 1: Clean previous builds
    print("\n🧹 Step 1: Cleaning previous builds...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("✅ Cleaned dist directory")
    
    build_dir = project_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("✅ Cleaned build directory")
    
    spec_file = project_dir / "CamMana.spec"
    if spec_file.exists():
        spec_file.unlink()
        print("✅ Removed old spec file")
    
    # Step 2: Build Next.js frontend
    print("\n📦 Step 2: Building Next.js frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        shell=True
    )
    if result.returncode != 0:
        print("❌ Frontend build failed!")
        sys.exit(1)
    print("✅ Frontend built successfully!")
    
    # Verify out directory exists
    if not out_dir.exists():
        print(f"❌ Build output not found at {out_dir}")
        sys.exit(1)
    
    # Step 3: Package with PyInstaller
    print("\n📦 Step 3: Packaging with PyInstaller...")
    
    # Prepare add-data arguments
    add_data_args = [
        f"--add-data={out_dir};frontend/out",
    ]
    
    # Include models directory if exists (new location: backend/model_process/models)
    if models_dir.exists():
        add_data_args.append(f"--add-data={models_dir};backend/model_process/models")
    
    # Build with PyInstaller
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name=CamMana",
        "--onefile",
        "--windowed",
        "--icon=NONE",
        "--noconfirm",  # Overwrite without asking
        # Hidden imports for FastAPI/Uvicorn
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        # ONVIF dependencies
        "--collect-all=zeep",
        "--collect-all=onvif_zeep",
        # YOLO/Ultralytics
        "--hidden-import=ultralytics",
        "--collect-submodules=ultralytics",
        # ONNX Runtime
        "--hidden-import=onnxruntime",
        "--collect-submodules=onnxruntime",
        # APScheduler
        "--hidden-import=apscheduler.schedulers.asyncio",
        "--hidden-import=apscheduler.triggers.cron",
        # Zeroconf
        "--hidden-import=zeroconf",
        "--hidden-import=zeroconf._utils.ipaddress",
        # PySide6 for Qt GUI
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWebEngineWidgets",
        "--hidden-import=PySide6.QtWebEngineCore",
        # Optimize
        "--optimize=2",  # Highest optimization level
    ] + add_data_args + ["app.py"]
    
    result = subprocess.run(pyinstaller_args, cwd=project_dir, shell=True)
    
    if result.returncode != 0:
        print("❌ PyInstaller build failed!")
        sys.exit(1)
    
    # Step 4: Create distribution package
    print("\n📦 Step 4: Creating distribution package...")
    
    release_dir = dist_dir / "CamMana_Release"
    release_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy executable
    exe_path = dist_dir / "CamMana.exe"
    if exe_path.exists():
        shutil.copy2(exe_path, release_dir / "CamMana.exe")
        print(f"✅ Copied executable to {release_dir}")
    
    # Create README for users
    readme_content = """# CamMana - Vehicle Management System

## Installation

1. Extract all files to a folder of your choice
2. Run CamMana.exe

## Data Directory Configuration

By default, CamMana stores all data in a "database" folder next to the executable.

To use a custom data directory:
1. Create a file named ".env" in the same folder as CamMana.exe
2. Add this line: CAMMANA_DATA_DIR=C:\\Path\\To\\Your\\Data
3. The application will create all necessary folders automatically

## First Time Setup

1. Configure your cameras in the Settings page
2. Add locations (gates/checkpoints)
3. Optionally import registered vehicles
4. Start monitoring!

## System Requirements

- Windows 10/11 (64-bit)
- 4GB RAM minimum
- 500MB free disk space
- Network connection for camera access

## Support

For issues or questions, contact your system administrator.
"""
    
    with open(release_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✅ Created README.txt")
    
    # Create sample .env file
    env_sample = """# CamMana Configuration

# Custom data directory (optional)
# CAMMANA_DATA_DIR=C:\\CamMana_Data

# API Configuration
# HOST=0.0.0.0
# PORT=8000

# Default camera credentials (optional)
# CAMERA_DEFAULT_USER=admin
# CAMERA_DEFAULT_PASSWORD=password123
"""
    
    with open(release_dir / ".env.example", "w", encoding="utf-8") as f:
        f.write(env_sample)
    print("✅ Created .env.example")
    
    # Calculate size
    exe_size = exe_path.stat().st_size / (1024 * 1024)  # MB
    
    print("\n" + "=" * 60)
    print("✅ Build completed successfully!")
    print("=" * 60)
    print(f"\n📁 Release package: {release_dir}")
    print(f"📊 Executable size: {exe_size:.1f} MB")
    print(f"\n📋 Distribution includes:")
    print(f"   - CamMana.exe")
    print(f"   - README.txt")
    print(f"   - .env.example")
    print(f"\n🚀 Ready to distribute!")


if __name__ == "__main__":
    build()
