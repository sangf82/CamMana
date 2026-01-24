# CamMana System Documentation

This document serves as the comprehensive technical reference for the CamMana system, detailing system configuration, camera connectivity, backend process logic (Move In/Out), and data schemas.

---

# Part 1: System Configuration (Cameras & Locations)

## 1. Camera Configuration & Connection

### A. Connectivity Model
The system supports **ONVIF-compliant** IP cameras.
*   **Protocol**: RTSP (Real Time Streaming Protocol) for video, ONVIF for PTZ and discovery.
*   **Connection Flow**:
    1.  User submits `POST /api/cameras/connect` with IP, User, Password.
    2.  Backend initiates a blocking connection attempt (wrapped in `asyncio.to_thread` with a 10s timeout).
    3.  If successful:
        *   Retrieves the **Stream URI** and **Profile Token**.
        *   Initializes a `VideoStreamer` (handles frame grabbing via OpenCV in a separate thread).
        *   Registers the camera in the ephemeral `active_cameras` memory store.
        *   Saves/Updates the persistent record in `database/cameras.csv`.

### B. Camera Data Schema
**Storage File**: `database/cameras.csv`
**Pydantic Model**: `backend.schemas.Camera`

| Field | Description | Type | Key Notes |
| :--- | :--- | :--- | :--- |
| `id` | Unique UUID | String | Generated on creation. |
| `cam_id` | Human-readable ID | String | Format: `CAM-xx` (e.g., CAM-01). |
| `name` | Display Name | String | |
| `ip` | IPv4 Address | String | Primary key for connection attempts. |
| `port` | ONVIF Port | Integer | Default: 8899. |
| `user` | ONVIF Username | String | |
| `password` | ONVIF Password | String | |
| `stream_uri` | RTSP URL | String | Retrieved from camera upon connection. |
| `detection_mode` | AI Trigger Mode | Enum | `auto`, `manual`, `disabled`. |
| `tag` | Functional Role | Enum | Critical for AI logic (see below). |
| `location_id` | Location Reference | UUID | Links to `locations.csv`. |

### C. Camera Functional Tags
The `tag` field determines what AI tasks are performed on the stream:
*   `front_cam`: Used for **License Plate Recognition (ALPR)**.
*   `side_cam`: Used for **Color Detection** and **Wheel Counting**.
*   `top_cam`: Used for **Volume Estimation** (requires calibration).

## 2. Location Configuration

Locations provide logical grouping for cameras (e.g., "South Gate", "Main Entry").

### A. Location Schema
**Storage File**: `database/locations.csv`
**Pydantic Model**: `backend.schemas.Location`

| Field | Description | Type |
| :--- | :--- | :--- |
| `id` | Unique UUID | String |
| `name` | Display Name | String |
| `tag` | Categorization | String | Default: "Cơ bản". |

### B. Location Resolution Logic
When processing a check-in, the system resolves a flexible Location Name (or "Slug") to a strict Location ID.
*   **Logic**:
    1.  Direct ID Match.
    2.  Hardcoded Slug Mapping (e.g., "cong nam" -> "South Gate" ID).
    3.  Partial Name Match.
*   **File**: `backend.car_process.core.checkin_service.CheckInService._resolve_location_id`

## 3. List & Retrieval API

*   **Get Active Cameras** (`GET /api/cameras`): Returns active cameras with realtime status (`connected`, `streaming`) and `stream_info`.
*   **Get Saved Cameras** (`GET /api/cameras/saved`): Returns all configured cameras from CSV with inferred status.
*   **Get Locations**: Internal function used to map camera locations to check-in events.

---

# Part 2: Backend Logic (Vehicle Process)

## 1. File Structure & Responsibilities

The core logic is modularized within the `backend/` directory:

```
backend/
├── api/
│   ├── checkin.py            # Entry point for "Move In" API endpoints
│   ├── history.py            # Entry point for "Move Out" (status updates) and history retrieval
│   ├── cameras.py            # Camera management API
│   └── ...
├── car_process/
│   └── core/
│       ├── checkin_service.py # Orchestrator for the Check-In workflow
│       ├── detection_client.py# Client for communicating with external AI APIs (Plate, Color, Wheel)
│       └── storage_manager.py # Handles file system operations (saving images/JSONs)
├── data_process/
│   ├── history.py            # CSV operations for daily history logs
│   ├── cameras.py            # CSV operations for camera config
│   ├── config.py             # CSV operations for locations
│   └── ...
└── database/                 # Local storage
    ├── car_history/          # Stores images and full JSON details per vehicle
    ├── cameras.csv           # Camera config
    ├── locations.csv         # Location config
    └── history_DD_MM_YYYY.csv# lightweight CSV logs for tracking flows
```

## 2. Process Implementation

### A. Move In (Check-In)
**Endpoint:** `POST /api/checkin/capture-and-process`

This process is triggered when a vehicle arrives at a gate. It automates data capture, AI analysis, and record creation.

1.  **Image Capture**:
    *   The backend captures live frames from configured cameras (Front, Side, Top) using the active camera streams.
    *   *Fallback*: If the side camera fails, the front camera frame is used as a placeholder.

2.  **Core Processing (`CheckInService.process_checkin`)**:
    *   **External AI Analysis**: The `detection_client` sends images to the external AI endpoints:
        *   `/alpr`: Detects license plate numbers.
        *   `/detect_colors`: Identifies the vehicle's primary color.
        *   `/count_wheels`: Counts vehicle wheels (result x2 for total count).
    *   **Volume Estimation (Conditional)**:
        *   If a top camera image and calibration files (`calib_side.json`, `calib_topdown.json`) exist, the system calls the Volume API.
        *   Calculates cargo volume (`vol_measured`).

3.  **Data Storage**:
    *   **Folder Creation**: A unique folder is created: `database/car_history/{date}/{uuid}_{location}_{timestamp}/`.
    *   **Artifacts**: Captured images (front, side, top) are saved here.
    *   **Status JSON**: A `checkin_status.json` file is created containing all detected attributes and current status.
    *   **Registration Match**: The system checks if the plate exists in the registered cars database.

4.  **History Logging**:
    *   A new record is appended to the daily history CSV (`history_{date}.csv`).
    *   **Initial Status**: Set to "in" or "pending_verification".

### B. Move Out (Check-Out)
**Endpoint:** `PUT /api/history`

Currently, "Move Out" is implemented as a status update to an existing history record.

1.  **Status Update**:
    *   The frontend sends a request to update a specific record identified by `plate` and `time_in`.
    *   **Updates**: Sets `time_out` to the current time, updates `status` to "out", and optionally adds notes.

2.  **CSV Persistence**:
    *   The `backend.data_process.history` module locates the row in the specific date's CSV and updates the fields in place.

## 3. Data Processing & External APIs

The system relies on an external API service for heavy AI tasks.

| Function | Endpoint | Input | Output |
| :--- | :--- | :--- | :--- |
| **Plate Recognition** | `/alpr` | Front Image | Plate string, confidence |
| **Color Detection** | `/detect_colors` | Side Image | Color class (e.g., "Red"), confidence |
| **Wheel Counting** | `/count_wheels` | Side Image | Wheel count (visible), bounding boxes |
| **Volume Estimate** | `/estimate_volume` | Side + Top Images + Calib | Volume ($m^3$) |

**Volume Integration Logic:**
*   Requires: Side image, Top Foreground (Truck), Top Background (No Truck), Side Calibration, Top Calibration.
*   The backend automatically manages picking the correct `background` image from `database/backgrounds` and calibration files (`database/calibration`).

## 4. Data Schemas

### A. History CSV Schema
**File:** `database/history_{dd}_{mm}_{yyyy}.csv`

Used for the main "History" table view.

| Field | Description | Type |
| :--- | :--- | :--- |
| `plate` | License plate number | String |
| `location` | Gate/Location ID (e.g., "Gate 1") | String |
| `time_in` | Timestamp of entry | ISO/String |
| `time_out` | Timestamp of exit (default: "---") | ISO/String |
| `vol_std` | Registered standard volume ($m^3$) | Float/String |
| `vol_measured` | AI calculated volume ($m^3$) | Float/String |
| `status` | Current state ("in", "out", "pending") | String |
| `verify` | Verification status ("yes", "no") | String |
| `note` | Operator notes | String |

### B. Check-In Status JSON Schema
**File:** `database/car_history/.../checkin_status.json`

Stores the full, rich data for a specific event.

```json
{
  "uuid": "unique_transaction_id",
  "location_id": "gate_id",
  "date": "20-01-2026",
  "folder_path": "path/to/storage/folder",
  "plate_number": "29H-123.45",
  "plate_confidence": 0.95,
  "color": "Red",
  "color_confidence": 0.88,
  "wheel_count": 6,
  "wheel_confidence": 0.92,
  "volume": 12.5,
  "status": "pending_verification",
  "created_at": "timestamp",
  "history_record": { ...copy of csv row... }
}
```
