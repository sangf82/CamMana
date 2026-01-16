# Location Tags Implementation Guide

## Overview
This document explains how to use location tags in the CamMana system to configure detection models and capture strategies based on camera location purposes.

## Location Tags

### Available Tags:
1. **`check-in`** - Entry gate cameras
   - **Purpose**: Detect vehicles entering the facility
   - **Detection Sequence**:
     1. Car detection (detect if there's a car)
     2. Plate recognition (read license plate)
     3. Color detection (identify car color)
     4. Wheel count (count number of wheels)
   - **Capture Strategy**: `continuous` - Capture continuously until car enters fully
   
2. **`check-out`** - Exit gate cameras
   - **Purpose**: Detect vehicles leaving and match with entry history
   - **Detection Sequence**:
     1. Car detection (detect if there's a car)
     2. Plate recognition (read license plate)
     3. Color detection (identify car color)
     4. Wheel count (count number of wheels)
   - **Capture Strategy**: `verify_and_match` - Capture and match with entry history
   - **Additional Logic**: Match detected plate with entry history to update status

3. **`volume-estimate`** - Volume measurement stations
   - **Purpose**: Calculate truck box dimensions and material volume
   - **Detection Sequence**:
     1. Truck detection (detect truck)
     2. Dimension estimation (estimate truck box dimensions if not in DB)
     3. Volume calculation (calculate material volume in truck box)
     4. Plate recognition (associate with vehicle record)
   - **Capture Strategy**: `multi_angle` - Capture from multiple angles for 3D reconstruction
   - **Volume Tolerance**: ±5% (0.05) tolerance for volume estimation
   - **Special Logic**:
     - If truck dimensions not in DB, calculate and store
     - Compare measured volume with registered standard volume
     - Use tolerance range for validation

4. **`general`** - General purpose cameras
   - **Purpose**: Basic monitoring and detection
   - **Detection Sequence**:
     1. Car detection
     2. Plate recognition
   - **Capture Strategy**: `on_motion` - Capture on motion detection

## Usage Examples

### Backend - Python

#### 1. Get detection configuration for a location:

```python
from backend.detection import get_detection_config, get_camera_detection_models

# Get complete configuration
config = get_detection_config("check-in")
print(f"Description: {config.description}")
print(f"Sequence: {config.detection_sequence}")
print(f"Strategy: {config.capture_strategy}")

# Get just the model sequence
models = get_camera_detection_models("check-in")
# Returns: ["car_detection", "plate_recognition", "color_detection", "wheel_count"]
```

#### 2. Group cameras by their location tags:

```python
from backend.detection import group_cameras_by_tag
from backend.data_process import get_cameras, get_locations

cameras = get_cameras()
locations = get_locations()

# Group cameras by tag
grouped = group_cameras_by_tag(cameras, locations)

# Access cameras by tag
checkin_cameras = grouped.get('check-in', [])
checkout_cameras = grouped.get('check-out', [])
volume_cameras = grouped.get('volume-estimate', [])
```

#### 3. Apply detection logic based on tag:

```python
from backend.detection import get_detection_config, get_capture_strategy

def process_camera_frame(camera, frame, location_tag):
    """Process camera frame based on location tag"""
    
    # Get detection models for this location
    config = get_detection_config(location_tag)
    
    # Run detection models in sequence
    results = {}
    for model_name in config.detection_sequence:
        if model_name == "car_detection":
            results['car'] = detect_car(frame)
        elif model_name == "plate_recognition":
            if results.get('car'):  # Only if car detected
                results['plate'] = recognize_plate(frame)
        elif model_name == "color_detection":
            if results.get('car'):
                results['color'] = detect_color(frame)
        elif model_name == "wheel_count":
            if results.get('car'):
                results['wheels'] = count_wheels(frame)
        elif model_name == "dimension_estimation":
            if results.get('truck'):
                results['dimensions'] = estimate_dimensions(frame)
        elif model_name == "volume_calculation":
            if results.get('dimensions'):
                results['volume'] = calculate_volume(frame, results['dimensions'])
    
    # Apply capture strategy
    strategy = config.capture_strategy
    if strategy == "continuous":
        capture_continuous(camera, results)
    elif strategy == "verify_and_match":
        capture_and_match(camera, results)
    elif strategy == "multi_angle":
        capture_multi_angle(camera, results)
    
    return results


def handle_volume_measurement(plate, measured_volume, location_tag):
    """Handle volume measurement with tolerance"""
    from backend.detection import get_volume_tolerance
    
    tolerance = get_volume_tolerance(location_tag)  # Returns 0.05 for volume-estimate
    
    # Get registered car data
    car = get_registered_car(plate)
    if car and car.get('standard_volume'):
        standard = float(car['standard_volume'])
        min_vol = standard * (1 - tolerance)
        max_vol = standard * (1 + tolerance)
        
        if min_vol <= measured_volume <= max_vol:
            return "NORMAL", f"Volume within acceptable range (±{tolerance*100}%)"
        else:
            return "ABNORMAL", f"Volume outside range. Expected: {standard}±{tolerance*100}%, Got: {measured_volume}"
    else:
        # No standard volume, use measured as baseline
        return "BASELINE", f"No standard volume. Using measured: {measured_volume}"
```

### Frontend - TypeScript/React

#### 1. Display location tags in UI:

```typescript
interface LocationItem {
    id: string | number
    name: string
    tag?: string  // "check-in" | "check-out" | "volume-estimate" | "general"
    description?: string
}

// Display tag badge
function LocationBadge({ tag }: { tag: string }) {
    const tagLabels = {
        'check-in': 'Check-in',
        'check-out': 'Check-out',
        'volume-estimate': 'Volume',
        'general': 'General'
    }
    
    return (
        <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs font-medium">
            {tagLabels[tag] || 'General'}
        </span>
    )
}
```

#### 2. Add tag selector in location form:

```tsx
<select 
    className="w-full p-2 bg-background border rounded"
    value={locationTag}
    onChange={(e) => setLocationTag(e.target.value)}
>
    <option value="general">General - Mục đích chung</option>
    <option value="check-in">Check-in - Cổng vào</option>
    <option value="check-out">Check-out - Cổng ra</option>
    <option value="volume-estimate">Volume-estimate - Đo thể tích</option>
</select>
```

## Database Schema

### locations.csv
```csv
id,name,tag,description
1768207201391,Cổng Nam (Vào),check-in,Entry gate for incoming vehicles - detects car first then plate/color/wheels
1768207215054,Cổng Bắc (Ra),check-out,Exit gate for outgoing vehicles - matches with entry history
1768207221305,Trạm Cân,volume-estimate,Volume measurement station - calculates truck dimensions and load volume
```

## API Endpoints

### Get locations with tags:
```
GET /api/cameras/locations
Response: [
    {
        "id": "1768207201391",
        "name": "Cổng Nam (Vào)",
        "tag": "check-in",
        "description": "Entry gate for incoming vehicles..."
    },
    ...
]
```

### Save locations:
```
POST /api/cameras/locations
Body: [
    {
        "id": "1768207201391",
        "name": "Cổng Nam (Vào)",
        "tag": "check-in",
        "description": "Entry gate for incoming vehicles..."
    }
]
```

## Implementation Checklist

- [x] Define location tags enum (check-in, check-out, volume-estimate, general)
- [x] Create detection configuration for each tag
- [x] Update location data model to include tag and description
- [x] Update CSV headers to include tag and description
- [x] Update frontend UI for tag selection
- [x] Create helper functions to get detection config by tag
- [x] Create function to group cameras by location tag
- [ ] Integrate with detection service to use tag-based logic
- [ ] Implement capture strategies (continuous, verify_and_match, multi_angle)
- [ ] Add volume tolerance validation for volume-estimate locations
- [ ] Create API endpoints to get cameras grouped by tag
- [ ] Update documentation

## Next Steps

1. **Integrate with Detection Service**: Modify the detection service to use `get_camera_detection_models()` to determine which models to run based on location tag.

2. **Implement Capture Strategies**: Create capture strategy handlers:
   - `capture_continuous()` - For check-in cameras
   - `capture_and_match()` - For check-out cameras
   - `capture_multi_angle()` - For volume-estimate cameras

3. **Add History Matching**: For check-out cameras, implement logic to match detected plates with entry history.

4. **Volume Validation**: For volume-estimate cameras, implement volume tolerance checking using `get_volume_tolerance()`.

5. **API Enhancement**: Add endpoint to get cameras grouped by tag for easier management.

## Benefits

1. **Centralized Configuration**: All detection logic for a location type is defined in one place
2. **Easy to Extend**: Add new location tags by adding to the `LocationTag` enum
3. **Flexible**: Each location can have its own detection sequence and capture strategy
4. **Type-Safe**: Using enums and dataclasses ensures type safety
5. **Well-Documented**: Purpose of each location is clear from tag and description
