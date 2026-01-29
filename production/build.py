#!/usr/bin/env python
"""
CamMana Production Build Script

Usage:
  uv run python production/build.py              # Full clean build
  uv run python production/build.py --incremental # Incremental build (faster)
  uv run python production/build.py --frontend   # Frontend only
  uv run python production/build.py --backend    # Backend only
  uv run python production/build.py --clean      # Manual cleanup only
"""

import os
import sys
import shutil
import subprocess
import time
import re
import tomllib
from functools import lru_cache
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
PROD_DIR = ROOT_DIR / "production"
BUILD_DIR = PROD_DIR / "build"
OUTPUT_DIR = PROD_DIR / "output"
ASSETS_DIR = PROD_DIR / "assets"
ISS_CONFIG = PROD_DIR / "config" / "installer.iss"
FRONTEND_DIR = ROOT_DIR / "frontend"

# CLI Arguments
INCREMENTAL = "--incremental" in sys.argv or "-i" in sys.argv
FRONTEND_ONLY = "--frontend" in sys.argv
BACKEND_ONLY = "--backend" in sys.argv
CLEAN_ONLY = "--clean" in sys.argv

# CPU Configuration
CPU_CORES = os.cpu_count() or 8
NUITKA_JOBS = max(1, min(CPU_CORES - 2, 16))

# Build timing
BUILD_START = time.time()

# Package mappings (pip name -> import name)
PACKAGE_NAME_MAP = {
    "opencv-python": "cv2",
    "pillow": "PIL",
    "pyside6": "PySide6",
    "pydantic-settings": "pydantic_settings",
    "python-multipart": "multipart",
    "python-dotenv": "dotenv",
    "onvif-zeep": "onvif",
    "fpdf2": "fpdf",
    "python-jose": "jose",
}

# Packages that need full inclusion (dynamic imports)
INCLUDE_FULL_PACKAGES = {
    "pandas", "matplotlib", "openpyxl", "passlib",
    "bcrypt", "PIL", "jose", "apscheduler",
}

# Packages to skip in Nuitka
SKIP_PACKAGES = {"uvicorn"}

# =============================================================================
# PYPROJECT CONFIG
# =============================================================================


@lru_cache(maxsize=1)
def get_pyproject_config() -> dict:
    """Read and cache pyproject.toml configuration (cached for performance)."""
    pyproject_path = ROOT_DIR / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def get_app_version() -> str:
    """Get app version from pyproject.toml."""
    return get_pyproject_config().get("project", {}).get("version", "1.0.0")


def get_app_author() -> str:
    """Get app author from pyproject.toml."""
    authors = get_pyproject_config().get("project", {}).get("authors", [])
    return authors[0].get("name", "Unknown") if authors and isinstance(authors[0], dict) else "Unknown"



def get_production_packages() -> list[str]:
    """Extract production dependencies from pyproject.toml for Nuitka."""
    try:
        dependencies = get_pyproject_config().get("project", {}).get("dependencies", [])
    except FileNotFoundError:
        print("⚠️  Warning: pyproject.toml not found")
        return []
    
    packages = []
    for dep in dependencies:
        if match := re.match(r"^([a-zA-Z0-9_-]+)", dep):
            pip_name = match.group(1).lower()
            if pip_name not in SKIP_PACKAGES:
                packages.append(PACKAGE_NAME_MAP.get(pip_name, pip_name.replace("-", "_")))
    return packages


def sync_installer_config():
    """
    Synchronize installer.iss with version/author from pyproject.toml.
    This ensures the installer always matches the codebase version.
    """
    version = get_app_version()
    author = get_app_author()
    
    log(f"Syncing installer config: v{version} by {author}", "info")
    
    iss_content = ISS_CONFIG.read_text(encoding="utf-8")
    
    # Update #define directives at the top
    iss_content = re.sub(
        r'#define AppVersion "[^"]+"',
        f'#define AppVersion "{version}"',
        iss_content
    )
    iss_content = re.sub(
        r'#define AppPublisher "[^"]+"',
        f'#define AppPublisher "{author}"',
        iss_content
    )
    
    ISS_CONFIG.write_text(iss_content, encoding="utf-8")
    log(f"Installer synced: v{version}, author: {author}", "success")


def preflight_checks() -> bool:
    """
    Validate all requirements BEFORE starting the long build process.
    Catches missing files and configuration issues early.
    """
    header("PRE-BUILD VALIDATION")
    errors = []
    warnings = []
    
    # Required files
    required_files = [
        (ROOT_DIR / "app.py", "Main entry point"),
        (ROOT_DIR / "pyproject.toml", "Project configuration"),
        (ASSETS_DIR / "icon.ico", "Application icon"),
        (ASSETS_DIR / "icon.png", "Splash screen icon"),
        (ISS_CONFIG, "Inno Setup configuration"),
    ]
    for path, desc in required_files:
        if not path.exists():
            errors.append(f"Missing {desc}: {path.name}")
    
    # Wizard images for installer (optional but recommended)
    for img in ["wizard_small.bmp", "wizard_large.bmp"]:
        if not (ASSETS_DIR / img).exists():
            warnings.append(f"Missing installer image: {img} (installer will use defaults)")
    
    # Check Nuitka is available
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            errors.append("Nuitka not working. Run: uv add nuitka")
    except Exception as e:
        errors.append(f"Nuitka check failed: {e}")
    
    # Check frontend build or node_modules
    frontend_out = FRONTEND_DIR / "out"
    if not frontend_out.exists():
        if not (FRONTEND_DIR / "node_modules").exists():
            warnings.append("Frontend not built & no node_modules - npm install will run")
        else:
            log("Frontend will be built during this process", "info")
    
    # Report results
    for w in warnings:
        log(w, "warning")
    
    if errors:
        for e in errors:
            log(e, "error")
        print()
        log("Pre-flight checks FAILED. Fix errors above before building.", "error")
        return False
    
    log("All pre-flight checks passed!", "success")
    print()
    return True


# =============================================================================
# LOGGING & UTILITIES
# =============================================================================

def elapsed() -> str:
    """Get elapsed time since build start."""
    mins, secs = divmod(int(time.time() - BUILD_START), 60)
    return f"{mins:02d}:{secs:02d}"


LOG_ICONS = {
    "info": "💡", "success": "✅", "warning": "⚠️",
    "error": "❌", "step": "🚀", "dim": "⚙️",
}

def log(msg: str, level: str = "info"):
    """Print formatted log message with icon."""
    print(f"[{elapsed()}] {LOG_ICONS.get(level, '🔹')} {msg}")


def header(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}\n")


def run_cmd(cmd, cwd=None, check=True, silent=False):
    """Run a shell command with optional logging."""
    if not silent:
        cmd_str = ' '.join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
        log(f"Running: {cmd_str[:60]}...", "dim")
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, shell=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode})")
    return result


# =============================================================================
# BUILD SYNC FUNCTIONS
# =============================================================================}


def sync_installer_config():
    """Sync installer.iss version/author from pyproject.toml."""
    version, author = get_app_version(), get_app_author()
    log(f"Syncing installer: v{version} by {author}", "info")
    
    content = ISS_CONFIG.read_text(encoding="utf-8")
    content = re.sub(r'#define AppVersion "[^"]+"', f'#define AppVersion "{version}"', content)
    content = re.sub(r'#define AppPublisher "[^"]+"', f'#define AppPublisher "{author}"', content)
    ISS_CONFIG.write_text(content, encoding="utf-8")
    
    log(f"Installer synced: v{version}, author: {author}", "success")


# =============================================================================
# BUILD OPERATIONS
# =============================================================================


def clean(incremental: bool = False, create_dirs: bool = True):
    """Clean build artifacts"""
    if incremental:
        log("Incremental mode - keeping Nuitka cache", "info")
        return
    
    log("Full Build Refresh: Cleaning all artifacts...", "step")
    
    # In FULL build, we clean EVERYTHING including the build cache for a true refresh
    targets = [
        ROOT_DIR / "CamMana_Setup.exe", 
        PROD_DIR / "dist",
        BUILD_DIR,
        OUTPUT_DIR
    ]
    
    for f in targets:
        if f.exists():
            if f.is_dir():
                shutil.rmtree(f, ignore_errors=True)
            else:
                f.unlink(missing_ok=True)

    if create_dirs:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clean pycache
    count = 0
    for p in ROOT_DIR.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
        count += 1
    
    log(f"Pre-flight cleanup done ({count} pycache dirs removed)", "success")


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
    
    # Auto-detect packages from pyproject.toml
    all_packages = get_production_packages()
    packages_to_include = [pkg for pkg in all_packages if pkg in INCLUDE_FULL_PACKAGES]
    
    log(f"Auto-detected {len(all_packages)} dependencies from pyproject.toml", "info")
    log(f"Including full packages: {', '.join(packages_to_include)}", "dim")
    
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
    ]
    
    # Add dynamic package includes (packages with complex submodule structures)
    for pkg in packages_to_include:
        nuitka_cmd.append(f"--include-package={pkg}")
    
    # Continue with rest of Nuitka options
    nuitka_cmd.extend([
        # Output
        f"--output-dir={BUILD_DIR}",
        "--assume-yes-for-downloads",
        "--show-memory",
        f"--jobs={NUITKA_JOBS}",
        # === PERFORMANCE OPTIMIZATIONS ===
        "--lto=yes",             # Enable Link Time Optimization for better runtime performance
        "--no-pyi-file",         # Don't spend time parsing .pyi files
        "--python-flag=no_site", # Faster startup (skip site.py)
        
        # === EXCLUDE UNUSED PACKAGES AND BLOAT ===
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-unittest-mode=nofollow",
        "--noinclude-IPython-mode=nofollow",
        
        # Block heavy libraries from being followed recursively (they take ages)
        "--nofollow-import-to=torch",
        "--nofollow-import-to=torchvision",
        "--nofollow-import-to=ultralytics",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=numba",
        "--nofollow-import-to=docutils",
        "--nofollow-import-to=notebook",
        "--nofollow-import-to=jupyter",
        "--nofollow-import-to=pandas.tests",
        "--nofollow-import-to=numpy.tests",
        "--nofollow-import-to=numpy.f2py",
        "--nofollow-import-to=matplotlib.tests",
        "--nofollow-import-to=matplotlib.sphinxext",
        "--nofollow-import-to=matplotlib.backends.test_backends",
        "--nofollow-import-to=matplotlib.sample_data",
        "--nofollow-import-to=matplotlib.backends.qt_editor",
        
        # Entry
        str(ROOT_DIR / "app.py")
    ])
    
    print()
    log("Phase 1/3: Python optimization...", "info")
    log("Scanning project dependencies... (This can take 15-30 mins for 100k+ files)", "dim")
    
    # Add show progress back
    nuitka_cmd.insert(10, "--show-progress")
    # Set NO_COLOR to prevent colorama/ANSI issues on Windows pipes
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    
    process = subprocess.Popen(
        nuitka_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True, 
        shell=False,
        env=env,
        bufsize=1
    )
    
    pbar = tqdm(total=100, desc="Building", unit="%", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]')
    
    errors = []
    modules_total = 0
    modules_done = 0
    
    # regex for module progress: (123/456)
    module_regex = re.compile(r"\((\d+)/(\d+)\)")
    # regex for C compilation progress: [ 10%]
    color_strip = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        line = line.rstrip()
        # Strip ANSI colors if present
        clean_line = color_strip.sub('', line)
        
        # Track phases and update pbar
        if "Completed Python level" in clean_line:
            pbar.set_description("Phase 2/3: Generating C code")
            pbar.n = 33 # roughly 1/3
            pbar.refresh()
        elif "Running C compilation" in clean_line:
            pbar.set_description("Phase 3/3: Compiling C code")
            pbar.n = 66 # roughly 2/3
            pbar.refresh()
        elif "Backend C:" in clean_line:
            # Try to find percentage like [ 10%]
            if "%" in clean_line:
                try:
                    pct_str = clean_line.split("[")[1].split("%")[0].strip()
                    pct = int(pct_str)
                    # Maps 0-100% C comp to 66-100% total progress
                    total_pct = 66 + int(pct * 0.34)
                    pbar.n = total_pct
                    pbar.set_postfix_str(f"C Comp: {pct}%")
                    pbar.refresh()
                except:
                    pass
        elif "Optimizing module" in clean_line:
            match = module_regex.search(clean_line)
            if match:
                done = int(match.group(1))
                total = int(match.group(2))
                modules_done = done
                modules_total = total
                # Maps module progress to 0-33% total progress
                total_pct = int((done / total) * 33)
                pbar.n = total_pct
                pbar.set_description(f"Phase 1/3: Optimizing ({done}/{total})")
                pbar.refresh()
            
        elif "error:" in clean_line.lower() and "torch" not in clean_line.lower():
            errors.append(clean_line)
        elif "warning:" in clean_line.lower() and any(kw in clean_line.lower() for kw in ["missing", "failed"]):
            tqdm.write(f"[{elapsed()}] ⚠️  {clean_line}")
    
    pbar.n = 100
    pbar.set_description("Compilation Finished")
    pbar.close()
    print()
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
        # Silently skip if not found, just a small status info
        log("Inno Setup not found - installer skipped (Install it to create .exe setup)", "dim")
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
    mode = "FULL"
    if INCREMENTAL: mode = "INCREMENTAL"
    elif FRONTEND_ONLY: mode = "FRONTEND ONLY"
    elif BACKEND_ONLY: mode = "BACKEND ONLY"
    elif CLEAN_ONLY: mode = "CLEANUP"
    
    header(f"CamMana Production Build [{mode}]")
    
    if CLEAN_ONLY:
        clean(incremental=False, create_dirs=False)
        log("Cleanup finished successfully (Build folders removed)", "success")
        return

    print(f"  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  CPU cores:  {CPU_CORES} (using {NUITKA_JOBS} workers)")
    print("  💡 Tip: Disable Antivirus for the build folder to speed up Phase 3.")
    print("  💡 Tip: Install 'ccache' to make incremental builds instant.")
    print()
    
    try:
        # Run pre-flight checks before any heavy work
        if not FRONTEND_ONLY and not preflight_checks():
            sys.exit(1)
        
        if FRONTEND_ONLY:
            build_frontend(force=True)
        else:
            # Sync version/author to installer config
            sync_installer_config()
            
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
