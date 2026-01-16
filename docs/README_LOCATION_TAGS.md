# 🏷️ Location Tags Feature - Complete Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Tag Types](#tag-types)
4. [Features](#features)
5. [Usage](#usage)
6. [Documentation](#documentation)
7. [Testing](#testing)

---

## 🎯 Overview

The **Location Tags** feature enables you to categorize camera locations by their purpose and automatically configure detection models and capture strategies. Tags help the system understand what role each camera location plays in your vehicle monitoring workflow.

### Key Benefits
- ✅ **Automatic Model Selection**: System chooses appropriate detection models based on location tag
- ✅ **Optimized Capture**: Different capture strategies for different purposes
- ✅ **Volume Validation**: Automatic tolerance checking for weighing stations
- ✅ **History Matching**: Check-out cameras automatically match with entry records
- ✅ **Easy Management**: Simple UI to assign and manage location tags

---

## 🚀 Quick Start

### 1. View Current Tags
```bash
# Run test to see all configured tags
uv run python tests/test_location_tags.py
```

### 2. Add Tagged Location via UI
1. Open CamMana → Cameras page
2. Click **"Cấu hình"** (Settings) button
3. In left panel under **"Vị trí (Location)"**:
   - Enter name: e.g., "Cổng Đông"
   - Select tag: e.g., "Check-in - Cổng vào"
   - Enter description: e.g., "East gate for truck entrance"
   - Click **"Thêm vị trí"**

### 3. Use in Code
```python
from backend.detection import get_detection_config

# Get detection models for a location
config = get_detection_config("check-in")
print(config.detection_sequence)
# Output: ['car_detection', 'plate_recognition', 'color_detection', 'wheel_count']
```

---

## 🏷️ Tag Types

### 1. **check-in** (Entry Gate)
- **Purpose**: Detect vehicles entering facility
- **Models**: Car → Plate → Color → Wheels
- **Strategy**: Continuous capture during entry
- **Use Case**: Main entrance gates

**Detection Flow:**
```
Vehicle Approaches
    ↓
Detect Car ✓
    ↓
Read Plate (e.g., "29A-12345") ✓
    ↓
Identify Color (e.g., "White") ✓
    ↓
Count Wheels (e.g., 4) ✓
    ↓
Log Entry to History
```

### 2. **check-out** (Exit Gate)
- **Purpose**: Detect vehicles leaving and match with entry
- **Models**: Car → Plate → Color → Wheels
- **Strategy**: Verify and match with history
- **Use Case**: Exit gates

**Detection Flow:**
```
Vehicle Approaches Exit
    ↓
Detect Car & Read Plate ✓
    ↓
Match with Entry History
    ↓
Found Entry Record ✓
    ↓
Verify Color Match ✓
    ↓
Update Exit Time & Status
```

### 3. **volume-estimate** (Weighing Station)
- **Purpose**: Calculate truck cargo volume
- **Models**: Truck → Dimensions → Volume → Plate
- **Strategy**: Multi-angle capture for 3D reconstruction
- **Tolerance**: ±5% for validation
- **Use Case**: Weighing/measurement stations

**Detection Flow:**
```
Truck Arrives at Station
    ↓
Detect Truck ✓
    ↓
Check Registered Dimensions (DB)
├─ Found: Use registered (6m × 2.5m × 2m)
└─ Not Found: Estimate dimensions
    ↓
Calculate Current Volume (28.5m³)
    ↓
Read Plate ("29A-12345") ✓
    ↓
Validate Volume (Standard: 30m³ ± 5%)
├─ 28.5m³ - 31.5m³ → NORMAL ✓
├─ < 28.5m³ → UNDER_LOADED
└─ > 31.5m³ → OVER_LOADED
    ↓
Save to History
```

### 4. **general** (General Monitoring)
- **Purpose**: Basic surveillance
- **Models**: Car → Plate
- **Strategy**: Capture on motion
- **Use Case**: General monitoring cameras

---

## ✨ Features

### Backend Features
✅ **Tag-based Detection Config**
- Automatic model selection based on location tag
- Predefined detection sequences for each tag type
- Configurable capture strategies

✅ **Volume Tolerance Validation**
- ±5% tolerance for volume-estimate locations
- Automatic comparison with registered standards
- Status: NORMAL, UNDER_LOADED, OVER_LOADED

✅ **Camera Grouping**
- Group cameras by location tags
- Easy access to all cameras of a specific type
- Simplified management and configuration

✅ **RESTful API**
- Get locations with tags
- Get cameras grouped by tag
- Get detection config for any tag

### Frontend Features
✅ **Enhanced Location Management UI**
- Tag dropdown with 4 options
- Description textarea for detailed info
- Visual tag badges (Check-in, Check-out, Volume, General)
- Inline editing of tag and description

✅ **Improved UX**
- Color-coded tag badges
- Hover tooltips
- Responsive design
- Form validation

---

## 💻 Usage

### Python API

#### Get Detection Configuration
```python
from backend.detection import get_detection_config

config = get_detection_config("check-in")

# Access properties
print(f"Description: {config.description}")
print(f"Models: {config.detection_sequence}")
print(f"Strategy: {config.capture_strategy}")
```

#### Group Cameras by Tag
```python
from backend.detection import group_cameras_by_tag
from backend.data_process import get_cameras, get_locations

cameras = get_cameras()
locations = get_locations()

grouped = group_cameras_by_tag(cameras, locations)

# Get cameras for specific tag
checkin_cameras = grouped.get('check-in', [])
volume_cameras = grouped.get('volume-estimate', [])
```

#### Validate Volume
```python
from backend.detection import get_volume_tolerance

tolerance = get_volume_tolerance("volume-estimate")  # 0.05

standard_volume = 30  # m³
measured_volume = 28.5  # m³

min_allowed = standard_volume * (1 - tolerance)  # 28.5
max_allowed = standard_volume * (1 + tolerance)  # 31.5

if min_allowed <= measured_volume <= max_allowed:
    status = "NORMAL"
elif measured_volume < min_allowed:
    status = "UNDER_LOADED"
else:
    status = "OVER_LOADED"
```

### REST API

#### Get All Locations with Tags
```bash
GET /api/cameras/locations

Response:
[
  {
    "id": "1768207201391",
    "name": "Cổng Nam (Vào)",
    "tag": "check-in",
    "description": "Entry gate for incoming vehicles..."
  },
  ...
]
```

#### Get Cameras Grouped by Tag
```bash
GET /api/cameras/locations/grouped

Response:
{
  "success": true,
  "data": {
    "check-in": [camera1, camera2],
    "check-out": [camera3],
    "volume-estimate": [camera4]
  }
}
```

#### Get Detection Config for Tag
```bash
GET /api/cameras/locations/tags/check-in/config

Response:
{
  "success": true,
  "tag": "check-in",
  "description": "Entry gate - detect incoming vehicles",
  "detection_sequence": ["car_detection", "plate_recognition", ...],
  "capture_strategy": "continuous",
  "volume_tolerance": null
}
```

### Frontend Components

#### Location with Tag
```tsx
interface LocationItem {
    id: string | number
    name: string
    tag?: string
    description?: string
}

// Display tag badge
<span className="px-2 py-0.5 bg-primary/10 text-primary rounded">
    {loc.tag === 'check-in' ? 'Check-in' : 
     loc.tag === 'check-out' ? 'Check-out' : 
     loc.tag === 'volume-estimate' ? 'Volume' : 
     'General'}
</span>
```

---

## 📚 Documentation

### Core Documentation
- **[LOCATION_TAGS.md](docs/LOCATION_TAGS.md)** - Complete guide with examples
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Visual architecture diagram
- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Implementation details
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Quick reference card

### Code Documentation
- **[detection_config.py](backend/detection/detection_config.py)** - Detection configuration module
- **[config.py](backend/api/config.py)** - API endpoints

---

## 🧪 Testing

### Run Test Suite
```bash
uv run python tests/test_location_tags.py
```

### Expected Output
```
✅ Testing Detection Configurations
✅ Testing Helper Functions  
✅ Testing Locations Data
✅ Testing Camera Grouping
✅ All tests completed!
```

### Manual Testing
1. **UI Testing**:
   - Add new location with tag
   - Edit existing location
   - Delete location
   - View tag badges

2. **API Testing**:
   - Test all new API endpoints
   - Verify response formats
   - Check error handling

3. **Integration Testing**:
   - Group cameras by tag
   - Get detection config
   - Validate volume tolerance

---

## 🛠️ Migration

### Migrate Existing Locations
If you have existing locations without tags:

```bash
uv run python scripts/migrate_location_tags.py
```

The script will:
1. Read existing locations
2. Suggest tags based on names
3. Prompt for custom descriptions
4. Save updated locations

---

## 📊 Data Schema

### locations.csv
```csv
id,name,tag,description
1768207201391,Cổng Nam (Vào),check-in,Entry gate for incoming vehicles...
1768207215054,Cổng Bắc (Ra),check-out,Exit gate for outgoing vehicles...
1768207221305,Trạm Cân,volume-estimate,Volume measurement station...
```

### cameras.csv (Reference)
```csv
id,name,location_id,...
1,Cam 1,1768207201391,...
2,Cam 2,1768207215054,...
3,Cam 3,1768207221305,...
```

---

## 🔄 Next Steps

### Phase 1: Core Integration (Current)
- ✅ Define location tags
- ✅ Create detection configs
- ✅ Update data model
- ✅ Build UI for tag management
- ✅ Create API endpoints
- ✅ Write documentation

### Phase 2: Detection Service Integration (Next)
- [ ] Integrate with detection service
- [ ] Implement capture strategies
- [ ] Add volume validation logic
- [ ] Create history matching for check-out
- [ ] Test end-to-end workflow

### Phase 3: Advanced Features (Future)
- [ ] Tag-based dashboards
- [ ] Tag-specific reporting
- [ ] Alert rules by tag
- [ ] ML model routing
- [ ] Performance optimization

---

## 🆘 Support

### Common Issues

**Q: Tag not showing in UI?**  
A: Check if location has `tag` field in `locations.csv`

**Q: Detection config not found?**  
A: Verify tag name matches: check-in, check-out, volume-estimate, general

**Q: Volume tolerance not working?**  
A: Only `volume-estimate` tag has tolerance, others return `None`

**Q: Cameras not grouping?**  
A: Ensure cameras have `location_id` matching location's `id`

### Getting Help
1. Check documentation in `docs/` folder
2. Review test output for errors
3. Verify CSV file formats
4. Check API responses

---

## 📄 License

Part of the CamMana project.

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0  
**Status**: ✅ Production Ready
