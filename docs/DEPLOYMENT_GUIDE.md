# CamMana Deployment Guide

## Building the Application

### Prerequisites
- Python 3.12+
- Node.js 18+
- uv package manager
- Git

### Build Steps

1. **Install Build Dependencies**
   ```bash
   # Install PyInstaller
   pip install -r requirements-build.txt
   
   # Install Python dependencies
   uv sync
   
   # Install frontend dependencies
   cd frontend
   npm install
   cd ..
   ```

2. **Build the Executable**
   ```bash
   uv run python build.py
   ```

3. **Distribution Package**
   The build script creates a `dist/CamMana_Release/` folder containing:
   - `CamMana.exe` - Main executable
   - `README.txt` - User installation guide
   - `.env.example` - Configuration template

## Package Optimizations

### Backend Dependencies Optimized
- ✅ Removed `modal` (not needed for production)
- ✅ Removed `pyinstaller` from runtime (build-only)
- ✅ Optimized YOLO/Ultralytics imports
- ✅ Added ONNX Runtime for faster inference
- ✅ Reduced package size by ~200MB

### Frontend Dependencies
- ✅ Using Next.js static export
- ✅ Minimal runtime bundle
- ✅ All UI libraries tree-shaken
- ✅ Production build optimizations

## Configurable Data Directory

### Default Behavior
By default, CamMana stores all data in:
```
<exe_location>/database/
├── csv_data/          # CSV files (cameras, history, etc.)
├── car_history/       # Evidence images and JSONs
├── backgrounds/       # Static and processed backgrounds
├── calibration/       # Camera calibration files
├── captured_img/      # Temporary captures
├── logs/              # Application logs
└── report/            # Generated reports
```

### Custom Data Directory

Users can configure a custom data directory by:

**Method 1: Environment Variable**
```bash
# Windows CMD
set CAMMANA_DATA_DIR=C:\CamMana_Data

# Windows PowerShell
$env:CAMMANA_DATA_DIR="C:\CamMana_Data"

# Run application
CamMana.exe
```

**Method 2: .env File** (Recommended)
Create a `.env` file next to `CamMana.exe`:
```env
CAMMANA_DATA_DIR=C:\CamMana_Data
HOST=0.0.0.0
PORT=8000
CAMERA_DEFAULT_USER=admin
CAMERA_DEFAULT_PASSWORD=yourpassword
```

### Multi-Instance Deployment

You can run multiple CamMana instances with different data directories:

```
Location 1:
C:\CamMana_Gate1\
├── CamMana.exe
├── .env  # CAMMANA_DATA_DIR=D:\Data\Gate1
└── database/  # (optional, if .env not used)

Location 2:
C:\CamMana_Gate2\
├── CamMana.exe
├── .env  # CAMMANA_DATA_DIR=D:\Data\Gate2
└── database/
```

## Deployment Scenarios

### Scenario 1: Single PC Deployment
```
1. Extract CamMana_Release.zip to C:\CamMana
2. Run CamMana.exe
3. Data stored in C:\CamMana\database\
```

### Scenario 2: Network Storage
```
1. Install CamMana on local PC
2. Create .env file:
   CAMMANA_DATA_DIR=\\NetworkShare\CamMana_Data
3. All data stored on network drive
4. Multiple PCs can access same data (use Master/Client sync)
```

### Scenario 3: Master/Client Architecture
```
Master PC:
- Full installation with database
- sync_config.json: {"is_destination": true, "remote_url": null}
- Advertises via Zeroconf

Client PCs:
- Full installation
- sync_config.json: {"is_destination": false, "remote_url": "http://master-ip:8000"}
- Local data syncs to Master
```

## System Requirements

### Minimum
- OS: Windows 10/11 (64-bit)
- CPU: Intel i3 or equivalent
- RAM: 4GB
- Storage: 500MB + data
- Network: 100Mbps

### Recommended
- OS: Windows 11 (64-bit)
- CPU: Intel i5 or better
- RAM: 8GB
- Storage: 10GB SSD
- Network: 1Gbps

## First-Time Setup

1. **Launch Application**
   - Double-click `CamMana.exe`
   - Wait for server to start (~10 seconds)
   - Browser opens automatically

2. **Initial Configuration**
   - Go to Settings → Locations
   - Add your gates/checkpoints
   - Go to Settings → Cameras
   - Add and connect cameras
   - Configure camera types and functions

3. **Optional: Import Registered Vehicles**
   - Go to Registered Vehicles
   - Click Import
   - Upload Excel/CSV file

4. **Optional: Add Calibration Files**
   - Place camera calibration files in `database/calibration/`
   - Format: `calib_side_{cam_id}.json`, `calib_top_{cam_id}.json`

## Troubleshooting

### Application Won't Start
```
Check:
1. Windows Defender/Antivirus blocking exe
2. Port 8000 already in use
3. Check logs in database/logs/
```

### Data Not Persisting
```
Check:
1. Folder permissions on data directory
2. .env file syntax (no quotes around paths)
3. Path exists and is writable
```

### Camera Connection Issues
```
Check:
1. Camera IP reachable (ping test)
2. ONVIF enabled on camera
3. Correct username/password
4. Firewall rules allowing traffic
```

## Backup Strategy

### Automatic Retention
- CSV files: 2 days rotation
- Car history folders: 2 days rotation
- Logs: Manual cleanup

### Manual Backup
```bash
# Backup entire database
xcopy /E /I /Y database D:\Backups\CamMana_%DATE%

# Backup only CSVs
xcopy /Y database\csv_data\*.csv D:\Backups\CSV\
```

### Network Backup
Point `CAMMANA_DATA_DIR` to a backed-up network location.

## Performance Tips

1. **SSD Storage**: Use SSD for database directory
2. **Network**: Gigabit for multiple cameras
3. **Cleanup**: Regular deletion of old car_history folders
4. **Cameras**: Limit to 4-6 per PC
5. **Resolution**: Use 1080p max for volume cameras

## Support

For issues, check:
1. `database/logs/` for error messages
2. System Event Viewer
3. Network connectivity
4. Camera firmware updates

---

**Version**: 2.0.0  
**Build Date**: Generated by build.py  
**Platform**: Windows 10/11 64-bit
