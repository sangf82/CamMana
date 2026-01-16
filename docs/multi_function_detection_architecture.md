# Multi-Function Camera Detection Architecture

## Overview
This document outlines the backend architecture for handling multi-function camera types (e.g., cameras with both `car_detect` and `plate_detect` capabilities) and orchestrating complex detection workflows.

---

## Current System Analysis

### ✅ What You Already Have
1. **Location-Tag Based System**: `Cổng vào`, `Cổng ra`, `Đo thể tích`, `Cơ bản`
2. **Detection Service**: Handles car detection, IoU deduplication, camera pairing (front/side)
3. **Camera Pairing Logic**: `front_cam` + `side_cam` coordination
4. **Parallel AI Processing**: Uses `ThreadPoolExecutor` for plate/color/wheel detection
5. **Smart Functions**: Modular functions listed in frontend (`car_detect`, `plate_detect`, `color_detect`, etc.)

### ⚠️ Current Gaps
1. **No Link Between Camera Types & Functions**: Frontend defines types with functions, but backend doesn't use them yet
2. **Hard-coded Detection Logic**: Current logic is fixed (always runs plate+color+wheel)
3. **No Dynamic Function Selection**: Can't configure "this camera type runs only X+Y functions"
4. **Folder Structure**: Good idea, but needs systematic implementation with UUID → plate_number rename

---

## Proposed Architecture

### 1. **Enhanced Camera Type Schema**

#### Backend Data Structure
```python
# backend/data_process/camtypes.csv
id,name,functions,capture_strategy,ai_config
1,Check-in Scanner,car_detect;plate_detect;color_detect,dual_cam,{"confidence": 0.3}
2,Volume Estimator,car_detect;volume_detect,single_cam,{"confidence": 0.5}
3,Basic Monitor,car_detect;plate_detect,single_cam,{"confidence": 0.4}
```

#### Functions to Detection Model Mapping
```python
FUNCTION_TO_MODEL_MAP = {
    'car_detect': 'CarDetector',
    'plate_detect': 'detect_plate',
    'color_detect': 'detect_colors',
    'wheel_detect': 'count_wheels',
    'box_detect': 'detect_box_dimensions',
    'volume_detect': 'calculate_volume'
}
```

---

### 2. **Dynamic Detection Pipeline**

#### Core Concept
Instead of hard-coded "always detect plate+color+wheel", create a **dynamic pipeline builder** that reads from camera type configuration.

#### Pipeline Orchestrator
```python
# backend/detect_car/pipeline_orchestrator.py

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class DetectionTask:
    """Single detection task in the pipeline"""
    function_id: str          # 'plate_detect'
    model_callable: callable  # detect_plate
    input_source: str         # 'front_cam' or 'side_cam'
    output_key: str           # 'plate'
    parallel_group: int = 1   # Tasks with same group run in parallel

class DetectionPipeline:
    """Builds and executes detection pipelines based on camera type"""
    
    def __init__(self, camera_type_config: Dict[str, Any]):
        self.type_config = camera_type_config
        self.functions = camera_type_config.get('functions', '').split(';')
        self.tasks = self._build_tasks()
    
    def _build_tasks(self) -> List[DetectionTask]:
        """Build task list from function IDs"""
        tasks = []
        
        # Define task configuration
        task_definitions = {
            'car_detect': DetectionTask('car_detect', self._detect_car, 'front_cam', 'vehicle', 1),
            'plate_detect': DetectionTask('plate_detect', detect_plate, 'front_cam', 'plate', 2),
            'color_detect': DetectionTask('color_detect', detect_colors, 'side_cam', 'color', 2),
            'wheel_detect': DetectionTask('wheel_detect', count_wheels, 'side_cam', 'wheel', 2),
            'box_detect': DetectionTask('box_detect', detect_box_dimensions, 'side_cam', 'box', 3),
            'volume_detect': DetectionTask('volume_detect', calculate_volume, 'side_cam', 'volume', 3),
        }
        
        for func_id in self.functions:
            if func_id in task_definitions:
                tasks.append(task_definitions[func_id])
        
        return tasks
    
    def execute(self, front_frame, side_frame=None) -> Dict[str, Any]:
        """Execute all tasks in pipeline with parallelization"""
        frames = {'front_cam': front_frame, 'side_cam': side_frame}
        results = {}
        
        # Group tasks by parallel_group
        grouped_tasks = {}
        for task in self.tasks:
            if task.parallel_group not in grouped_tasks:
                grouped_tasks[task.parallel_group] = []
            grouped_tasks[task.parallel_group].append(task)
        
        # Execute groups sequentially, tasks within group in parallel
        for group_id in sorted(grouped_tasks.keys()):
            group_results = self._execute_parallel_group(
                grouped_tasks[group_id], 
                frames, 
                results
            )
            results.update(group_results)
        
        return results
    
    def _execute_parallel_group(self, tasks: List[DetectionTask], 
                                frames: Dict, 
                                previous_results: Dict) -> Dict[str, Any]:
        """Execute a group of tasks in parallel"""
        group_results = {}
        
        def run_task(task: DetectionTask):
            frame = frames.get(task.input_source)
            if frame is None:
                return {task.output_key: {"success": False, "error": "Frame not available"}}
            
            try:
                result = task.model_callable(frame)
                return {task.output_key: result}
            except Exception as e:
                return {task.output_key: {"success": False, "error": str(e)}}
        
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = [executor.submit(run_task, task) for task in tasks]
            for future in futures:
                try:
                    group_results.update(future.result(timeout=15))
                except Exception as e:
                    print(f"Task execution error: {e}")
        
        return group_results
```

---

### 3. **Enhanced Detection Service**

#### Integration with Type System
```python
# backend/detect_car/detection_service.py (ENHANCED)

class DetectionService:
    def __init__(self):
        self.detector = CarDetector(confidence=0.3, detect_trucks=True)
        self.states: Dict[str, DetectionState] = {}
        self._streamers: Dict[str, Any] = {}
        self._camera_configs: Dict[str, Dict] = {}  # NEW: Store full camera config
    
    def register_camera(self, camera_id: str, streamer: Any, camera_config: Dict):
        """Register camera with full configuration"""
        self._streamers[camera_id] = streamer
        self._camera_configs[camera_id] = camera_config
        if camera_id not in self.states:
            self.states[camera_id] = DetectionState()
    
    def capture_with_detection(self, camera_id: str, force: bool = False) -> Dict[str, Any]:
        """Enhanced capture with dynamic pipeline based on camera type"""
        
        # Get camera configuration
        camera_config = self._camera_configs.get(camera_id, {})
        camera_type_name = camera_config.get('type', '')
        
        # Load camera type configuration from database
        cam_types = data_process.get_cam_types()
        type_config = next((t for t in cam_types if t['name'] == camera_type_name), None)
        
        if not type_config:
            return {"success": False, "error": "Camera type not configured"}
        
        # Get frames
        streamer = self._streamers.get(camera_id)
        if not streamer or not streamer.is_streaming:
            return {"success": False, "error": "Camera not streaming"}
        
        front_frame = streamer.get_capture_frame() or streamer.last_frame
        if front_frame is None:
            return {"success": False, "error": "No frame available"}
        
        # Get paired camera frame if needed
        side_frame = None
        paired_cam_id = self.get_paired_camera(camera_id)
        if paired_cam_id:
            side_streamer = self._streamers.get(paired_cam_id)
            if side_streamer and side_streamer.is_streaming:
                side_frame = side_streamer.get_capture_frame() or side_streamer.last_frame
        
        # Check if 'car_detect' is in functions
        functions = type_config.get('functions', '').split(';')
        if 'car_detect' not in functions:
            return {"success": False, "error": "Camera type doesn't support car detection"}
        
        # Run initial car detection
        result = self.detector.detect(front_frame)
        if not result["detected"]:
            return {"success": False, "skipped": True, "reason": "No vehicle detected"}
        
        # IoU check (anti-duplicate)
        current_bbox = result["bbox"]
        current_time = time.time()
        state = self.states.get(camera_id, DetectionState())
        
        if not force and state.last_bbox:
            iou = self._calculate_iou(current_bbox, state.last_bbox)
            time_diff = current_time - state.last_detection_time
            if iou > IOU_THRESHOLD and time_diff < 30:
                return {
                    "success": False, "skipped": True, 
                    "reason": f"Same car (IoU: {iou:.2f})"
                }
        
        state.last_bbox = current_bbox
        state.last_detection_time = current_time
        self.states[camera_id] = state
        
        # Create capture folder with UUID
        import uuid
        temp_uuid = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        location = camera_config.get('location', 'unknown')
        
        capture_folder = CAPTURE_DIR / f"{temp_uuid}_{location}_{timestamp}"
        capture_folder.mkdir(parents=True, exist_ok=True)
        
        # Save images
        enhanced_front = self._enhance_image(front_frame)
        x1, y1, x2, y2 = current_bbox
        cv2.rectangle(enhanced_front, (x1, y1), (x2, y2), (34, 197, 94), 3)
        front_path = capture_folder / f"{temp_uuid}_front.jpg"
        cv2.imwrite(str(front_path), enhanced_front)
        
        side_path = None
        if side_frame is not None:
            enhanced_side = self._enhance_image(side_frame)
            side_path = capture_folder / f"{temp_uuid}_side.jpg"
            cv2.imwrite(str(side_path), enhanced_side)
        
        # Execute dynamic detection pipeline
        pipeline = DetectionPipeline(type_config)
        detection_results = pipeline.execute(front_frame, side_frame)
        
        # Save JSON outputs for each function
        for func_id in functions:
            if func_id == 'car_detect':
                continue  # Already done
            
            result_key = FUNCTION_TO_OUTPUT_MAP.get(func_id, func_id)
            if result_key in detection_results:
                json_path = capture_folder / f"{temp_uuid}_{func_id}.json"
                with open(json_path, 'w') as f:
                    json.dump(detection_results[result_key], f, indent=2)
        
        # Extract key data
        plate_number = None
        if 'plate' in detection_results:
            plates = detection_results['plate'].get('plates', [])
            plate_number = plates[0] if plates else None
        
        # Rename folder if plate detected
        if plate_number:
            new_folder_name = f"{plate_number}_{location}_{timestamp}"
            new_folder_path = CAPTURE_DIR / new_folder_name
            capture_folder.rename(new_folder_path)
            capture_folder = new_folder_path
            
            # Rename all files
            for old_file in capture_folder.glob(f"{temp_uuid}_*"):
                new_name = old_file.name.replace(temp_uuid, plate_number)
                old_file.rename(capture_folder / new_name)
        
        # Save to database
        detection_data = {
            'folder_path': str(capture_folder),
            'timestamp': timestamp,
            'plate_number': plate_number,
            'location': location,
            'camera_id': camera_id,
            'camera_type': camera_type_name,
            'detection_results': detection_results,
            'confidence': result["confidence"],
            'bbox': current_bbox
        }
        record_id = storage.save_captured_car(detection_data)
        
        return {
            "success": True,
            "record_id": record_id,
            "folder_path": str(capture_folder),
            "plate_number": plate_number,
            "detection_results": detection_results
        }
```

---

### 4. **Folder Structure Best Practices**

#### Recommended Naming Convention
```
database/car_history/
├── 29A12345_CongChinh_15_01_2026_14_30_45/
│   ├── 29A12345_front.jpg
│   ├── 29A12345_side.jpg
│   ├── 29A12345_plate.json
│   ├── 29A12345_color.json
│   ├── 29A12345_wheel.json
│   └── metadata.json
│
├── UNKNOWN_CongPhu_15_01_2026_14_31_20/  # If plate detection failed
│   ├── UNKNOWN_front.jpg
│   ├── UNKNOWN_side.jpg
│   └── ...
```

#### Metadata File Structure
```json
{
  "capture_id": "29A12345_CongChinh_15_01_2026_14_30_45",
  "timestamp": "15/01/2026 14:30:45",
  "location": "Cổng Chính",
  "camera_id": "cam_001",
  "camera_type": "Check-in Scanner",
  "functions_executed": [
    "car_detect",
    "plate_detect",
    "color_detect",
    "wheel_detect"
  ],
  "plate_number": "29A-12345",
  "vehicle_class": "car",
  "confidence": 0.87,
  "bbox": [120, 80, 450, 320],
  "processing_time_ms": 1250
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create `pipeline_orchestrator.py` with `DetectionPipeline` class
- [ ] Map all 6 smart functions to actual model callables
- [ ] Update `DetectionService.register_camera()` to accept full config
- [ ] Test with single-function camera type

### Phase 2: Multi-Function Support (Week 2)
- [ ] Implement parallel task grouping (group 1, 2, 3)
- [ ] Test with 2-function camera (car_detect + plate_detect)
- [ ] Validate JSON output for all functions
- [ ] Add error handling for missing frames

### Phase 3: Folder Management (Week 3)
- [ ] UUID → plate_number rename logic
- [ ] Implement `metadata.json` generation
- [ ] Add cleanup for failed detections
- [ ] Test with paired cameras (front + side)

### Phase 4: API Integration (Week 4)
- [ ] Create `/api/detection/execute/{camera_id}` endpoint
- [ ] Add `/api/detection/pipeline/preview` (show what will run)
- [ ] Frontend integration for multi-function display
- [ ] Real-time detection testing

---

## API Endpoints Design

### New Endpoints

#### 1. Execute Detection
```http
POST /api/detection/execute/{camera_id}
{
  "force": false,  // Bypass IoU check
  "save_images": true,
  "save_json": true
}

Response:
{
  "success": true,
  "record_id": 123,
  "folder_path": "/database/car_history/29A12345_CongChinh_15_01_2026_14_30_45",
  "plate_number": "29A-12345",
  "detection_results": {
    "plate": {"success": true, "plates": ["29A-12345"]},
    "color": {"success": true, "primary_color": "white"},
    "wheel": {"success": true, "wheel_count": 4}
  }
}
```

#### 2. Preview Pipeline
```http
GET /api/detection/pipeline/preview/{camera_id}

Response:
{
  "camera_id": "cam_001",
  "camera_type": "Check-in Scanner",
  "functions": ["car_detect", "plate_detect", "color_detect"],
  "tasks": [
    {"function": "car_detect", "source": "front_cam", "parallel_group": 1},
    {"function": "plate_detect", "source": "front_cam", "parallel_group": 2},
    {"function": "color_detect", "source": "side_cam", "parallel_group": 2}
  ],
  "requires_paired_camera": true,
  "estimated_time_ms": 1500
}
```

#### 3. Get Detection History
```http
GET /api/detection/history/{plate_number}

Response:
{
  "plate_number": "29A-12345",
  "total_detections": 5,
  "detections": [
    {
      "timestamp": "15/01/2026 14:30:45",
      "location": "Cổng Chính",
      "folder_path": "...",
      "functions_executed": ["car_detect", "plate_detect", "color_detect"]
    }
  ]
}
```

---

## Advice & Best Practices

### ✅ DO
1. **Use UUID temporarily, rename to plate_number**: Good for handling detection failures
2. **Parallel execution for independent tasks**: plate_detect (front) + color_detect (side) can run simultaneously
3. **Save JSON for each function**: Makes debugging and re-processing easier
4. **Metadata file**: Essential for quick lookups without parsing all JSONs
5. **Location in folder name**: Helps with organization and search

### ⚠️ CONSIDER
1. **Fallback folder naming**: What if plate detection fails completely? Use `UNKNOWN_{timestamp}` or keep UUID
2. **Retry logic**: If plate detection fails, should you retry with different parameters?
3. **Storage cleanup**: Set retention policy (e.g., delete `UNKNOWN_*` folders after 7 days)
4. **Frame quality check**: Before detection, verify frame isn't blurry/dark
5. **Database indexing**: Index by plate_number, timestamp, location for fast queries

### ❌ DON'T
1. **Don't run volume detection on every car**: Only for specific camera types at loading zones
2. **Don't process side_cam independently**: It should always be triggered by front_cam detection
3. **Don't save raw frames**: Always enhance/optimize before saving (reduces storage by 40%)
4. **Don't hard-code function lists**: Always read from camera type configuration
5. **Don't block on AI processing**: Use async/threading to keep stream responsive

---

## Example: Full Workflow

### Scenario: Car enters "Cổng Chính" gate

1. **Front camera** (type: "Check-in Scanner", functions: `car_detect;plate_detect;color_detect`)
   - Detects car → trigger capture
   
2. **System creates folder**: `c4e8f9a2_CongChinh_15_01_2026_14_30_45`

3. **Captures images**:
   - `c4e8f9a2_front.jpg` (front camera, high-res)
   - `c4e8f9a2_side.jpg` (paired side camera, high-res)

4. **Runs detection pipeline**:
   - Group 1: `car_detect` on front_frame → vehicle found
   - Group 2 (parallel):
     - `plate_detect` on front_frame → "29A-12345"
     - `color_detect` on side_frame → "white"

5. **Saves JSON outputs**:
   - `c4e8f9a2_plate.json`
   - `c4e8f9a2_color.json`

6. **Renames folder & files**: `c4e8f9a2_*` → `29A12345_*`
   - Folder: `29A12345_CongChinh_15_01_2026_14_30_45`
   - Files: `29A12345_front.jpg`, etc.

7. **Saves to database**: Creates record in `captured_cars_15-01-2026.csv`

8. **Returns API response** with detection results

---

## Testing Strategy

### Unit Tests
- Test `DetectionPipeline.execute()` with mock frames
- Test IoU calculation edge cases
- Test folder rename logic

### Integration Tests
- Test with real camera streams
- Test paired camera coordination
- Test all 6 function combinations

### Load Tests
- 10 cars/minute detection rate
- Multiple cameras simultaneously
- Storage space usage monitoring

---

## Performance Optimization

### Current Bottlenecks
1. AI model inference (plate/color/wheel) - **Solution**: Parallel execution (already done)
2. High-res frame capture - **Solution**: Pre-fetch during detection interval
3. File I/O (saving images/JSON) - **Solution**: Async file writing

### Recommended Improvements
1. **Model caching**: Load AI models once, reuse across detections
2. **Frame buffer**: Keep last N high-res frames in memory
3. **Batch processing**: Queue multiple detections, process in batches
4. **GPU acceleration**: If available, use for car/plate detection

---

## Security Considerations

1. **Sanitize plate numbers**: Remove special chars before using in folder names
2. **Access control**: Restrict API endpoints with authentication
3. **Data retention**: Automatically archive/delete old detections
4. **Audit logs**: Track all detection events and folder operations

---

## Conclusion

Your current approach is **solid**! The main improvements needed are:

1. ✅ **Dynamic function selection** based on camera type (not hard-coded)
2. ✅ **Systematic folder structure** with UUID → plate rename
3. ✅ **Pipeline orchestration** for flexible multi-function support
4. ✅ **Metadata tracking** for fast queries and debugging

This architecture allows you to:
- Add new camera types without code changes
- Mix and match any combination of 6+ functions
- Scale to hundreds of cameras
- Debug individual detection failures easily
- Support future features (e.g., "run only plate_detect after 6 PM")
