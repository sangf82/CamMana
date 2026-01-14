# CamMana Backend API Documentation

**Version:** 2.1.0  
**Base URL:** `http://localhost:8000`  
**Last Updated:** 2026-01-14 (Refactored Architecture)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture) ⭐ NEW
3. [Authentication](#authentication)
4. [Camera Management](#camera-management)
5. [PTZ Control](#ptz-control)
6. [Video Streaming](#video-streaming)
7. [Detection & Capture](#detection--capture)
8. [History Management](#history-management)
9. [Registered Cars](#registered-cars) ⭐ UPDATED
10. [Schedule Management](#schedule-management)
11. [Configuration](#configuration)
12. [Data Models](#data-models)
13. [Error Handling](#error-handling)

---

## Overview

The CamMana Backend API provides comprehensive camera management, video streaming, vehicle detection, and data storage capabilities using FastAPI and ONVIF protocols.

### Tech Stack
- **Framework:** FastAPI 0.104+
- **Protocol:** ONVIF for camera control
- **Storage:** CSV files (modular data_process package)
- **Streaming:** RTSP/HTTP streaming
- **Detection:** External API services + local volume detection

### API Features
- ✅ Multi-camera management
- ✅ Real-time video streaming
- ✅ PTZ (Pan-Tilt-Zoom) control
- ✅ Vehicle detection with license plate recognition
- ✅ Color and wheel count detection
- ✅ Volume & dimension detection (NEW)
- ✅ Historical data tracking
- ✅ Registered car import with smart merge
- ✅ Schedule management
- ✅ Configuration management
- ✅ Report generation (Placeholder)

---

## Architecture

### Backend Structure (v2.1.0 - Refactored)

The backend has been completely refactored into a modular structure for better maintainability:

```
backend/
├── api/                          # Modular API routers
│   ├── __init__.py              # Router exports
│   └── (Future: cameras.py, history.py, detection.py, etc.)
│
├── data_process/                # CSV data storage operations
│   ├── __init__.py              # Package exports
│   ├── _common.py               # Shared utilities & constants
│   ├── cameras.py               # Camera configuration storage
│   ├── registered_cars.py       # Registered cars with smart import
│   ├── history.py               # History data operations
│   ├── captured_cars.py         # Captured car records & logs
│   ├── config.py                # Locations & types configuration
│   └── report.py                # Report generation (placeholder)
│
├── detect_car/                  # Detection services
│   ├── car_detect.py            # Vehicle detection
│   ├── info_detect.py           # Plate, color, wheel detection
│   ├── volume_detect.py         # Volume & dimension detection (NEW)
│   └── detection_service.py     # Detection orchestration
│
├── camera_config/               # Camera management
│   ├── camera.py                # ONVIF camera manager
│   └── streamer.py              # Video streaming
│
└── server.py                    # FastAPI application

```

### Key Improvements

✅ **No SQLite Dependency** - Pure CSV storage  
✅ **Modular Data Operations** - Separated by feature  
✅ **Reusable Detection Services** - Shared across APIs  
✅ **Date-Based Storage** - History and registered cars  
✅ **Smart Import Logic** - Automatic merge for registered cars  
✅ **Thread-Safe Operations** - All CSV writes protected  

---

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

> **Note:** Authentication should be implemented for production deployments.

---

## Camera Management

### Get All Connected Cameras

```http
GET /api/cameras
```

**Description:** Returns list of all active camera connections.

**Response:**
```json
[
  {
    "id": "uuid-string",
    "name": "Camera 1",
    "ip": "192.168.1.100",
    "connected": true,
    "streaming": true,
    "stream_uri": "rtsp://...",
    "tag": "front_cam",
    "detection_mode": "auto",
    "auto_detection_running": true,
    "stream_info": {
      "resolution": "1920x1080",
      "fps": 25
    }
  }
]
```

---

### Get Saved Cameras

```http
GET /api/cameras/saved
```

**Description:** Returns all saved camera configurations from CSV storage.

**Response:**
```json
[
  {
    "id": "uuid-string",
    "name": "Main Gate Camera",
    "ip": "192.168.1.100",
    "port": 8899,
    "username": "admin",
    "location": "Cổng Nam (Vào)",
    "location_id": "loc-123",
    "type": "Dome",
    "brand": "Hikvision",
    "status": "Online"
  }
]
```

**Status Values:**
- `Online` - Camera is streaming
- `Connected` - Camera is connected but not streaming
- `Offline` - Camera is not connected
- `Local` - Camera configuration saved but not active

---

### Save Camera Configuration

```http
POST /api/cameras
```

**Description:** Save or update camera configuration.

**Request Body:**
```json
{
  "id": "uuid-string",  // Optional, auto-generated if not provided
  "name": "Camera Name",
  "ip": "192.168.1.100",
  "port": 8899,
  "username": "admin",
  "password": "password123",
  "location": "Cổng Nam (Vào)",
  "type": "Dome",
  "brand": "Hikvision"
}
```

**Response:**
```json
{
  "success": true,
  "id": "uuid-string"
}
```

---

### Connect Camera

```http
POST /api/cameras/connect
```

**Description:** Establish connection to an ONVIF camera.

**Request Body:**
```json
{
  "ip": "192.168.1.100",
  "port": 8899,
  "user": "admin",
  "password": "password123",
  "name": "Camera 1",
  "tag": "front_cam",  // Optional: "front_cam" or "side_cam"
  "detection_mode": "disabled"  // "auto", "manual", or "disabled"
}
```

**Response:**
```json
{
  "success": true,
  "id": "camera-uuid",
  "message": "Camera connected successfully",
  "resolution": {
    "width": 1920,
    "height": 1080
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Connection timed out after 10 seconds"
}
```

---

### Disconnect Camera

```http
POST /api/cameras/{camera_id}/disconnect
```

**Parameters:**
- `camera_id` (path) - Camera UUID

**Response:**
```json
{
  "success": true
}
```

---

### Delete Camera

```http
DELETE /api/cameras/{camera_id}
```

**Description:** Delete camera from both active connections and saved configurations.

**Parameters:**
- `camera_id` (path) - Camera UUID

**Response:**
```json
{
  "success": true
}
```

---

### Update Detection Mode

```http
POST /api/cameras/{camera_id}/detection_mode
```

**Request Body:**
```json
{
  "detection_mode": "auto"  // "auto", "manual", or "disabled"
}
```

**Response:**
```json
{
  "success": true,
  "detection_mode": "auto"
}
```

---

### Update Camera Tag

```http
POST /api/cameras/{camera_id}/tag
```

**Request Body:**
```json
{
  "tag": "front_cam"  // "front_cam", "side_cam", or null
}
```

**Response:**
```json
{
  "success": true,
  "tag": "front_cam"
}
```

---

## PTZ Control

All PTZ endpoints follow the same pattern with a speed parameter.

### Move Camera Up

```http
POST /api/cameras/{camera_id}/ptz/up
```

**Request Body:**
```json
{
  "speed": 0.5  // Range: 0.1 - 1.0
}
```

### Move Camera Down

```http
POST /api/cameras/{camera_id}/ptz/down
```

### Move Camera Left

```http
POST /api/cameras/{camera_id}/ptz/left
```

### Move Camera Right

```http
POST /api/cameras/{camera_id}/ptz/right
```

### Zoom In

```http
POST /api/cameras/{camera_id}/ptz/zoom-in
```

### Zoom Out

```http
POST /api/cameras/{camera_id}/ptz/zoom-out
```

### Stop PTZ Movement

```http
POST /api/cameras/{camera_id}/ptz/stop
```

**Response (all PTZ endpoints):**
```json
{
  "success": true
}
```

---

## Video Streaming

### Start Stream

```http
POST /api/cameras/{camera_id}/stream/start
```

**Response:**
```json
{
  "success": true
}
```

---

### Stop Stream

```http
POST /api/cameras/{camera_id}/stream/stop
```

**Response:**
```json
{
  "success": true
}
```

---

### Get Video Feed

```http
GET /api/cameras/{camera_id}/stream
```

**Description:** Returns MJPEG video stream.

**Response:** 
- **Content-Type:** `multipart/x-mixed-replace; boundary=frame`
- **Body:** Continuous JPEG frames

**Usage Example (HTML):**
```html
<img src="http://localhost:8000/api/cameras/{camera_id}/stream" />
```

---

### Get Snapshot

```http
GET /api/cameras/{camera_id}/snapshot
```

**Description:** Capture a single frame from the camera.

**Response:**
- **Content-Type:** `image/jpeg`
- **Body:** JPEG image data

---

### Capture Image

```http
POST /api/cameras/{camera_id}/capture
```

**Description:** Save a snapshot to disk.

**Response:**
```json
{
  "success": true,
  "filename": "capture_20260114_145030.jpg",
  "path": "/database/captured_img/..."
}
```

---

## Detection & Capture

### Detect Vehicle

```http
GET /api/cameras/{camera_id}/detect
```

**Description:** Run single vehicle detection on current frame.

**Response:**
```json
{
  "success": true,
  "detections": [
    {
      "class": "car",
      "confidence": 0.95,
      "bbox": [100, 200, 300, 400],
      "plate_number": "65H-719.94",
      "color": "white"
    }
  ]
}
```

---

### Capture with Detection

```http
POST /api/cameras/{camera_id}/capture_with_detection?force=false
```

**Query Parameters:**
- `force` (optional, boolean) - Force capture even if no vehicle detected

**Description:** Capture image and run detection, save results if vehicle found.

**Response:**
```json
{
  "success": true,
  "detected": true,
  "plate_number": "65H-719.94",
  "folder_path": "/database/captured_car/car_at_14_01_2026_14_50_30",
  "record_id": "20260114_145030_abc123"
}
```

---

### Get Captured Cars

```http
GET /api/captured_cars?limit=50&date=2026_01_14
```

**Query Parameters:**
- `limit` (optional, default: 50) - Maximum records to return
- `date` (optional) - Date in format `YYYY_MM_DD` (default: today)

**Response:**
```json
[
  {
    "id": "20260114_145030_abc123",
    "timestamp": "2026-01-14 14:50:30",
    "folder_path": "/database/captured_car/...",
    "plate_number": "65H-719.94",
    "primary_color": "white",
    "wheel_count": "4",
    "confidence": 0.95,
    "class_name": "car",
    "bbox": [100, 200, 300, 400]
  }
]
```

---

### Search Captured Cars

```http
GET /api/captured_cars/search?plate=65H&date=2026_01_14
```

**Query Parameters:**
- `plate` (required) - Plate number search term
- `date` (optional) - Date in format `YYYY_MM_DD`

**Response:** Same as Get Captured Cars

---

### Get Detection Logs

```http
GET /api/detection_logs?camera_id=uuid&date=2026_01_14&limit=100
```

**Query Parameters:**
- `camera_id` (optional) - Filter by camera
- `date` (optional) - Date in format `YYYY_MM_DD`
- `limit` (optional, default: 100) - Maximum records

**Response:**
```json
[
  {
    "timestamp": "2026-01-14 14:50:30",
    "camera_id": "camera-uuid",
    "event_type": "detection",
    "details": {
      "plate_number": "65H-719.94",
      "confidence": 0.95
    }
  }
]
```

---

## History Management

### Get History Data

```http
GET /api/history?date=14/01/2026
```

**Query Parameters:**
- `date` (optional) - Date in format `dd/mm/yyyy` or `dd_mm_yyyy` (default: today)

**Description:** Get vehicle entry/exit history for a specific date.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "plate": "65H-719.94",
      "location": "Trạm Cân",
      "time_in": "13:34:50",
      "time_out": "14:40:15",
      "vol_std": "14.5",
      "vol_measured": "14.4",
      "status": "đã vào",
      "verify": "ngoài danh sách",
      "note": "Xe được cấp phép đặc biệt"
    }
  ],
  "count": 16
}
```

---

### Get Available History Dates

```http
GET /api/history/dates
```

**Description:** Returns list of all dates with history data.

**Response:**
```json
{
  "success": true,
  "dates": [
    "14/01/2026",
    "13/01/2026",
    "12/01/2026"
  ]
}
```

---

### Get History Date Range

```http
GET /api/history/range?start_date=12/01/2026&end_date=14/01/2026
```

**Query Parameters:**
- `start_date` (required) - Start date in format `dd/mm/yyyy`
- `end_date` (required) - End date in format `dd/mm/yyyy`

**Response:**
```json
{
  "success": true,
  "data": [...],  // Combined records from all dates
  "count": 38
}
```

---

### Save History Record

```http
POST /api/history?date=14/01/2026
```

**Query Parameters:**
- `date` (optional) - Date in format `dd/mm/yyyy` (default: today)

**Request Body:**
```json
{
  "plate": "65H-719.94",
  "location": "Trạm Cân",
  "time_in": "13:34:50",
  "time_out": "14:40:15",
  "vol_std": "14.5",
  "vol_measured": "14.4",
  "status": "đã vào",
  "verify": "ngoài danh sách",
  "note": "Xe được cấp phép đặc biệt"
}
```

**Response:**
```json
{
  "success": true
}
```

---

### Save Bulk History Records

```http
POST /api/history/bulk?date=14/01/2026
```

**Description:** Replace entire history file with new records.

**Request Body:**
```json
[
  {
    "plate": "65H-719.94",
    "location": "Trạm Cân",
    // ... other fields
  },
  {
    "plate": "79H-745.65",
    "location": "Cổng Bắc (Ra)",
    // ... other fields
  }
]
```

**Response:**
```json
{
  "success": true,
  "count": 2
}
```

---

## Schedule Management

### Get Schedule

```http
GET /api/schedule
```

**Description:** Load schedule data from Excel file.

**Response:**
```json
[
  {
    "stt": "1",
    "time_in": "08:30:00",
    "plate": "65H-719.94",
    "vehicle_type": "Xe tải",
    "dimensions": "2.5x6.0x2.3",
    "volume": "34.5",
    "status_validity": "Valid",
    "notes": "Scheduled delivery"
  }
]
```

---

### Upload Schedule

```http
POST /api/schedule/upload
```

**Description:** Upload new schedule Excel file.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (Excel file)

**Response:**
```json
{
  "success": true,
  "filename": "CCN_template.xlsx"
}
```

---

## Configuration

### Get Locations

```http
GET /api/cameras/locations
```

**Response:**
```json
[
  {
    "id": "loc-123",
    "name": "Cổng Nam (Vào)"
  },
  {
    "id": "loc-456",
    "name": "Trạm Cân"
  }
]
```

---

### Save Locations

```http
POST /api/cameras/locations
```

**Request Body:**
```json
[
  {
    "id": "loc-123",
    "name": "Cổng Nam (Vào)"
  },
  {
    "id": "",
    "name": "New Location"  // ID auto-generated
  }
]
```

**Response:**
```json
{
  "success": true
}
```

---

### Get Camera Types

```http
GET /api/cameras/types
```

**Response:**
```json
[
  {
    "id": "type-123",
    "name": "Dome"
  },
  {
    "id": "type-456",
    "name": "Bullet"
  }
]
```

---

### Save Camera Types

```http
POST /api/cameras/types
```

**Request Body:**
```json
[
  {
    "id": "type-123",
    "name": "Dome"
  }
]
```

**Response:**
```json
{
  "success": true
}
```

---

### Get Registered Cars

```http
GET /api/cameras/registered_cars
```

**Response:**
```json
[
  {
    "id": "car-123",
    "plate_number": "65H-719.94",
    "owner": "Company ABC",
    "model": "Hino 500",
    "color": "White",
    "notes": "Regular delivery",
    "created_at": "2026-01-10 10:00:00",
    "box_dimensions": "2.5x6.0x2.3",
    "standard_volume": "34.5"
  }
]
```

---

### Save Registered Cars

```http
POST /api/cameras/registered_cars
```

**Request Body:**
```json
[
  {
    "id": "car-123",
    "plate_number": "65H-719.94",
    "owner": "Company ABC",
    "model": "Hino 500",
    "color": "White",
    "box_dimensions": "2.5x6.0x2.3",
    "standard_volume": "34.5",
    "notes": "Regular delivery"
  }
]
```

**Response:**
```json
{
  "success": true
}
```

---

## Data Models

### CameraConnectRequest

```typescript
{
  ip: string
  port: number = 8899
  user: string = "admin"
  password: string = ""
  name: string = "Camera"
  tag?: "front_cam" | "side_cam" | null
  detection_mode: "auto" | "manual" | "disabled" = "disabled"
}
```

### PTZMoveRequest

```typescript
{
  speed: number = 0.5  // Range: 0.1 - 1.0
}
```

### UpdateDetectionModeRequest

```typescript
{
  detection_mode: "auto" | "manual" | "disabled"
}
```

### UpdateCameraTagRequest

```typescript
{
  tag: "front_cam" | "side_cam" | null
}
```

### HistoryRecord

```typescript
{
  plate: string
  location: string
  time_in: string  // HH:MM:SS
  time_out: string  // HH:MM:SS or "---"
  vol_std: string  // Volume in m³
  vol_measured: string  // Volume in m³
  status: "đang vào" | "đã vào" | "đang cân" | "đang ra" | "đã ra"
  verify: "đã xác nhận" | "ngoài danh sách"
  note: string
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

- `200` - Success
- `404` - Resource not found
- `400` - Bad request / Invalid parameters
- `500` - Internal server error

### Common Errors

#### Camera Not Found
```json
{
  "detail": "Camera not found"
}
```

#### Connection Timeout
```json
{
  "success": false,
  "error": "Connection timed out after 10 seconds"
}
```

#### Invalid Detection Mode
```json
{
  "detail": "Invalid detection mode"
}
```

#### File Not Found
```json
{
  "detail": "Schedule file not found: /path/to/file.xlsx"
}
```

---

## CSV File Formats

### History Files (`history_dd_mm_yyyy.csv`)

```csv
plate,location,time_in,time_out,vol_std,vol_measured,status,verify,note
65H-719.94,Trạm Cân,13:34:50,14:40:15,14.5,14.4,đã vào,ngoài danh sách,Note text
```

### Captured Cars (`captured_cars_YYYY_MM_DD.csv`)

```csv
id,timestamp,folder_path,plate_number,primary_color,wheel_count,front_cam_id,side_cam_id,confidence,class_name,bbox
20260114_145030_abc,2026-01-14 14:50:30,/path/...,65H-719.94,white,4,cam-1,cam-2,0.95,car,"[100,200,300,400]"
```

### Cameras (`cameras.csv`)

```csv
id,name,ip,port,user,password,location,type,status,tag,username,brand,cam_id,location_id
uuid,Camera 1,192.168.1.100,8899,admin,pass123,Cổng Nam,Dome,Online,front_cam,admin,Hikvision,cam-1,loc-123
```

### Locations (`locations.csv`)

```csv
id,name
loc-123,Cổng Nam (Vào)
loc-456,Trạm Cân
```

### Camera Types (`camtypes.csv`)

```csv
id,name
type-123,Dome
type-456,Bullet
```

### Registered Cars (`registered_cars.csv`)

```csv
id,plate_number,owner,model,color,notes,created_at,box_dimensions,standard_volume
car-123,65H-719.94,Company ABC,Hino 500,White,Regular,2026-01-10 10:00:00,2.5x6.0x2.3,34.5
```

---

## Notes

- All timestamps are in format: `YYYY-MM-DD HH:MM:SS`
- History dates use format: `dd/mm/yyyy` or `dd_mm_yyyy`
- Captured car dates use format: `YYYY_MM_DD`
- Camera UUIDs are auto-generated if not provided
- CSV files are stored in `database/data/` directory
- Detection logs are stored in `database/data/logs/`

---

## Support & Contact

For issues or questions about the API, please refer to the main project documentation or contact the development team.

**Project Repository:** CamMana  
**Documentation Version:** 2.0.0  
**Last Updated:** 2026-01-14
