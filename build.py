"""
CamMana Build Script - Zero-Config Bootstrapper Strategy
=========================================================

Creates a lightweight distribution that sets up its own environment on first run.

OUTPUT STRUCTURE:
  product/
    dist/
      CamMana/
        CamMana.exe           <- Main launcher (lightweight ~70MB)
        _internal/            <- PySide6 and Qt assets
        assets/               <- Icons + uv.exe
        frontend/out/         <- Static Next.js build
        backend/              <- Python source code (not bundled in exe)
        pyproject.toml        <- For uv sync
        uv.lock               <- Locked dependencies
        .venv/                <- Created on first run by uv

STRATEGY:
  1. Bundle ONLY PySide6 + QtWebEngine (for splash screen UI)
  2. Copy backend source code as-is (not frozen)
  3. On first run, uv creates .venv and installs heavy deps (torch, ultralytics)
  4. Launcher spawns Python from .venv to run backend server
  5. Clean subprocess management = no zombies
"""

import subprocess
import sys
import shutil
import time
from pathlib import Path


def build():
    project_dir = Path(__file__).parent
    frontend_dir = project_dir / "frontend"
    out_dir = frontend_dir / "out"
    product_dir = project_dir / "product"
    build_dir = product_dir / "build"
    dist_dir = product_dir / "dist"
    
    print("=" * 70)
    print("🚀 CamMana Build - Zero-Config Bootstrapper Strategy")
    print("=" * 70)
    
    # -------------------------------------------------------------------------
    # Step 0: Validate prerequisites
    # -------------------------------------------------------------------------
    print("\n📋 Step 0: Validating prerequisites...")
    
    required_files = [
        project_dir / "pyproject.toml",
        project_dir / "uv.lock", 
        project_dir / "assets" / "uv.exe",
        project_dir / "assets" / "icon.ico",
    ]
    
    for f in required_files:
        if not f.exists():
            print(f"❌ Missing required file: {f}")
            sys.exit(1)
    
    print("✅ All prerequisites found")
    
    # -------------------------------------------------------------------------
    # Step 1: Clean previous builds
    # -------------------------------------------------------------------------
    print("\n🧹 Step 1: Cleaning previous builds...")
    start_time = time.time()
    
    for folder in [dist_dir, build_dir]:
        if folder.exists():
            # Force kill any running instances first
            subprocess.run(
                ["taskkill", "/F", "/IM", "CamMana.exe", "/T"],
                capture_output=True,
                shell=True
            )
            time.sleep(0.5)
            try:
                shutil.rmtree(folder)
            except PermissionError as e:
                print(f"⚠️ Could not clean {folder}: {e}")
                print("   Close any running CamMana instances and try again.")
                sys.exit(1)
    
    product_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Cleaned in {time.time() - start_time:.1f}s")
    
    # -------------------------------------------------------------------------
    # Step 2: Build Next.js frontend (static export)
    # -------------------------------------------------------------------------
    print("\n📦 Step 2: Building Next.js frontend...")
    start_time = time.time()
    
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        shell=True
    )
    if result.returncode != 0:
        print("❌ Frontend build failed!")
        sys.exit(1)
    
    if not out_dir.exists():
        print(f"❌ Expected output at {out_dir} not found")
        sys.exit(1)
    
    print(f"✅ Frontend built in {time.time() - start_time:.1f}s")
    
    # -------------------------------------------------------------------------
    # Step 3: Package launcher with PyInstaller
    # -------------------------------------------------------------------------
    print("\n📦 Step 3: Packaging launcher with PyInstaller...")
    start_time = time.time()
    
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name=CamMana",
        "--onedir",                    # One directory, NOT one file (faster startup)
        "--windowed",                  # No console window
        "--noconfirm",
        "--clean",
        f"--icon={project_dir / 'assets' / 'icon.ico'}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={product_dir}",
        
        # -----------------------------------------------------------------
        # CRITICAL: Exclude heavy packages - they'll be installed by uv
        # -----------------------------------------------------------------
        "--exclude-module=torch",
        "--exclude-module=torchvision", 
        "--exclude-module=torchaudio",
        "--exclude-module=ultralytics",
        "--exclude-module=opencv-python",
        "--exclude-module=cv2",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=PIL",
        "--exclude-module=pillow",
        "--exclude-module=httpx",
        "--exclude-module=fastapi",
        "--exclude-module=uvicorn",
        "--exclude-module=pydantic",
        "--exclude-module=starlette",
        
        # Also exclude dev/test modules
        "--exclude-module=tensorboard",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=pytest",
        "--exclude-module=unittest",
        
        # -----------------------------------------------------------------
        # Include PySide6 for the splash screen UI
        # -----------------------------------------------------------------
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWebEngineWidgets",
        "--hidden-import=PySide6.QtWebEngineCore",
        "--hidden-import=PySide6.QtWebChannel",
        "--hidden-import=PySide6.QtNetwork",
        
        # -----------------------------------------------------------------
        # Bundle ONLY the launcher assets (icons)
        # Frontend and backend will be copied separately
        # -----------------------------------------------------------------
        f"--add-data={project_dir / 'assets'};assets",
        
        "app.py"
    ]
    
    result = subprocess.run(pyinstaller_args, cwd=project_dir, shell=True)
    if result.returncode != 0:
        print("❌ PyInstaller build failed!")
        sys.exit(1)
    
    print(f"✅ PyInstaller completed in {time.time() - start_time:.1f}s")
    
    # -------------------------------------------------------------------------
    # Step 4: Copy project files to distribution
    # -------------------------------------------------------------------------
    print("\n📁 Step 4: Copying project files to distribution...")
    start_time = time.time()
    
    dist_app_dir = dist_dir / "CamMana"
    
    # 4a. Copy frontend/out
    dest_frontend = dist_app_dir / "frontend" / "out"
    shutil.copytree(out_dir, dest_frontend)
    print(f"   ✓ Copied frontend/out ({sum(1 for _ in dest_frontend.rglob('*'))} files)")
    
    # 4b. Copy backend source (as-is, not frozen!)
    dest_backend = dist_app_dir / "backend"
    shutil.copytree(
        project_dir / "backend",
        dest_backend,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    )
    print(f"   ✓ Copied backend source")
    
    # 4c. Copy pyproject.toml and uv.lock (CRITICAL for uv sync)
    for filename in ["pyproject.toml", "uv.lock"]:
        src = project_dir / filename
        if src.exists():
            shutil.copy2(src, dist_app_dir / filename)
            print(f"   ✓ Copied {filename}")
    
    # 4d. Create empty database folder structure
    db_dir = dist_app_dir / "database"
    db_dir.mkdir(exist_ok=True)
    for subdir in ["csv_data", "captured_img", "car_history", "logs", "report", 
                   "calibration", "backgrounds"]:
        (db_dir / subdir).mkdir(exist_ok=True)
    print(f"   ✓ Created database folder structure")
    
    # 4e. Copy default config files if they exist
    default_configs = [
        "database/sync_config.json",
        "database/system_config.json",
        "database/calibration/calib_side.json",
        "database/calibration/calib_topdown.json",
    ]
    for cfg in default_configs:
        src = project_dir / cfg
        if src.exists():
            dest = dist_app_dir / cfg
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    
    print(f"✅ Files copied in {time.time() - start_time:.1f}s")
    
    # -------------------------------------------------------------------------
    # Step 5: Create helper scripts
    # -------------------------------------------------------------------------
    print("\n📝 Step 5: Creating helper scripts...")
    
    # README for users
    readme_content = """CamMana - Camera Manager
========================

FIRST RUN:
  When you launch CamMana.exe for the first time, it will automatically
  set up the required Python environment. This takes 1-3 minutes depending
  on your internet speed.

REQUIREMENTS:
  - Windows 10 or later
  - Internet connection (for first-time setup only)
  - 4GB RAM minimum

FILES:
  CamMana.exe      - Main application
  backend/         - Server code  
  frontend/out/    - Web interface
  database/        - Data storage
  .venv/           - Python environment (created on first run)

TROUBLESHOOTING:
  If the app doesn't start:
  1. Delete the .venv folder and restart
  2. Check if antivirus is blocking the app
  3. Run as administrator if needed
"""
    (dist_app_dir / "README.txt").write_text(readme_content, encoding="utf-8")
    
    # Quick launcher batch file (optional, for debugging)
    launcher_bat = """@echo off
cd /d "%~dp0"
CamMana.exe
pause
"""
    (dist_app_dir / "Run_Debug.bat").write_text(launcher_bat, encoding="utf-8")
    
    print("✅ Helper scripts created")
    
    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("✅ BUILD COMPLETE!")
    print("=" * 70)
    
    # Calculate size
    total_size = sum(f.stat().st_size for f in dist_app_dir.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    print(f"\n📁 Output: {dist_app_dir}")
    print(f"📊 Size: {size_mb:.1f} MB")
    print(f"\n🚀 To run: Double-click CamMana.exe")
    print("\n📦 To distribute: Zip the entire 'CamMana' folder")
    

if __name__ == "__main__":
    build()
