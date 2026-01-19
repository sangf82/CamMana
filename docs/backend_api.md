# Backend API Documentation

## Overview
This API is built with FastAPI and serves as the backend for the CamMana application. It handles camera management, video streaming, vehicle detection, check-in processing, and data storage.

**Base URL**: `http://localhost:8000` (Default)

## 1. Camera Management
Base Path: `/api/cameras`

### Get All Cameras
- **GET** `/api/cameras`
- Retrieves a list of all connected and configured cameras with their current status (online/offline, streaming status).

### Save Camera Config
- **POST** `/api/cameras`
- data: `CameraCreate` schema
- Saves or updates a camera's configuration (IP, credentials, name).

### Delete Camera
- **DELETE** `/api/cameras/{camera_id}`
- Removes a camera from the configuration and disconnects it if active.

### Get Saved Cameras
- **GET** `/api/cameras/saved`
- Returns all persistent camera configurations stored in the database.

### Connect Camera
- **POST** `/api/cameras/connect`
- data: `CameraConnectRequest`
- Attempts to connect to an ONVIF camera and initialize a streamer.

### Disconnect Camera
- **POST** `/api/cameras/{camera_id}/disconnect`
- Disconnects an active camera session.

### Update Detection Mode
- **POST** `/api/cameras/{camera_id}/detection_mode`
- data: `{"detection_mode": "auto" | "manual" | "disabled"}`
- Enable or disable auto-detection for a specific camera.

### Update Camera Tag
- **POST** `/api/cameras/{camera_id}/tag`
- data: `{"tag": "front_cam" | "side_cam"}`
- Assigns a role tag to the camera.

## 2. Video Streaming & PTZ
Base Path: `/api/cameras`

### Start/Stop Stream
- **POST** `/api/cameras/{camera_id}/stream/start`
- **POST** `/api/cameras/{camera_id}/stream/stop`

### Video Feed
- **GET** `/api/cameras/{camera_id}/stream`
- Returns an MJPEG video stream.

### Snapshot
- **GET** `/api/cameras/{camera_id}/snapshot`
- Returns a single JPEG frame.

### Capture Image
- **POST** `/api/cameras/{camera_id}/capture`
- Captures and saves an image to disk.

### PTZ Controls
- **POST** `/api/cameras/{camera_id}/ptz/{action}`
- Actions: `up`, `down`, `left`, `right`, `zoom-in`, `zoom-out`, `stop`
- data: `{"speed": float}`

## 3. Check-In & Processing
Base Path: `/api/checkin`

### Capture and Process
- **POST** `/api/checkin/capture-and-process`
- data: `CaptureAndProcessRequest` (front_camera_id, side_camera_id, location_id)
- Triggers simultaneous capture from cameras, runs AI analysis (plate, color, wheels), and logs the check-in.

### Process Uploaded Images
- **POST** `/api/checkin/process`
- multipart/form-data: `front_image`, `side_image`, `location_id`
- Process a check-in using manually uploaded images.

### Verify Plate
- **POST** `/api/checkin/verify`
- data: `VerifyPlateRequest`
- Submit human verification of an AI-detected license plate.

### Get Pending Verifications
- **GET** `/api/checkin/pending`
- value: List of check-ins requiring human approval.

### Get Check-in Status
- **GET** `/api/checkin/status/{folder_name}`
- Retrieve the status of a specific check-in transaction.

## 4. Configuration & Data
Base Path: `/api/cameras` (shared prefix)

### Locations
- **GET** `/api/cameras/locations`
- **POST** `/api/cameras/locations`
- Manage physical locations (gates, stations).

### Camera Types
- **GET** `/api/cameras/types`
- **POST** `/api/cameras/types`
- Manage camera model types.

### Registered Cars
- **GET** `/api/cameras/registered_cars`
- **POST** `/api/cameras/registered_cars`
- **POST** `/api/cameras/registered_cars/import`
- Manage the database of authorized vehicles.

### Location Tags
- **GET** `/api/cameras/locations/grouped`
- **GET** `/api/cameras/locations/tags/{tag}/config`
- Get camera groups and detection strategies per location tag.

## 5. History & Logs
Base Path: `/api`

### History Log
- **GET** `/api/history` (Optional `?date=dd/mm/yyyy`)
- **POST** `/api/history` (Add record)
- **PUT** `/api/history` (Update record)
- Manage daily entry/exit logs.

### Detection JSON Logs
- **GET** `/api/detection_logs`
- Raw detection event logs.

### Captured Cars Metadata
- **GET** `/api/captured_cars`
- List of processed vehicle captures.

## 6. Static Resources

### Car Images
- **GET** `/api/images/{date_folder}/{car_folder}/{filename}`
- Serve captured images for evidence/display.
