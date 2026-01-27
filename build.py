"""
Build script for CamMana Windows Application
Creates a standalone .exe file with all dependencies bundled

Output Structure:
  product/
    build/          <- PyInstaller build artifacts
    cammana.exe     <- Final executable
    README.txt
    .env.example
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
    product_dir = project_dir / "product"
    build_dir = product_dir / "build"
    models_dir = project_dir / "backend" / "model_process" / "models"  # Models in backend
    
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
    if product_dir.exists():
        shutil.rmtree(product_dir)
        print("✅ Cleaned product directory")
    
    # Create product directory structure
    product_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean old dist/build in project root if exists
    old_dist = project_dir / "dist"
    old_build = project_dir / "build"
    if old_dist.exists():
        shutil.rmtree(old_dist)
    if old_build.exists():
        shutil.rmtree(old_build)
    
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
    
    # Include models directory if exists (backend/model_process/models)
    if models_dir.exists():
        add_data_args.append(f"--add-data={models_dir};backend/model_process/models")
    
    # Build with PyInstaller (output to product directory)
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name=CamMana",
        "--onefile",
        "--windowed",
        "--icon=NONE",
        "--noconfirm",  # Overwrite without asking
        f"--distpath={product_dir}",  # Output exe to product folder
        f"--workpath={build_dir}",     # Build artifacts to product/build
        f"--specpath={build_dir}",     # Spec file to product/build
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
        # Image processing
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        # Data processing
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",  # Excel export
        "--hidden-import=xlrd",      # Excel read
        # HTTP/Async
        "--hidden-import=httpx",
        "--hidden-import=aiofiles",
        "--hidden-import=passlib",
        "--hidden-import=passlib.handlers.bcrypt",
        # Optimize
        "--optimize=2",  # Highest optimization level
    ] + add_data_args + ["app.py"]
    
    result = subprocess.run(pyinstaller_args, cwd=project_dir, shell=True)
    
    if result.returncode != 0:
        print("❌ PyInstaller build failed!")
        sys.exit(1)
    
    # Step 4: Create distribution package
    print("\n📦 Step 4: Creating distribution package...")
    
    # Executable is already in product folder
    exe_path = product_dir / "CamMana.exe"
    
    if not exe_path.exists():
        print(f"❌ Executable not found at {exe_path}")
        sys.exit(1)
    
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
    
    with open(product_dir / "README.txt", "w", encoding="utf-8") as f:
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
    
    with open(product_dir / ".env.example", "w", encoding="utf-8") as f:
        f.write(env_sample)
    print("✅ Created .env.example")
    
    # Save build configuration info
    build_info = f"""# CamMana Build Configuration
# Generated during build process

Build Date: {os.popen('date /t').read().strip()}
Python Version: {sys.version}
PyInstaller Output: product/

## Directory Structure
product/
├── CamMana.exe     <- Main executable
├── README.txt      <- User documentation
├── .env.example    <- Environment config template
└── build/          <- PyInstaller artifacts (can be deleted)

## Hidden Imports Included
- uvicorn (logging, loops, protocols, lifespan)
- zeep, onvif_zeep (ONVIF camera support)
- ultralytics (YOLO car detection)
- apscheduler (task scheduling)
- zeroconf (network discovery)
- PySide6 (Qt GUI)

## Data Bundles
- frontend/out (Next.js static export)
- backend/model_process/models/ (YOLO model)
"""
    
    with open(build_dir / "BUILD_CONFIG.md", "w", encoding="utf-8") as f:
        f.write(build_info)
    print("✅ Saved build configuration to product/build/BUILD_CONFIG.md")
    
    # Calculate size
    exe_size = exe_path.stat().st_size / (1024 * 1024)  # MB
    
    print("\n" + "=" * 60)
    print("✅ Build completed successfully!")
    print("=" * 60)
    print(f"\n📁 Output folder: {product_dir}")
    print(f"📊 Executable size: {exe_size:.1f} MB")
    print(f"\n📋 Distribution structure:")
    print(f"   product/")
    print(f"   ├── CamMana.exe")
    print(f"   ├── README.txt")
    print(f"   ├── .env.example")
    print(f"   └── build/           <- Build artifacts")
    print(f"\n🚀 Ready to distribute!")


if __name__ == "__main__":
    build()
