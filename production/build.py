#!/usr/bin/env python
"""
CamMana Production Build Script

Usage:
  uv run python production/build.py              # Full clean build
  uv run python production/build.py --incremental # Incremental build (faster)
  uv run python production/build.py --frontend   # Frontend only
  uv run python production/build.py --backend    # Backend only
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
PROD_DIR = ROOT_DIR / "production"
BUILD_DIR = PROD_DIR / "build"
OUTPUT_DIR = PROD_DIR / "output"
ASSETS_DIR = PROD_DIR / "assets"
ISS_CONFIG = PROD_DIR / "config" / "installer.iss"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Parse arguments
INCREMENTAL = "--incremental" in sys.argv or "-i" in sys.argv
FRONTEND_ONLY = "--frontend" in sys.argv
BACKEND_ONLY = "--backend" in sys.argv

# Detect CPU cores for optimal parallelization
CPU_CORES = os.cpu_count() or 8
NUITKA_JOBS = min(CPU_CORES, 16)  # Use all cores up to 16

# Build start time
BUILD_START = time.time()


def elapsed() -> str:
    """Get elapsed time since build start"""
    secs = int(time.time() - BUILD_START)
    mins, secs = divmod(secs, 60)
    return f"{mins:02d}:{secs:02d}"


def log(msg: str, level: str = "info"):
    """Print formatted log messages"""
    icons = {
        "info": "[INFO]",
        "success": "[ OK ]",
        "warning": "[WARN]",
        "error": "[FAIL]",
        "step": "[====]",
        "dim": "[....]",
    }
    icon = icons.get(level, "[INFO]")
    print(f"[{elapsed()}] {icon} {msg}")


def header(title: str):
    """Print a section header"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def run_cmd(cmd, cwd=None, check=True, silent=False):
    """Run a command with logging"""
    if not silent:
        cmd_str = ' '.join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
        log(f"Running: {cmd_str[:60]}...", "dim")
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, shell=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode})")
    return result


def clean(incremental: bool = False):
    """Clean build artifacts"""
    if incremental:
        log("Incremental mode - keeping Nuitka cache", "info")
        return
    
    log("Cleaning previous build artifacts...", "step")
    
    for f in [ROOT_DIR / "CamMana_Setup.exe", PROD_DIR / "dist"]:
        if f.exists():
            if f.is_dir():
                shutil.rmtree(f)
            else:
                f.unlink()

    for d in [BUILD_DIR, OUTPUT_DIR]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    
    # Clean pycache
    count = 0
    for p in ROOT_DIR.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
        count += 1
    
    log(f"Cleaned {count} cache directories", "success")


def build_frontend(force: bool = False):
    """Build React frontend"""
    log("Building React Frontend...", "step")
    out_dir = FRONTEND_DIR / "out"
    
    if not force and out_dir.exists() and (out_dir / "index.html").exists():
        log("Frontend already built (use --frontend to rebuild)", "info")
        return
    
    if out_dir.exists():
        shutil.rmtree(out_dir)
    
    if not (FRONTEND_DIR / "node_modules").exists():
        log("Installing npm dependencies...", "info")
        run_cmd(["npm", "install"], cwd=FRONTEND_DIR, silent=True)
    
    run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, silent=True)
    log("Frontend build complete", "success")


def compile_nuitka():
    """Compile Python to standalone using Nuitka"""
    log("Compiling with Nuitka...", "step")
    log(f"Using {NUITKA_JOBS} parallel workers (detected {CPU_CORES} CPU cores)", "info")
    
    # Nuitka command - optimized for speed and size
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        # Data files
        f"--include-data-dir={FRONTEND_DIR / 'out'}=frontend/out",
        f"--include-data-dir={ASSETS_DIR}=assets",
        # Windows
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={ASSETS_DIR / 'icon.ico'}",
        # Plugins
        "--plugin-enable=pyside6",
        # Output
        f"--output-dir={BUILD_DIR}",
        "--assume-yes-for-downloads",
        # Progress display
        "--show-progress",
        "--show-memory",
        # Performance - use all available cores
        f"--jobs={NUITKA_JOBS}",
        # === EXCLUDE UNUSED PACKAGES ===
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-unittest-mode=nofollow",
        "--noinclude-IPython-mode=nofollow",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=torchvision",
        "--nofollow-import-to=ultralytics",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=notebook",
        "--nofollow-import-to=jupyter",
        # Entry
        str(ROOT_DIR / "app.py")
    ]
    
    print()
    log("Phase 1/3: Python optimization...", "info")
    
    # Run with real-time output
    process = subprocess.Popen(
        nuitka_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True, 
        shell=True, 
        bufsize=1
    )
    
    errors = []
    last_phase = ""
    modules_done = 0
    
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        line = line.rstrip()
        
        # Track phases
        if "Completed Python level" in line:
            print()
            log("Phase 2/3: Generating C code...", "info")
            last_phase = "c_gen"
        elif "Running C compilation" in line:
            print()
            log("Phase 3/3: Compiling C code...", "info")
            last_phase = "c_compile"
        elif "Backend C:" in line:
            # Show C compilation progress
            print(f"\r         {line.strip()}", end="", flush=True)
        elif "Optimizing module" in line:
            # Count modules
            modules_done += 1
            if modules_done % 50 == 0:
                print(f"\r         Optimized {modules_done} modules...", end="", flush=True)
        elif "error:" in line.lower() and "torch" not in line.lower():
            errors.append(line)
            print(f"\n[ERROR] {line}")
        elif "warning:" in line.lower() and any(kw in line.lower() for kw in ["missing", "failed"]):
            print(f"\n[WARN] {line}")
    
    print()  # New line after progress
    process.wait()
    
    if process.returncode != 0:
        header("BUILD FAILED")
        if errors:
            for e in errors[:5]:
                log(e, "error")
        log("Try: uv sync && uv run python production/build.py", "info")
        raise RuntimeError("Nuitka compilation failed")
    
    log(f"Optimized {modules_done} modules", "success")
    
    # Move output
    dist = BUILD_DIR / "app.dist"
    target = PROD_DIR / "dist"
    
    if dist.exists():
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(dist), str(target))
        
        src = target / "app.exe"
        dst = target / "CamMana.exe"
        if src.exists():
            if dst.exists():
                dst.unlink()
            src.rename(dst)
        
        size_mb = dst.stat().st_size / 1024 / 1024
        log(f"Executable created: CamMana.exe ({size_mb:.1f} MB)", "success")
    else:
        raise RuntimeError("Build output not found")


def package_inno():
    """Create installer with Inno Setup"""
    log("Creating Windows installer...", "step")
    
    iscc = None
    for p in [
        shutil.which("iscc"),
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]:
        if p and Path(p).exists():
            iscc = p
            break
    
    if not iscc:
        log("Inno Setup not found - skipping installer", "warning")
        log("Install from: https://jrsoftware.org/isdl.php", "info")
        return
    
    result = run_cmd([str(iscc), f"/O{OUTPUT_DIR}", str(ISS_CONFIG)], check=False, silent=True)
    if result.returncode == 0:
        src = OUTPUT_DIR / "CamMana_Setup.exe"
        if src.exists():
            shutil.copy2(src, ROOT_DIR / "CamMana_Setup.exe")
            size_mb = src.stat().st_size / 1024 / 1024
            log(f"Installer created: CamMana_Setup.exe ({size_mb:.1f} MB)", "success")
    else:
        log("Inno Setup packaging failed", "error")


def main():
    mode = "INCREMENTAL" if INCREMENTAL else "FULL"
    if FRONTEND_ONLY:
        mode = "FRONTEND ONLY"
    elif BACKEND_ONLY:
        mode = "BACKEND ONLY"
    
    header(f"CamMana Production Build [{mode}]")
    
    print(f"  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  CPU cores:  {CPU_CORES} (using {NUITKA_JOBS} workers)")
    print()
    
    try:
        if FRONTEND_ONLY:
            build_frontend(force=True)
        else:
            clean(incremental=INCREMENTAL)
            if not BACKEND_ONLY:
                build_frontend()
            compile_nuitka()
            package_inno()
        
        # Summary
        total_time = int(time.time() - BUILD_START)
        mins, secs = divmod(total_time, 60)
        
        header("BUILD SUCCESSFUL")
        
        dist_exe = PROD_DIR / "dist" / "CamMana.exe"
        setup_exe = ROOT_DIR / "CamMana_Setup.exe"
        
        print(f"  Total time: {mins}m {secs}s")
        print()
        if dist_exe.exists():
            size = dist_exe.stat().st_size / 1024 / 1024
            print(f"  Standalone: {dist_exe}")
            print(f"              Size: {size:.1f} MB")
        if setup_exe.exists():
            size = setup_exe.stat().st_size / 1024 / 1024
            print(f"  Installer:  {setup_exe}")
            print(f"              Size: {size:.1f} MB")
        print()
            
    except Exception as e:
        print()
        log(f"Build failed: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
