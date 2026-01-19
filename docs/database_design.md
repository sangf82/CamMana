# Database Design Documentation

## Overview
This project uses a CSV-based storage system for handling vehicle data, history logs, and configuration. The system is designed to create daily files for time-series data and handle expiration policies automatically.

## Data Storage Location
- **Path**: `database/csv_data/`
- **Format**: Comma-Separated Values (CSV)

## Entities

### 1. Registered Cars (`registered_cars.csv`)
Stores information about vehicles authorized or registered in the system.
- **File Pattern**: `registered_cars_dd-mm-yyyy.csv`
- **Lifecycle**: Daily file. Migrates data from the previous day if no new import occurs. Expires after 48 hours.
- **Schema**:
  - `id`: Unique identifier
  - `plate_number`: Vehicle license plate
  - `vehicle_type`: Type of vehicle (e.g., Truck)
  - `driver_name`: Name of the driver
  - `company`: Company name
  - `created_at`: Date created
  - `updated_at`: Date updated
  - `status`: Registration status

### 2. History (`history.csv`)
Logs vehicle entry/exit events and processing results.
- **File Pattern**: `history_dd_mm_yyyy.csv`
- **Lifecycle**: New empty file created daily. Expires after 48 hours.
- **Schema**:
  - `plate`: Vehicle license plate
  - `location`: Gate or camera location
  - `time_in`: Time of entry
  - `time_out`: Time of exit
  - `vol_std`: Standard volume
  - `vol_measured`: Measured volume
  - `status`: Processing status
  - `verify`: Verification status
  - `note`: Additional notes

### 3. Cameras (`cameras.csv`)
Stores configuration for camera streams.
- **File**: `cameras.csv` (Static/Config)
- **Schema**:
  - `id`: Camera ID
  - `name`: Display name
  - `rtsp_url`: RTSP stream URL
  - `location`: Physical location tag
  - `status`: Online/Offline status

### 4. Captured Cars (`captured_cars.csv`)
Temporary or processed logs of captured vehicle images and detection metadata.
- **File Pattern**: `captured_cars_dd-mm-yyyy.csv`
- **Lifecycle**: Daily file.

## Data Access Layer
Data access is managed by the `backend.data_process` module:
- `registered_cars.py`: Handles CRUD and migration for registered cars.
- `history.py`: Handles appending and reading history logs.
- `cameras.py`: Manages camera configuration.
- `_common.py`: Shared utilities for CSV reading/writing and locking.
