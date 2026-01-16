# Files to Delete - Complete Removal Plan

## Old Files Being Deleted

### `backend/detect_car/` folder - DELETE ALL:
1. ❌ `car_detect.py` (8,806 bytes) - ✅ Migrated to `car_process/functions/car_detection.py`
2. ❌ `info_detect.py` (5,798 bytes) - ✅ Migrated to `plate/color/wheel_detection.py`
3. ❌ `volume_detect.py` (4,371 bytes) - ✅ Migrated to `volume_detection.py`
4. ❌ `pipeline_orchestrator.py` (13,492 bytes) - ✅ Replaced by `core/orchestrator.py`
5. ❌ `detection_service.py` (15,354 bytes) - ✅ Migrated to `car_process/core/detection_service.py`
6. ❌ `__init__.py` (878 bytes) - ✅ No longer needed (compatibility layer removed)

### `backend/detection/` folder - DELETE ALL:
1. ❌ `detection_config.py` (5,936 bytes) - ✅ Migrated to `config/location_config.py`
2. ❌ `__init__.py` (1,645 bytes) - ✅ No longer needed (compatibility layer removed)

## Total Space Saved
**~56 KB of duplicate/old code removed**

## All imports updated to use:
✅ `backend/car_process/` - New unified module
✅ `backend/__init__.py` - Imports from car_process
✅ `backend/api/cameras.py` - Uses car_process
✅ `backend/api/pipeline.py` - Uses car_process

## Folders to Remove
- `backend/detect_car/` (entire folder)
- `backend/detection/` (entire folder)
