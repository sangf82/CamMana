"""
Build script for CamMana Windows Application
Creates a standalone .exe file with all dependencies bundled
"""

import subprocess
import sys
import shutil
from pathlib import Path


def build():
    """Build the CamMana Windows application"""
    
    project_dir = Path(__file__).parent
    frontend_dir = project_dir / "frontend"
    out_dir = frontend_dir / "out"
    
    print("=" * 60)
    print("🔨 Building CamMana Windows Application")
    print("=" * 60)
    
    # Step 1: Build Next.js frontend
    print("\n📦 Step 1: Building Next.js frontend...")
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
    
    # Step 2: Create PyInstaller spec file
    print("\n📦 Step 2: Packaging with PyInstaller...")
    
    # Build with PyInstaller
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--name=CamMana",
        "--onefile",
        "--windowed",
        "--icon=NONE",
        f"--add-data={out_dir};frontend/out",
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
        "--collect-all=zeep",
        "--collect-all=onvif_zeep",
        "app.py"
    ], cwd=project_dir, shell=True)
    
    if result.returncode != 0:
        print("❌ PyInstaller build failed!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Build completed successfully!")
    print("=" * 60)
    print(f"\n📁 Executable location: {project_dir / 'dist' / 'CamMana.exe'}")
    print("\nTo run the app, execute: dist\\CamMana.exe")


if __name__ == "__main__":
    build()
