# Refactoring Plan: Merge to `backend/car_process/`

## Your Proposal Analysis

### ✅ **EXCELLENT IDEA!** Here's why:

1. **Better Organization**: One file per detection function makes code easier to find and maintain
2. **Single Source of Truth**: All detection logic in one place
3. **Clearer Responsibilities**: Each file has a single, well-defined purpose
4. **Easier Testing**: Test individual functions in isolation
5. **Scalability**: Easy to add new detection functions without cluttering existing files
6. **Reduced Confusion**: No more "which folder should this go in?"

---

## Proposed New Structure

### 📁 `backend/car_process/` (New Unified Folder)

```
backend/car_process/
├── __init__.py                      # Package exports
│
├── functions/                       # Detection Functions (one per file)
│   ├── __init__.py
│   ├── car_detection.py            # Vehicle detection (YOLO)
│   ├── plate_detection.py          # License plate recognition
│   ├── color_detection.py          # Vehicle color analysis
│   ├── wheel_detection.py          # Wheel/axle counting
│   ├── box_detection.py            # Truck box dimensions (TODO)
│   └── volume_detection.py         # Volume calculation
│
├── config/                          # Configuration & Strategy
│   ├── __init__.py
│   ├── function_config.py          # Function definitions & metadata
│   ├── location_config.py          # Location tag strategies
│   └── camera_type_config.py       # Camera type presets
│
├── core/                            # Core Orchestration
│   ├── __init__.py
│   ├── orchestrator.py             # Main detection orchestrator
│   ├── pipeline.py                 # Pipeline executor (from pipeline_orchestrator.py)
│   └── detection_service.py        # Service management (from detection_service.py)
│
└── utils/                           # Shared Utilities
    ├── __init__.py
    ├── image_processing.py         # Image enhancement, cropping
    ├── io_utils.py                 # File I/O, folder management
    └── deduplication.py            # IoU checks, anti-duplicate logic
```

---

## File-by-File Breakdown

### 1. `functions/` - Detection Functions (One per Function)

Each file implements a **single detection capability** with a standard interface:

#### `functions/car_detection.py`
```python
"""
Vehicle Detection Function
Uses YOLO to detect cars, trucks, buses in video frames.
"""

from typing import Dict, Any
import numpy as np

class CarDetectionFunction:
    """YOLO-based vehicle detection"""
    
    # Metadata
    FUNCTION_ID = "car_detect"
    FUNCTION_NAME = "Nhận diện xe (Real-time)"
    DESCRIPTION = "Phát hiện phương tiện từ luồng video trực tiếp"
    INPUT_SOURCE = "front_cam"
    PARALLEL_GROUP = 1
    
    def __init__(self, confidence: float = 0.3, detect_trucks: bool = True):
        self.confidence = confidence
        self.detect_trucks = detect_trucks
        self._model = None  # Lazy load
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect vehicles in a frame.
        
        Args:
            frame: Input image (numpy array)
            
        Returns:
            {
                "success": bool,
                "detected": bool,
                "bbox": [x1, y1, x2, y2],
                "confidence": float,
                "class_name": str,  # "car", "truck", "bus"
                "class_id": int
            }
        """
        # Implementation from car_detect.py
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return function metadata for configuration"""
        return {
            "id": self.FUNCTION_ID,
            "name": self.FUNCTION_NAME,
            "description": self.DESCRIPTION,
            "input_source": self.INPUT_SOURCE,
            "parallel_group": self.PARALLEL_GROUP
        }
```

#### `functions/plate_detection.py`
```python
"""
License Plate Detection Function
Uses OCR to extract license plate numbers from vehicle images.
"""

from typing import Dict, Any, List
import numpy as np

class PlateDetectionFunction:
    """License plate recognition using PaddleOCR"""
    
    FUNCTION_ID = "plate_detect"
    FUNCTION_NAME = "Nhận diện biển số"
    DESCRIPTION = "Tự động trích xuất biển số xe từ hình ảnh"
    INPUT_SOURCE = "front_cam"
    PARALLEL_GROUP = 2
    
    def __init__(self):
        self._ocr = None  # Lazy load PaddleOCR
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect license plate in a frame.
        
        Returns:
            {
                "success": bool,
                "plates": List[str],  # ["29A-12345"]
                "confidence": float,
                "positions": List[bbox]  # Optional
            }
        """
        # Implementation from info_detect.py
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "id": self.FUNCTION_ID,
            "name": self.FUNCTION_NAME,
            "description": self.DESCRIPTION,
            "input_source": self.INPUT_SOURCE,
            "parallel_group": self.PARALLEL_GROUP
        }
```

#### Similar files for:
- `functions/color_detection.py` - Color analysis
- `functions/wheel_detection.py` - Wheel counting
- `functions/box_detection.py` - Box dimensions
- `functions/volume_detection.py` - Volume calculation

**Standard Interface** (all functions implement):
```python
class DetectionFunction:
    FUNCTION_ID: str
    FUNCTION_NAME: str
    DESCRIPTION: str
    INPUT_SOURCE: str  # "front_cam" or "side_cam"
    PARALLEL_GROUP: int
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Execute detection on frame"""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return function metadata"""
        pass
```

---

### 2. `config/function_config.py` - Function Registry & Configuration

```python
"""
Function Configuration Registry

Manages all available detection functions, their metadata,
and mapping to actual implementations.
"""

from typing import Dict, List, Type, Any
from backend.car_process.functions import (
    CarDetectionFunction,
    PlateDetectionFunction,
    ColorDetectionFunction,
    WheelDetectionFunction,
    BoxDetectionFunction,
    VolumeDetectionFunction
)

# Function Registry - Maps function_id to implementation class
FUNCTION_REGISTRY: Dict[str, Type] = {
    "car_detect": CarDetectionFunction,
    "plate_detect": PlateDetectionFunction,
    "color_detect": ColorDetectionFunction,
    "wheel_detect": WheelDetectionFunction,
    "box_detect": BoxDetectionFunction,
    "volume_detect": VolumeDetectionFunction,
}

# Function Metadata - Auto-generated from classes
FUNCTION_METADATA: Dict[str, Dict[str, Any]] = {
    func_id: func_class().get_metadata()
    for func_id, func_class in FUNCTION_REGISTRY.items()
}

def get_function(function_id: str):
    """Get function instance by ID"""
    if function_id not in FUNCTION_REGISTRY:
        raise ValueError(f"Unknown function: {function_id}")
    return FUNCTION_REGISTRY[function_id]()

def get_function_metadata(function_id: str) -> Dict[str, Any]:
    """Get metadata for a function"""
    return FUNCTION_METADATA.get(function_id, {})

def list_all_functions() -> List[Dict[str, Any]]:
    """List all available functions with metadata"""
    return list(FUNCTION_METADATA.values())

def validate_function_list(function_ids: List[str]) -> bool:
    """Check if all function IDs are valid"""
    return all(fid in FUNCTION_REGISTRY for fid in function_ids)
```

---

### 3. `config/location_config.py` - Location Tag Strategies

```python
"""
Location-Based Detection Strategies

Defines what detection functions should run at different location types.
Merged from backend/detection/detection_config.py
"""

from enum import Enum
from typing import Dict, List
from dataclasses import dataclass

class LocationTag(str, Enum):
    """Location tags for camera grouping"""
    CHECK_IN = "Cổng vào"
    CHECK_OUT = "Cổng ra"
    VOLUME_ESTIMATE = "Đo thể tích"
    GENERAL = "Cơ bản"

@dataclass
class LocationStrategy:
    """Detection strategy for a location type"""
    tag: LocationTag
    description: str
    suggested_functions: List[str]  # Suggested function IDs
    capture_strategy: str
    volume_tolerance: float = None

# Location-based strategies
LOCATION_STRATEGIES: Dict[LocationTag, LocationStrategy] = {
    LocationTag.CHECK_IN: LocationStrategy(
        tag=LocationTag.CHECK_IN,
        description="Entry gate - detect incoming vehicles",
        suggested_functions=["car_detect", "plate_detect", "color_detect", "wheel_detect"],
        capture_strategy="continuous"
    ),
    
    LocationTag.CHECK_OUT: LocationStrategy(
        tag=LocationTag.CHECK_OUT,
        description="Exit gate - detect outgoing vehicles",
        suggested_functions=["car_detect", "plate_detect", "color_detect"],
        capture_strategy="verify_and_match"
    ),
    
    LocationTag.VOLUME_ESTIMATE: LocationStrategy(
        tag=LocationTag.VOLUME_ESTIMATE,
        description="Volume measurement station",
        suggested_functions=["car_detect", "box_detect", "volume_detect", "plate_detect"],
        capture_strategy="multi_angle",
        volume_tolerance=0.05
    ),
    
    LocationTag.GENERAL: LocationStrategy(
        tag=LocationTag.GENERAL,
        description="General purpose camera",
        suggested_functions=["car_detect", "plate_detect"],
        capture_strategy="on_motion"
    )
}

def get_location_strategy(tag: str) -> LocationStrategy:
    """Get detection strategy for a location tag"""
    try:
        location_tag = LocationTag(tag)
        return LOCATION_STRATEGIES[location_tag]
    except (ValueError, KeyError):
        return LOCATION_STRATEGIES[LocationTag.GENERAL]
```

---

### 4. `config/camera_type_config.py` - Predefined Camera Types

```python
"""
Predefined Camera Type Configurations

Common camera type presets that users can select from.
These are defaults; users can create custom types with their own function sets.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class CameraTypePreset:
    """Predefined camera type configuration"""
    id: str
    name: str
    functions: List[str]
    description: str
    use_case: str

# Predefined Camera Types
CAMERA_TYPE_PRESETS: Dict[str, CameraTypePreset] = {
    "check_in_scanner": CameraTypePreset(
        id="check_in_scanner",
        name="Check-in Scanner",
        functions=["car_detect", "plate_detect", "color_detect", "wheel_detect"],
        description="Full vehicle analysis for entry gates",
        use_case="Entry gates, check-in stations"
    ),
    
    "check_out_scanner": CameraTypePreset(
        id="check_out_scanner",
        name="Check-out Scanner",
        functions=["car_detect", "plate_detect", "color_detect"],
        description="Quick verification for exit gates",
        use_case="Exit gates, check-out stations"
    ),
    
    "plate_only": CameraTypePreset(
        id="plate_only",
        name="Plate-Only Scanner",
        functions=["car_detect", "plate_detect"],
        description="Fast license plate recognition",
        use_case="Parking lots, toll gates"
    ),
    
    "volume_scanner": CameraTypePreset(
        id="volume_scanner",
        name="Volume Scanner",
        functions=["car_detect", "box_detect", "volume_detect", "plate_detect"],
        description="Material volume measurement for trucks",
        use_case="Loading zones, weigh stations"
    ),
    
    "basic_monitor": CameraTypePreset(
        id="basic_monitor",
        name="Basic Monitor",
        functions=["car_detect"],
        description="Simple vehicle detection",
        use_case="Monitoring, counting"
    ),
    
    # Special type for custom configurations
    "custom": CameraTypePreset(
        id="custom",
        name="Custom Configuration",
        functions=[],  # User selects functions
        description="Fully customizable function selection",
        use_case="Any custom use case"
    )
}

def get_preset(preset_id: str) -> CameraTypePreset:
    """Get a camera type preset by ID"""
    return CAMERA_TYPE_PRESETS.get(preset_id, CAMERA_TYPE_PRESETS["basic_monitor"])

def list_presets() -> List[CameraTypePreset]:
    """List all available presets"""
    return list(CAMERA_TYPE_PRESETS.values())
```

---

### 5. `core/orchestrator.py` - Main Orchestration Logic

```python
"""
Detection Orchestrator

Main controller that coordinates detection execution based on camera type.
Handles both predefined camera types and custom configurations.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from backend.car_process.config.function_config import get_function, get_function_metadata
from backend.car_process.config.camera_type_config import get_preset

class DetectionOrchestrator:
    """
    Orchestrates detection execution for a camera based on its type configuration.
    
    Supports:
    1. Predefined camera types (check-in, check-out, volume, etc.)
    2. Custom camera types with user-selected functions
    """
    
    def __init__(self):
        self._function_instances = {}  # Cache function instances
    
    def execute_for_camera_type(self, 
                                camera_type: Dict[str, Any],
                                front_frame: np.ndarray,
                                side_frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Execute detection for a camera type configuration.
        
        Args:
            camera_type: Camera type config from database
                {
                    "name": "Check-in Scanner",
                    "functions": "car_detect;plate_detect;color_detect"
                }
            front_frame: Front camera frame
            side_frame: Optional side camera frame
            
        Returns:
            Detection results for all configured functions
        """
        # Parse function list
        functions_str = camera_type.get('functions', '')
        function_ids = [f.strip() for f in functions_str.split(';') if f.strip()]
        
        if not function_ids:
            return {"success": False, "error": "No functions configured"}
        
        # Prepare frames
        frames = {
            'front_cam': front_frame,
            'side_cam': side_frame
        }
        
        # Group functions by parallel group
        grouped_functions = self._group_by_parallel_group(function_ids)
        
        # Execute groups sequentially, functions within group in parallel
        all_results = {}
        for group_id, func_ids_in_group in sorted(grouped_functions.items()):
            group_results = self._execute_parallel_group(func_ids_in_group, frames)
            all_results.update(group_results)
        
        return {
            "success": True,
            "results": all_results,
            "camera_type": camera_type.get('name', 'Unknown'),
            "executed_functions": list(all_results.keys())
        }
    
    def execute_for_preset(self,
                          preset_id: str,
                          front_frame: np.ndarray,
                          side_frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Execute detection using a predefined camera type preset.
        
        Args:
            preset_id: Preset ID (e.g., "check_in_scanner")
            front_frame: Front camera frame
            side_frame: Optional side camera frame
        """
        preset = get_preset(preset_id)
        
        # Convert preset to camera_type format
        camera_type = {
            "name": preset.name,
            "functions": ";".join(preset.functions)
        }
        
        return self.execute_for_camera_type(camera_type, front_frame, side_frame)
    
    def _group_by_parallel_group(self, function_ids: List[str]) -> Dict[int, List[str]]:
        """Group functions by their parallel group number"""
        grouped = {}
        for func_id in function_ids:
            metadata = get_function_metadata(func_id)
            group = metadata.get('parallel_group', 1)
            
            if group not in grouped:
                grouped[group] = []
            grouped[group].append(func_id)
        
        return grouped
    
    def _execute_parallel_group(self, 
                                function_ids: List[str], 
                                frames: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Execute a group of functions in parallel"""
        results = {}
        
        def run_function(func_id: str):
            # Get function instance (cached)
            if func_id not in self._function_instances:
                self._function_instances[func_id] = get_function(func_id)
            
            func_instance = self._function_instances[func_id]
            metadata = get_function_metadata(func_id)
            
            # Get required frame
            frame_source = metadata.get('input_source', 'front_cam')
            frame = frames.get(frame_source)
            
            if frame is None:
                return (func_id, {
                    "success": False,
                    "error": f"Frame from {frame_source} not available"
                })
            
            # Execute
            try:
                result = func_instance.detect(frame)
                return (func_id, result)
            except Exception as e:
                return (func_id, {
                    "success": False,
                    "error": str(e)
                })
        
        # Run in parallel
        with ThreadPoolExecutor(max_workers=len(function_ids)) as executor:
            futures = [executor.submit(run_function, fid) for fid in function_ids]
            for future in futures:
                func_id, result = future.result()
                results[func_id] = result
        
        return results
    
    def preview_execution_plan(self, camera_type: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview what functions will be executed without running them.
        
        Useful for UI to show user what will happen.
        """
        functions_str = camera_type.get('functions', '')
        function_ids = [f.strip() for f in functions_str.split(';') if f.strip()]
        
        # Build execution plan
        grouped = self._group_by_parallel_group(function_ids)
        
        plan = []
        for group_id, func_ids in sorted(grouped.items()):
            group_info = {
                "parallel_group": group_id,
                "execution_mode": "parallel" if len(func_ids) > 1 else "sequential",
                "functions": []
            }
            
            for func_id in func_ids:
                metadata = get_function_metadata(func_id)
                group_info["functions"].append({
                    "id": func_id,
                    "name": metadata.get('name', func_id),
                    "input_source": metadata.get('input_source', 'unknown')
                })
            
            plan.append(group_info)
        
        return {
            "camera_type": camera_type.get('name', 'Unknown'),
            "total_functions": len(function_ids),
            "execution_plan": plan,
            "requires_side_camera": any(
                get_function_metadata(fid).get('input_source') == 'side_cam'
                for fid in function_ids
            )
        }

# Singleton instance
_orchestrator = None

def get_orchestrator() -> DetectionOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DetectionOrchestrator()
    return _orchestrator
```

---

## Migration Path

### Phase 1: Create New Structure (Week 1)
1. ✅ Create `backend/car_process/` folder
2. ✅ Split `car_detect.py` → `functions/car_detection.py`
3. ✅ Split `info_detect.py` → `functions/plate_detection.py`, `color_detection.py`, `wheel_detection.py`
4. ✅ Move `detection_config.py` → `config/location_config.py`
5. ✅ Create `config/function_config.py` (new)
6. ✅ Create `config/camera_type_config.py` (new)
7. ✅ Move `detection_service.py` → `core/detection_service.py`
8. ✅ Move `pipeline_orchestrator.py` → `core/pipeline.py`
9. ✅ Create `core/orchestrator.py` (new)

### Phase 2: Update Imports (Week 1)
1. Update `backend/api/` files to use new imports
2. Add compatibility layer in old folders (deprecation warnings)
3. Update tests

### Phase 3: Remove Old Folders (Week 2)
1. Verify all functionality works
2. Delete `backend/detection/`
3. Delete `backend/detect_car/`
4. Remove compatibility layer

---

## Advantages of Your Proposal

### ✅ Pros

1. **Single Responsibility**: Each file has ONE job
   - `car_detection.py` only does car detection
   - Easy to understand and modify

2. **Easier Testing**: Test each function independently
   ```python
   # Test only plate detection
   from backend.car_process.functions import PlateDetectionFunction
   def test_plate_detection():
       func = PlateDetectionFunction()
       result = func.detect(test_frame)
       assert result["success"] == True
   ```

3. **Easy to Add New Functions**: Just create a new file
   ```python
   # backend/car_process/functions/speed_detection.py
   class SpeedDetectionFunction:
       FUNCTION_ID = "speed_detect"
       # ... implementation
   ```

4. **Better Code Organization**: Clear hierarchy
   - `functions/` = What you can detect
   - `config/` = How to configure detection
   - `core/` = How detection is executed

5. **Flexibility**: Support both presets AND custom configs
   - Preset: "Use Check-in Scanner" (predefined functions)
   - Custom: "I want only car_detect + color_detect" (user choice)

6. **Self-Documenting**: File names tell you what they do
   - `plate_detection.py` → obviously handles plate detection
   - No need to search through 500-line files

---

## Potential Concerns & Solutions

### ⚠️ Concern 1: Too Many Small Files?
**Answer**: This is actually GOOD!
- Each file is focused and easy to understand
- Python's module system handles this well
- IDE navigation is easier

### ⚠️ Concern 2: Import complexity?
**Solution**: Clean `__init__.py` files
```python
# backend/car_process/__init__.py
from .core.orchestrator import get_orchestrator
from .config.function_config import list_all_functions

__all__ = ['get_orchestrator', 'list_all_functions']
```

### ⚠️ Concern 3: Backward compatibility?
**Solution**: Keep old imports working temporarily
```python
# backend/detect_car/__init__.py (deprecated)
import warnings
from backend.car_process.functions.car_detection import CarDetectionFunction

warnings.warn("backend.detect_car is deprecated, use backend.car_process", DeprecationWarning)

# Still works for old code
CarDetector = CarDetectionFunction
```

---

## Comparison: Before vs After

### Before (Current State)
```
backend/
├── detection/              ← Configuration only
│   └── detection_config.py (5,936 bytes)
│
└── detect_car/             ← Everything else
    ├── car_detect.py       (8,806 bytes - car + other classes)
    ├── info_detect.py      (5,798 bytes - plate + color + wheel)
    ├── detection_service.py (15,354 bytes)
    └── volume_detect.py    (4,371 bytes)

Problems:
❌ car_detect.py has multiple detection classes
❌ info_detect.py mixes 3 different functions
❌ Split between detection/ and detect_car/ is confusing
❌ Hard to find specific detection logic
```

### After (Your Proposal)
```
backend/car_process/
├── functions/              ← ONE function per file
│   ├── car_detection.py
│   ├── plate_detection.py
│   ├── color_detection.py
│   ├── wheel_detection.py
│   ├── box_detection.py
│   └── volume_detection.py
│
├── config/                 ← ALL configuration in one place
│   ├── function_config.py      (function registry)
│   ├── location_config.py      (location strategies)
│   └── camera_type_config.py   (presets)
│
├── core/                   ← Orchestration logic
│   ├── orchestrator.py         (main controller)
│   ├── pipeline.py
│   └── detection_service.py
│
└── utils/                  ← Shared utilities
    ├── image_processing.py
    └── io_utils.py

Benefits:
✅ Clear organization
✅ Easy to find specific function
✅ One source of truth
✅ Easy to add new functions
✅ Better testing
```

---

## Recommendation

### 🎯 **YOUR PROPOSAL IS EXCELLENT!**

I **strongly recommend** implementing your refactoring plan because:

1. ✅ **Better Architecture**: Follows single responsibility principle
2. ✅ **Easier Maintenance**: Each file has one clear purpose
3. ✅ **Scalable**: Easy to add new detection functions
4. ✅ **Testable**: Test individual functions in isolation
5. ✅ **Self-Documenting**: File structure explains itself

### Implementation Priority

**Do Now** (High Priority):
1. ✅ Create the new folder structure
2. ✅ Split detection functions into separate files
3. ✅ Create function_config.py as registry
4. ✅ Create orchestrator.py to control execution

**Do Later** (Medium Priority):
5. ⏳ Migrate existing code to use new structure
6. ⏳ Add deprecation warnings to old folders
7. ⏳ Update documentation

**Do Eventually** (Low Priority):
8. ⏳ Remove old folders after verification
9. ⏳ Add more predefined camera type presets

---

## Next Steps

1. **Review this plan** - Does it match your vision?
2. **Create the folder structure** - I can help generate all files
3. **Migrate one function** - Start with car_detection as proof of concept
4. **Test it thoroughly** - Ensure it works with existing API
5. **Migrate remaining functions** - One by one
6. **Update API imports** - Point to new structure
7. **Remove old code** - Clean up deprecated folders

Would you like me to:
- ✅ Generate the complete new folder structure with all files?
- ✅ Create a step-by-step migration script?
- ✅ Write tests for the new structure?

Your refactoring idea is **spot-on** and will make the codebase much better! 🎯
