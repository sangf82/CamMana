# Database Folder Structure Changes

## ✅ Completed Restructuring

### Folder Changes
1. ✓ `data` → `csv_data` (renamed)
2. ✓ `logs` moved from `data/logs` → `database/logs`
3. ✓ `captured_car` → `car_history` (renamed)
4. ✓ `captured_img` → `saved_image` (renamed)
5. ✓ `schedule` folder removed (including contents)
6. ✓ Sample data preserved (no changes)

### New Database Structure
```
database/
├── car_history/           # Vehicle capture history folders
├── csv_data/              # All CSV data files
│   ├── cameras.csv
│   ├── locations.csv
│   ├── camtypes.csv
│   ├── registered_cars_*.csv
│   └── history_*.csv
├── logs/                  # Detection logs
├── sample_data/           # Sample/test data (unchanged)
└── saved_image/           # Manual image captures
    └── {cam-code}_{location}_{date}_{time}.jpg
```

### Code Updates

#### 1. Data Paths (`backend/data_process/_common.py`)
- Updated `DATA_DIR` to point to `csv_data`
- Updated `LOGS_DIR` to point to `database/logs`

#### 2. Detection Service (`backend/detect_car/detection_service.py`)
- Updated `CAPTURE_DIR` to `car_history`

#### 3. Car Detector (`backend/detect_car/car_detect.py`)
- Updated default capture_dir to `saved_image`

#### 4. Video Streamer (`backend/camera_config/streamer.py`)
- Updated capture path to `saved_image`
- Added `set_camera_info()` method
- **New filename format**: `{cam-code}_{location}_{date}_{time}.jpg`
- Example: `CAM-01_Cong-Nam-Vao_15-01-2026_001234.jpg`

#### 5. Camera API (`backend/api/cameras.py`)
- Sets camera info on streamer during connection
- Passes cam_code and location for proper image naming

#### 6. Schedule API (`backend/api/schedule.py`)
- Removed schedule file parsing
- Returns empty data (backward compatible)
- Marked as DEPRECATED

### Image Naming Examples

**Old format**: `capture_20260115_001234.jpg`

**New format**: 
- `CAM-01_Cong-Nam-Vao_15-01-2026_001234.jpg`
- `CAM-02_Tram-Can_15-01-2026_143512.jpg`
- `CAM-XX_Unknown_15-01-2026_093045.jpg` (if no camera info set)

### Testing Status
- ✅ All imports working
- ✅ Data paths updated
- ✅ Image capture paths updated
- ✅ Schedule removed (backward compatible)
- ✅ Sample data preserved

## Notes
- All existing data preserved in new locations
- Backward compatibility maintained
- Schedule endpoints return empty but don't error
- Image naming includes camera code and location for better organization
