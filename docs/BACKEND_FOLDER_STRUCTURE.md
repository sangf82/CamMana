# Backend Folder Structure: `detection/` vs `detect_car/`

## Quick Answer

- **`backend/detection/`** = **Configuration & Strategy** (WHAT to detect based on WHERE)
- **`backend/detect_car/`** = **Implementation & Execution** (HOW to detect using AI models)

---

## Detailed Comparison

### 📋 `backend/detection/` - Configuration Layer

**Purpose**: Defines **detection strategies** based on **location tags** (e.g., "Cổng vào", "Cổng ra", "Đo thể tích")

**Contents**:
```
backend/detection/
├── __init__.py
└── detection_config.py  (5,936 bytes)
```

**What it does**:
1. **Defines location tags** (`LocationTag` enum):
   - `Cổng vào` (Check-in) 
   - `Cổng ra` (Check-out)
   - `Đo thể tích` (Volume measurement)
   - `Cơ bản` (General)

2. **Maps tags to detection strategies** (`TAG_DETECTION_CONFIG`):
   ```python
   LocationTag.CHECK_IN: DetectionConfig(
       detection_sequence=["car_detection", "plate_recognition", "color_detection", "wheel_count"],
       capture_strategy="continuous"
   )
   ```

3. **Provides helper functions**:
   - `get_detection_config(tag)` - Get config for a location tag
   - `get_camera_detection_models(tag)` - Get which models to run
   - `get_capture_strategy(tag)` - Get capture strategy
   - `group_cameras_by_tag()` - Group cameras by location

**Example Usage**:
```python
from backend.detection import get_detection_config

# Get detection config for check-in gate
config = get_detection_config("Cổng vào")
# Returns: ["car_detection", "plate_recognition", "color_detection", "wheel_count"]
```

**Think of it as**: The "brain" that decides **WHAT** to detect **WHERE**

---

### 🤖 `backend/detect_car/` - Implementation Layer

**Purpose**: Contains **actual AI models** and **execution logic** for vehicle detection

**Contents**:
```
backend/detect_car/
├── __init__.py
├── car_detect.py            (8,806 bytes)   - YOLO car detection
├── detection_service.py     (15,354 bytes)  - Orchestration service
├── info_detect.py           (5,798 bytes)   - Plate/color/wheel detection
├── volume_detect.py         (4,371 bytes)   - Volume calculation
└── pipeline_orchestrator.py (13,492 bytes)  - Dynamic pipeline (NEW!)
```

**What each file does**:

#### 1. `car_detect.py` - Car Detection AI
- **YOLO-based vehicle detection**
- Detects cars, trucks, buses from video frames
- Returns bounding boxes and confidence scores

```python
from backend.detect_car import CarDetector

detector = CarDetector(confidence=0.3)
result = detector.detect(frame)
# Returns: {"detected": True, "bbox": [x1, y1, x2, y2], "confidence": 0.87}
```

#### 2. `info_detect.py` - Information Extraction
- **License plate detection** (using PaddleOCR or similar)
- **Color detection** (analyzes vehicle color)
- **Wheel counting** (counts axles/wheels)

```python
from backend.detect_car import detect_plate, detect_colors, count_wheels

plate_result = detect_plate(frame)        # → "29A-12345"
color_result = detect_colors(frame)       # → "white"
wheel_result = count_wheels(frame)        # → 4
```

#### 3. `detection_service.py` - Orchestration Service
- **Manages detection workflows**
- Coordinates front + side camera capture
- Handles IoU-based deduplication
- Manages auto-detection mode

```python
from backend.detect_car import get_detection_service

service = get_detection_service()
service.register_camera(camera_id, streamer)
result = service.capture_with_detection(camera_id)
```

#### 4. `volume_detect.py` - Volume Calculation
- **3D volume estimation** for trucks
- Calculates material volume in truck beds
- Used for loading/unloading verification

#### 5. `pipeline_orchestrator.py` - Dynamic Pipeline (NEW!)
- **New file I just created**
- Executes detection tasks based on camera type
- Handles parallel processing
- Flexible function selection

```python
from backend.detect_car.pipeline_orchestrator import DetectionPipeline

pipeline = DetectionPipeline(camera_type_config)
results = pipeline.execute(front_frame, side_frame)
```

**Think of it as**: The "hands" that actually **DO** the detection work

---

## How They Work Together

### Example: Car entering "Cổng vào" (Check-in Gate)

```
┌─────────────────────────────────────────────────────┐
│ 1. Location Tag: "Cổng vào"                         │
│    (from camera's location configuration)           │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 2. backend/detection/detection_config.py            │
│    → Looks up "Cổng vào" in TAG_DETECTION_CONFIG    │
│    → Returns: ["car_detection", "plate_recognition",│
│                "color_detection", "wheel_count"]     │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 3. backend/detect_car/detection_service.py          │
│    → Executes detection workflow                    │
│    → Calls actual AI models:                        │
│      - car_detect.py (YOLO)                          │
│      - info_detect.py (plate/color/wheel)            │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 4. Results saved to database                        │
│    → Folder: 29A12345_CongVao_15_01_2026/           │
│    → Images + JSON outputs                          │
└─────────────────────────────────────────────────────┘
```

---

## Code Example: Both Working Together

```python
# Step 1: Get camera configuration
camera = data_process.get_camera_by_id("cam_001")
# camera.location = "Cổng vào"

# Step 2: Use detection/ to get strategy (WHAT to detect)
from backend.detection import get_detection_config

config = get_detection_config(camera.location_tag)
# config.detection_sequence = ["car_detection", "plate_recognition", ...]

# Step 3: Use detect_car/ to execute detection (HOW to detect)
from backend.detect_car import get_detection_service

service = get_detection_service()
result = service.capture_with_detection(camera.id)
# result = {plate: "29A-12345", color: "white", wheel: 4}
```

---

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────┐        ┌────────────────────────┐  │
│  │ backend/detection/     │        │ backend/detect_car/    │  │
│  │ (Strategy Layer)       │   →    │ (Execution Layer)      │  │
│  ├────────────────────────┤        ├────────────────────────┤  │
│  │                        │        │                        │  │
│  │ • Location tags        │        │ • CarDetector (YOLO)   │  │
│  │ • Detection configs    │        │ • detect_plate()       │  │
│  │ • Capture strategies   │        │ • detect_colors()      │  │
│  │ • Tag-based routing    │        │ • count_wheels()       │  │
│  │                        │        │ • DetectionService     │  │
│  │ DECIDES: What to run   │        │ EXECUTES: AI models    │  │
│  │                        │        │                        │  │
│  └────────────────────────┘        └────────────────────────┘  │
│           ↑                                    ↑                 │
│           │                                    │                 │
│           └────── Both used by API Layer ─────┘                 │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ backend/api/config.py                                    │   │
│  │ • Groups cameras by location tag                        │   │
│  │ • Returns appropriate detection config                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## When is Each Used?

### `backend/detection/` is used when:
✅ You need to know **what detection strategy** to use for a location
✅ You're configuring cameras based on their **physical location**
✅ You want to **group cameras** by their purpose (check-in, check-out, volume)
✅ You need **location-specific detection sequences**

**API Examples**:
- `GET /api/cameras/locations/grouped` (groups by tag)
- `GET /api/cameras/locations/tags/{tag}/config` (gets detection config)

### `backend/detect_car/` is used when:
✅ You need to **actually detect vehicles** in video frames
✅ You're **executing detection workflows**
✅ You need **AI model predictions** (plate, color, wheel)
✅ You're **managing detection state** (IoU checks, auto-detection)

**API Examples**:
- `POST /api/cameras/{camera_id}/detect` (runs detection)
- `POST /api/cameras/{camera_id}/capture` (captures with detection)
- `POST /api/detection/pipeline/execute/{camera_id}` (new pipeline)

---

## Summary Table

| Aspect | `backend/detection/` | `backend/detect_car/` |
|--------|---------------------|----------------------|
| **Purpose** | Configuration & Strategy | Implementation & Execution |
| **Abstraction** | High-level (WHAT/WHERE) | Low-level (HOW) |
| **Main Focus** | Location tags, strategies | AI models, processing |
| **File Count** | 2 files | 6 files |
| **Total Size** | ~6 KB | ~48 KB |
| **Key Exports** | `LocationTag`, `DetectionConfig` | `CarDetector`, `DetectionService` |
| **Dependencies** | None (pure config) | OpenCV, YOLO, PaddleOCR |
| **When to Use** | Setting up cameras by location | Running actual detection |
| **Example** | "Check-in gates run plate+color" | `detect_plate(frame)` → "29A-12345" |

---

## Analogy

Think of your backend like a **restaurant kitchen**:

### `backend/detection/` = **Menu & Recipes**
- Defines **what dishes** are served **when**
- "Lunch menu: soup + main course"
- "Dinner menu: appetizer + main + dessert"
- **Doesn't cook anything**, just defines the strategy

### `backend/detect_car/` = **Kitchen Equipment & Chefs**
- The **actual cooking tools** (oven, stove, knives)
- The **chefs** who prepare the food
- Execute the recipes from the menu
- Do the **real work**

When a customer orders:
1. **Menu** (`detection/`) says: "Lunch special = soup + main"
2. **Kitchen** (`detect_car/`) executes: Cooks soup, cooks main, serves

---

## Recommendation

**Both folders are essential and complementary!**

- Keep `backend/detection/` for **location-based strategy configuration**
- Keep `backend/detect_car/` for **actual AI model execution**
- The new `pipeline_orchestrator.py` bridges them both!

**Future enhancement**: You could merge the location tag strategy with the camera type functions for even more flexibility!

```python
# Possible future combination:
Camera Type: "Check-in Scanner"
Functions: "car_detect;plate_detect;color_detect"  ← From type config

Location Tag: "Cổng vào"
Strategy: Use functions from camera type  ← From location config

Result: Best of both worlds! 🎯
```
