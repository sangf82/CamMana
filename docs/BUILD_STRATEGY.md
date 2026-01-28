# CamMana Build Strategy: Zero-Config Bootstrapper

## Overview

CamMana uses an **Intelligent Bootstrapper** strategy that creates a lightweight, reproducible single-folder distribution. This solves common issues with PyInstaller builds:

| Problem | Solution |
|---------|----------|
| 500MB+ exe file | ~70MB lightweight bundle |
| Slow extraction on start | `--onedir` = instant start |
| Zombie processes | `ProcessManager` with proper cleanup |
| Driver/library conflicts | `uv sync` installs correct versions per machine |
| Reproducibility issues | Lockfile ensures identical installs |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CamMana.exe                              │
│                     (Frozen PySide6 UI)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ SplashScreen │───▶│ Bootstrap    │───▶│ Backend Manager  │   │
│  │    (Qt)      │    │  Manager     │    │  (Subprocess)    │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│         │                   │                    │              │
│         ▼                   ▼                    ▼              │
│   Show progress      Run uv sync           Spawn Python        │
│                      (first run)           from .venv          │
│                                                  │              │
│                                                  ▼              │
│                                           FastAPI Server       │
│                                           (Port 8000)          │
│                                                  │              │
│  ┌──────────────────────────────────────────────┼──────────────┤
│  │              Main Window (Qt WebEngine)      │              │
│  │                                              ▼              │
│  │              ┌────────────────────────────────┐             │
│  │              │   Embedded Browser             │             │
│  │              │   http://127.0.0.1:8000        │             │
│  │              └────────────────────────────────┘             │
│  └──────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────┘
```

---

## Distribution Structure

```
CamMana/                         # Distribution folder (~70MB initial)
├── CamMana.exe                  # Main launcher
├── _internal/                   # PySide6 + Qt libraries (bundled)
│   └── assets/
│       ├── icon.ico
│       ├── icon.png
│       └── uv.exe               # Bundled uv for first-run setup
├── backend/                     # Python source code (NOT frozen)
│   ├── server.py
│   ├── config.py
│   └── ...
├── frontend/
│   └── out/                     # Static Next.js build
├── database/                    # User data folder
│   ├── csv_data/
│   ├── captured_img/
│   └── ...
├── pyproject.toml               # Dependency specification
├── uv.lock                      # Locked versions
├── .venv/                       # Created on first run (~400MB)
│   └── Scripts/
│       └── python.exe           # Python used to run backend
└── README.txt
```

---

## First-Run Flow

```
User double-clicks CamMana.exe
          │
          ▼
┌─────────────────────────────┐
│  Splash Screen appears      │  (Instant - no extraction delay)
└─────────────────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  BootstrapManager checks    │
│  for .venv folder           │
└─────────────────────────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
.venv exists?  .venv missing?
    │               │
    │               ▼
    │     ┌─────────────────────────┐
    │     │  Show: "First-time      │
    │     │  setup: Installing..."  │
    │     └─────────────────────────┘
    │               │
    │               ▼
    │     ┌─────────────────────────┐
    │     │  Run: uv sync --frozen  │
    │     │  (1-3 minutes)          │
    │     └─────────────────────────┘
    │               │
    └───────┬───────┘
            │
            ▼
┌─────────────────────────────┐
│  BackendManager spawns      │
│  python.exe from .venv      │
│  to run FastAPI server      │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│  Wait for port 8000         │
└─────────────────────────────┘
            │
            ▼
┌─────────────────────────────┐
│  Main window opens with     │
│  embedded browser           │
└─────────────────────────────┘
```

---

## Process Management (No Zombies)

The `ProcessManager` class ensures clean subprocess handling:

### Key Features

1. **Singleton Pattern**: Only one instance manages all processes
2. **Process Group**: Uses `CREATE_NEW_PROCESS_GROUP` on Windows
3. **Tree Kill**: Uses `taskkill /F /T` to kill entire process trees
4. **atexit Registration**: Cleanup runs even on unexpected exit
5. **Explicit Cleanup**: Also called manually before `sys.exit()`

### Process Lifecycle

```python
# Spawn with tracking
proc = ProcessManager().spawn(
    args=["python", "-c", "..."],
    cwd="/path/to/app"
)

# On app close:
# 1. closeEvent() fires
# 2. app.exec() returns
# 3. ProcessManager().cleanup_all() called explicitly
# 4. atexit handlers run (backup cleanup)
# 5. taskkill /F /T /PID kills all children
```

---

## Build Process

Run the build script:

```bash
cd s:\projects\CamMana
python build.py
```

### Build Steps

1. **Validate Prerequisites**
   - Check pyproject.toml, uv.lock, uv.exe, icon.ico

2. **Clean Previous Builds**
   - Kill running CamMana processes
   - Remove dist/ and build/ folders

3. **Build Next.js Frontend**
   - Runs `npm run build` in frontend/
   - Creates static export in frontend/out/

4. **Package with PyInstaller**
   - Creates `--onedir` bundle
   - Bundles ONLY PySide6 and Qt libraries
   - Excludes heavy packages (torch, ultralytics, numpy, etc.)

5. **Copy Project Files**
   - backend/ source code
   - frontend/out/ static files
   - pyproject.toml and uv.lock
   - database/ folder structure

6. **Create Helper Scripts**
   - README.txt with instructions
   - Run_Debug.bat for troubleshooting

---

## Why This Strategy Works

### 1. No Extraction Hang
- `--onedir` means files are already on disk
- No temp folder extraction needed
- App starts in < 1 second

### 2. Always Reproducible
- `uv sync --frozen` uses exact versions from uv.lock
- Each machine gets packages compiled for its hardware
- No binary compatibility issues

### 3. Zero Admin Rights
- Everything stays in app folder
- No registry writes
- No PATH modifications
- Can run from USB drive

### 4. Clean Separation
- UI runs in frozen PySide6 process
- Backend runs in separate Python process
- No import conflicts between frozen and dynamic code

### 5. No Zombie Processes
- ProcessManager tracks all subprocesses
- Uses Windows process groups for tree termination
- Multiple cleanup hooks ensure processes die

---

## Troubleshooting

### App doesn't start
1. Delete `.venv` folder and restart
2. Check if antivirus is blocking
3. Run as administrator

### First-run setup fails
1. Check internet connection
2. Ensure firewall allows uv.exe
3. Check pyproject.toml and uv.lock exist

### Backend doesn't start
1. Check port 8000 is free: `netstat -an | findstr 8000`
2. Check .venv/Scripts/python.exe exists
3. Look at Run_Debug.bat output

### Zombie processes remain
1. Open Task Manager
2. Kill all python.exe and CamMana.exe
3. Restart app

---

## Files Modified

| File | Purpose |
|------|---------|
| `build.py` | Build script with proper file copying |
| `app.py` | Application with ProcessManager |
| `assets/uv.exe` | Bundled uv binary for first-run setup |
| `pyproject.toml` | Dependency specification |
| `uv.lock` | Locked dependency versions |
