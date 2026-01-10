"""Database Utility Module - SQLite for Camera Configuration Only

Note: Captured car data and detection logs are now stored in daily CSV files.
See csv_storage.py for those functions.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database paths
DB_DIR = Path(__file__).parent.parent.parent / "database"
DB_PATH = DB_DIR / "cammana.db"
SCHEMA_PATH = DB_DIR / "schema" / "schema.sql"

@contextmanager
def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    with get_connection() as conn:
        conn.executescript(schema_sql)
    print(f"[DB] Initialized at {DB_PATH}")
    return True

# Camera CRUD
def save_camera(data: Dict[str, Any]) -> bool:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO cameras (id, name, ip, port, username, password, profile_token, stream_uri,
                resolution_width, resolution_height, fps, tag, detection_mode, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, ip=excluded.ip, port=excluded.port, username=excluded.username,
                password=excluded.password, profile_token=excluded.profile_token, stream_uri=excluded.stream_uri,
                resolution_width=excluded.resolution_width, resolution_height=excluded.resolution_height,
                fps=excluded.fps, tag=excluded.tag, detection_mode=excluded.detection_mode, updated_at=CURRENT_TIMESTAMP
        """, (data.get('id'), data.get('name', 'Camera'), data.get('ip'), data.get('port', 8899),
              data.get('username', 'admin'), data.get('password', ''), data.get('profile_token'),
              data.get('stream_uri'), data.get('resolution_width'), data.get('resolution_height'),
              data.get('fps'), data.get('tag'), data.get('detection_mode', 'disabled')))
    return True

def get_camera(camera_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
        return dict(row) if row else None

def get_all_cameras() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cameras ORDER BY created_at DESC").fetchall()]

def get_cameras_by_tag(tag: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cameras WHERE tag = ?", (tag,)).fetchall()]

def delete_camera(camera_id: str) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
    return True

def update_camera_detection_mode(camera_id: str, mode: str) -> bool:
    if mode not in ('auto', 'manual', 'disabled'):
        raise ValueError(f"Invalid detection mode: {mode}")
    with get_connection() as conn:
        conn.execute("UPDATE cameras SET detection_mode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (mode, camera_id))
    return True

# Auto-init
if not DB_PATH.exists():
    try:
        init_db()
    except Exception as e:
        print(f"[DB] Warning: {e}")
