
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
PROD_DIR = ROOT_DIR / "production"
BUILD_DIR = PROD_DIR / "build"
OUTPUT_DIR = PROD_DIR / "output"
ASSETS_DIR = PROD_DIR / "assets"
ISS_CONFIG = PROD_DIR / "config" / "installer.iss"
FRONTEND_DIR = ROOT_DIR / "frontend"

def run_cmd(cmd, cwd=None):
    """Run a command with clear logging"""
    cwd_str = f" in {cwd}" if cwd else ""
    print(f"🚀 Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}{cwd_str}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, shell=True, check=True)

def clean():
    """Clean build artifacts and old setup files"""
    print("🧹 Cleaning build directories and old setup files...")
    
    # Remove final setup from root to avoid version confusion
    root_setup = ROOT_DIR / "CamMana_Setup.exe"
    if root_setup.exists():
        root_setup.unlink()
        print(f"🗑️ Deleted old {root_setup.name}")

    for d in [BUILD_DIR, OUTPUT_DIR]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    
    # Clean pycache
    print("🧹 Cleaning __pycache__...")
    for p in ROOT_DIR.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)

def build_frontend():
    """Build React frontend to static files"""
    print("📦 Building React Frontend...")
    if not (FRONTEND_DIR / "node_modules").exists():
        run_cmd(["npm", "install"], cwd=FRONTEND_DIR)
    run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR)

def compile_nuitka():
    """Compile Python to a single native binary using Nuitka"""
    print("⚙️ Compiling Backend with Nuitka (this may take a few minutes)...")
    
    # Nuitka command
    # --onefile creates a single executable
    # --include-data-dir embeds our assets and frontend
    # --remove-output cleans up the massive amount of C source files after build
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        f"--include-data-dir={FRONTEND_DIR / 'out'}=frontend/out",
        f"--include-data-dir={ASSETS_DIR}=assets",
        f"--include-data-dir={ROOT_DIR / 'backend'}=backend",
        f"--include-data-file={ROOT_DIR / 'pyproject.toml'}=pyproject.toml",
        "--windows-console-mode=disable",
        "--plugin-enable=pyside6",
        "--output-dir={}".format(BUILD_DIR),
        "--output-filename=CamMana",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--show-progress",
        "--quiet",
        # Speed up & Bloat reduction
        "--jobs=20",
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-unittest-mode=nofollow",
        "--noinclude-IPython-mode=nofollow",
        str(ROOT_DIR / "app.py")
    ]
    run_cmd(nuitka_cmd)
    
    # Move the final EXE to production/CamMana.exe
    built_exe = BUILD_DIR / "CamMana.exe"
    target_exe = PROD_DIR / "CamMana.exe"
    
    if built_exe.exists():
        if target_exe.exists():
            target_exe.unlink()
        shutil.move(str(built_exe), str(target_exe))
        print(f"✅ Executable saved to: {target_exe}")
    else:
        # Check if it was created in a subdir for some reason
        possible_nested = BUILD_DIR / "app.dist" / "CamMana.exe"
        if possible_nested.exists():
             if target_exe.exists(): target_exe.unlink()
             shutil.move(str(possible_nested), str(target_exe))
             print(f"✅ Executable saved to: {target_exe}")

def package_inno():
    """Package the compiled app into a setup.exe using Inno Setup"""
    print("🛠️ Packaging with Inno Setup...")
    
    # Check for ISCC (Inno Setup Compiler) in common locations
    search_paths = [
        shutil.which("iscc"),
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"), # Fallback to v5
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramW6432", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe"
    ]
    
    iscc = None
    for p in search_paths:
        if p and Path(p).exists():
            iscc = p
            break
        
    if not iscc:
        print("❌ ISCC.exe (Inno Setup) not found. Skipping auto-packaging.")
        print(f"👉 Please install Inno Setup 6 and run '{ISS_CONFIG}' manually.")
        return

    # Inno Setup command
    # We pass the OutputDir via command line to keep the .iss file clean
    iscc_cmd = [
        str(iscc),
        f"/O{OUTPUT_DIR}",
        str(ISS_CONFIG)
    ]
    
    try:
        run_cmd(iscc_cmd)
        
        # Move final setup to root for convenience
        setup_exe = OUTPUT_DIR / "CamMana_Setup.exe"
        if setup_exe.exists():
            shutil.copy2(setup_exe, ROOT_DIR / "CamMana_Setup.exe")
            print(f"✅ Success! Installer created: {ROOT_DIR / 'CamMana_Setup.exe'}")
    except Exception as e:
        print(f"⚠️ Inno Setup failed: {e}")
        print("Note: The standalone EXE in 'production/CamMana.exe' is still valid.")

def main():
    try:
        clean()
        build_frontend()
        compile_nuitka()
        package_inno()
        print("\n🎉 Build process completed successfully.")
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
