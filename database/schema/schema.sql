-- CamMana Database Schema
-- SQLite database for camera configurations and captured car records

-- cameras table: stores camera connection configs
CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER DEFAULT 8899,
    username TEXT DEFAULT 'admin',
    password TEXT,
    profile_token TEXT,
    stream_uri TEXT,
    resolution_width INTEGER,
    resolution_height INTEGER,
    fps REAL,
    tag TEXT CHECK(tag IN ('front_cam', 'side_cam', NULL)),
    detection_mode TEXT DEFAULT 'disabled' CHECK(detection_mode IN ('auto', 'manual', 'disabled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for IP lookup
CREATE INDEX IF NOT EXISTS idx_cameras_ip ON cameras(ip);
CREATE INDEX IF NOT EXISTS idx_cameras_tag ON cameras(tag);

-- captured_cars table: metadata for each detection event
CREATE TABLE IF NOT EXISTS captured_cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    plate_number TEXT,
    primary_color TEXT,
    wheel_count INTEGER,
    front_cam_id TEXT REFERENCES cameras(id),
    side_cam_id TEXT REFERENCES cameras(id),
    confidence REAL,
    bbox TEXT,  -- JSON string of [x1, y1, x2, y2]
    class_name TEXT,  -- 'car' or 'truck'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for timestamp lookup
CREATE INDEX IF NOT EXISTS idx_captured_cars_timestamp ON captured_cars(timestamp);
CREATE INDEX IF NOT EXISTS idx_captured_cars_plate ON captured_cars(plate_number);

-- detection_logs table: tracking detection events for debugging
CREATE TABLE IF NOT EXISTS detection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id TEXT REFERENCES cameras(id),
    event_type TEXT NOT NULL,  -- 'detected', 'skipped_iou', 'captured', 'error'
    details TEXT,  -- JSON with additional info
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
