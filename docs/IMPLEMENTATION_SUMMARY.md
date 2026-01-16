# Location Tags Feature - Implementation Summary

## Overview
We have successfully implemented a comprehensive location tagging system for the CamMana project. This system allows you to categorize camera locations by their purpose and automatically configure detection models and capture strategies based on these tags.

## What Was Implemented

### 1. Backend - Data Model Updates
✅ **Updated `backend/data_process/_common.py`**
- Added `tag` and `description` fields to `LOCATION_HEADERS`
- Locations now support: `id`, `name`, `tag`, `description`

✅ **Updated `database/csv_data/locations.csv`**
- Added tag and description columns
- Populated existing locations with appropriate tags:
  - Cổng Nam (Vào): `check-in`
  - Cổng Bắc (Ra): `check-out`
  - Trạm Cân: `volume-estimate`

### 2. Backend - Detection Configuration Module
✅ **Created `backend/detection/detection_config.py`**
- Defined `LocationTag` enum with 4 tags:
  - `check-in` - Entry gate cameras
  - `check-out` - Exit gate cameras
  - `volume-estimate` - Volume measurement stations
  - `general` - General purpose cameras

- Created `DetectionConfig` dataclass with:
  - `detection_sequence` - Ordered list of models to run
  - `capture_strategy` - How to capture images
  - `volume_tolerance` - For volume-estimate locations (±5%)

- Implemented helper functions:
  - `get_detection_config(tag)` - Get config for a tag
  - `get_camera_detection_models(tag)` - Get model sequence
  - `get_capture_strategy(tag)` - Get capture strategy
  - `get_volume_tolerance(tag)` - Get volume tolerance
  - `group_cameras_by_tag(cameras, locations)` - Group cameras by tag

✅ **Created `backend/detection/__init__.py`**
- Exports all detection config functions

### 3. Backend - API Endpoints
✅ **Updated `backend/api/config.py`**
- Added three new endpoints:

1. **GET `/api/cameras/locations/grouped`**
   - Returns cameras grouped by location tags
   - Example response:
   ```json
   {
     "success": true,
     "data": {
       "check-in": [camera1, camera2],
       "check-out": [camera3],
       "volume-estimate": [camera4]
     }
   }
   ```

2. **GET `/api/cameras/locations/tags/{tag}/config`**
   - Returns detection config for a specific tag
   - Example: `/api/cameras/locations/tags/check-in/config`

3. **GET `/api/cameras/locations/tags/all/configs`**
   - Returns all tag configurations at once

### 4. Frontend - UI Updates
✅ **Updated `frontend/app/(dashboard)/cameras/page.tsx`**

**Interface Updates:**
- Extended `LocationItem` interface to include `tag` and `description`
- Added state variables for tag and description management

**Add Location Form:**
- Added tag dropdown with 4 options (general, check-in, check-out, volume-estimate)
- Added description textarea
- Improved form layout with better UX

**Edit Location Form:**
- Added tag dropdown in edit mode
- Added description textarea in edit mode
- Updated save/edit handlers to include tag and description

**Location Display:**
- Shows tag badge (Check-in, Check-out, Volume, General)
- Displays description below location name
- Color-coded tag badges

### 5. Documentation
✅ **Created `docs/LOCATION_TAGS.md`**
- Comprehensive guide on how to use location tags
- Detailed explanation of each tag type
- Python and TypeScript usage examples
- Database schema documentation
- API endpoint documentation
- Implementation checklist
- Next steps roadmap

## Location Tag Definitions

### 1. **check-in** - Entry Gate
- **Purpose**: Detect incoming vehicles
- **Detection Sequence**:
  1. Car detection (is there a car?)
  2. Plate recognition (read license plate)
  3. Color detection (identify car color)
  4. Wheel count (count wheels)
- **Capture Strategy**: `continuous` - Capture continuously while car enters
- **Use Case**: Main entrance gates to detect and log incoming vehicles

### 2. **check-out** - Exit Gate
- **Purpose**: Detect outgoing vehicles and match with history
- **Detection Sequence**:
  1. Car detection
  2. Plate recognition
  3. Color detection
  4. Wheel count
- **Capture Strategy**: `verify_and_match` - Capture and match with entry history
- **Use Case**: Exit gates to verify vehicles and update status

### 3. **volume-estimate** - Volume Measurement
- **Purpose**: Calculate truck load volume
- **Detection Sequence**:
  1. Truck detection
  2. Dimension estimation (if not in DB)
  3. Volume calculation (material in truck box)
  4. Plate recognition
- **Capture Strategy**: `multi_angle` - Multiple angles for 3D reconstruction
- **Volume Tolerance**: ±5% for validation
- **Use Case**: Weighing stations to measure cargo volume

### 4. **general** - General Purpose
- **Purpose**: Basic monitoring
- **Detection Sequence**:
  1. Car detection
  2. Plate recognition
- **Capture Strategy**: `on_motion`
- **Use Case**: General monitoring cameras

## How to Use

### Adding a New Location with Tag

1. **Via Frontend (Recommended)**:
   - Go to Cameras page → Click "Cấu hình" button
   - In the left panel under "Vị trí (Location)":
     - Enter location name (e.g., "Cổng Đông")
     - Select tag from dropdown (e.g., "Check-in - Cổng vào")
     - Enter description (e.g., "East gate for truck entrance")
     - Click "Thêm vị trí"

2. **Via API**:
   ```bash
   POST /api/cameras/locations
   Body: [
     {
       "id": "...",
       "name": "Cổng Đông",
       "tag": "check-in",
       "description": "East gate for truck entrance"
     }
   ]
   ```

### Getting Cameras by Tag (Python)

```python
from backend.detection import group_cameras_by_tag
from backend.data_process import get_cameras, get_locations

cameras = get_cameras()
locations = get_locations()

# Group cameras by tag
grouped = group_cameras_by_tag(cameras, locations)

# Get all check-in cameras
checkin_cams = grouped.get('check-in', [])

# Get all volume-estimate cameras
volume_cams = grouped.get('volume-estimate', [])
```

### Getting Detection Config for a Tag

```python
from backend.detection import get_detection_config

config = get_detection_config("check-in")
print(f"Models to run: {config.detection_sequence}")
print(f"Capture strategy: {config.capture_strategy}")
```

## Next Steps (TODO)

### Immediate Tasks:
1. **Integrate with Detection Service**
   - Modify detection service to use `get_camera_detection_models()` 
   - Route detections based on location tag
   - Implement capture strategies

2. **Implement Capture Strategies**
   - `capture_continuous()` for check-in
   - `capture_and_match()` for check-out
   - `capture_multi_angle()` for volume-estimate
   - `on_motion()` for general

3. **Volume Validation Logic**
   - Implement volume tolerance checking
   - Compare measured vs standard volume
   - Alert on out-of-range volumes

4. **History Matching for Check-out**
   - Match detected plate with entry history
   - Update status when vehicle exits
   - Calculate dwell time

### Future Enhancements:
- Add more location tags as needed
- Create UI dashboard showing cameras by tag
- Add tag-based reporting
- Implement tag-based alert rules
- Add ML model routing based on tags

## Files Modified

### Backend:
1. `backend/data_process/_common.py` - Updated LOCATION_HEADERS
2. `backend/detection/detection_config.py` - NEW: Detection config module
3. `backend/detection/__init__.py` - NEW: Module exports
4. `backend/api/config.py` - Added 3 new endpoints
5. `database/csv_data/locations.csv` - Added tag and description columns

### Frontend:
1. `frontend/app/(dashboard)/cameras/page.tsx` - Enhanced location management UI

### Documentation:
1. `docs/LOCATION_TAGS.md` - NEW: Comprehensive guide
2. `docs/IMPLEMENTATION_SUMMARY.md` - NEW: This file

## Testing

### Manual Testing Steps:
1. **Test Location CRUD**:
   - ✅ Add new location with tag
   - ✅ Edit location tag and description
   - ✅ Delete location
   - ✅ View location with tag badge

2. **Test API Endpoints**:
   ```bash
   # Get all locations (should include tag and description)
   GET http://localhost:8000/api/cameras/locations
   
   # Get cameras grouped by tag
   GET http://localhost:8000/api/cameras/locations/grouped
   
   # Get config for a tag
   GET http://localhost:8000/api/cameras/locations/tags/check-in/config
   
   # Get all tag configs
   GET http://localhost:8000/api/cameras/locations/tags/all/configs
   ```

3. **Test Python Functions**:
   ```python
   from backend.detection import get_detection_config, group_cameras_by_tag
   
   # Test get config
   config = get_detection_config("check-in")
   assert config.tag == "check-in"
   assert "car_detection" in config.detection_sequence
   
   # Test grouping
   from backend.data_process import get_cameras, get_locations
   grouped = group_cameras_by_tag(get_cameras(), get_locations())
   assert isinstance(grouped, dict)
   ```

## Benefits

✅ **Centralized Configuration**: All detection logic in one place
✅ **Type-Safe**: Using Python enums and dataclasses
✅ **Easy to Extend**: Add new tags by extending the enum
✅ **Well-Documented**: Clear purpose for each location
✅ **Frontend Support**: Complete UI for tag management
✅ **API Support**: RESTful endpoints for programmatic access

## Support

For questions or issues:
1. Check `docs/LOCATION_TAGS.md` for detailed usage
2. Review this implementation summary
3. Check the code comments in `backend/detection/detection_config.py`

---

**Implementation Date**: 2026-01-15
**Status**: ✅ Complete - Ready for Integration
**Next Phase**: Detection Service Integration
