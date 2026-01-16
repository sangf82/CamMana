# Location Tags - Simplified Version

## ✅ Changes Made

### 1. **Removed Description Field**
- Removed `description` column from `locations.csv`
- Updated `LOCATION_HEADERS` to only include: `id`, `name`, `tag`
- Removed description input/textarea from frontend UI
- Removed description display from location list

### 2. **Simplified to Vietnamese Tag Names**
All tags are now in short Vietnamese:

| Old Tag | New Tag | Purpose |
|---------|---------|---------|
| general | **Cơ bản** | General purpose |
| check-in | **Cổng vào** | Entry gate |
| check-out | **Cổng ra** | Exit gate |
| volume-estimate | **Đo thể tích** | Volume measurement |

## 📊 Current Data Structure

### locations.csv
```csv
id,name,tag
1768207201391,Cổng Nam (Vào),Cổng vào
1768207215054,Cổng Bắc (Ra),Cổng ra
1768207221305,Trạm Cân,Đo thể tích
```

## 🎨 Frontend UI

### Add Location Form
- **Name input**: Tên vị trí (vd: Cổng Nam)
- **Tag dropdown**: 
  - Cơ bản
  - Cổng vào
  - Cổng ra
  - Đo thể tích
- **No description field** ✓

### Location Display
- Shows location name
- Shows tag badge (Vietnamese name)
- No description ✓

## 💻 Python API

### Usage
```python
from backend.detection import get_detection_config

# Use Vietnamese tag names
config = get_detection_config("Cổng vào")
print(config.detection_sequence)
# ['car_detection', 'plate_recognition', 'color_detection', 'wheel_count']

config = get_detection_config("Đo thể tích")
print(config.volume_tolerance)
# 0.05
```

### Tag Enum
```python
class LocationTag(str, Enum):
    CHECK_IN = "Cổng vào"      # Entry gate
    CHECK_OUT = "Cổng ra"       # Exit gate  
    VOLUME_ESTIMATE = "Đo thể tích"  # Volume measurement
    GENERAL = "Cơ bản"          # General purpose
```

## ✅ Test Results

All tests pass with Vietnamese tags:

```
✅ Detection Configurations - OK
✅ Helper Functions - OK  
✅ Locations Data - OK (3 locations with Vietnamese tags)
✅ Camera Grouping - OK
```

## 📝 Files Modified

### Backend
1. `backend/data_process/_common.py` - Removed description from LOCATION_HEADERS
2. `backend/detection/detection_config.py` - Updated to Vietnamese tag names
3. `database/csv_data/locations.csv` - Removed description, updated tags to Vietnamese

### Frontend
1. `frontend/app/(dashboard)/cameras/page.tsx`:
   - Removed description state variables
   - Removed description input/textarea
   - Updated tag options to Vietnamese
   - Simplified location display (no description)

### Tests
1. `tests/test_location_tags.py` - Updated to use Vietnamese tag names

## 🚀 How to Use

### Add New Location (UI)
1. Go to Cameras → Cấu hình
2. Enter name: "Cổng Đông"
3. Select tag: "Cổng vào"
4. Click "Thêm vị trí"

### Get Detection Config (Code)
```python
# Get config using Vietnamese tag
config = get_detection_config("Cổng vào")

# Group cameras by Vietnamese tags
from backend.detection import group_cameras_by_tag
grouped = group_cameras_by_tag(cameras, locations)
entry_cameras = grouped.get('Cổng vào', [])
```

---

**Status**: ✅ Complete and tested  
**Last Updated**: 2026-01-15  
**Version**: 2.0 (Simplified Vietnamese)
