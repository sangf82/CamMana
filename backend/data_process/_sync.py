"""
Sync utility for keeping cameras.csv in sync with locations.csv and camtypes.csv
"""
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional
from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

class CameraDataSync:
    """Synchronizes camera data with related tables (locations, camera types)."""
    
    CAMERAS_FILE = DATA_DIR / "cameras.csv"
    CAMERA_HEADERS = ["id", "name", "ip", "port", "username", "password", 
                      "location", "type", "status", "tag", "brand", "cam_id", "location_id"]

    @classmethod
    def _read_cameras(cls) -> List[Dict[str, str]]:
        if not cls.CAMERAS_FILE.exists():
            return []
        with open(cls.CAMERAS_FILE, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    @classmethod
    def _write_cameras(cls, data: List[Dict[str, str]]):
        with open(cls.CAMERAS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cls.CAMERA_HEADERS)
            writer.writeheader()
            for row in data:
                # Ensure only valid headers are written
                filtered_row = {k: row.get(k, '') for k in cls.CAMERA_HEADERS}
                writer.writerow(filtered_row)

    @classmethod
    def sync_location_name(cls, location_id: str, new_name: str) -> int:
        """
        Update cameras that reference this location_id with the new location name.
        Returns number of cameras updated.
        """
        cameras = cls._read_cameras()
        updated_count = 0
        
        for cam in cameras:
            if cam.get('location_id') == location_id:
                old_name = cam.get('location', '')
                if old_name != new_name:
                    cam['location'] = new_name
                    updated_count += 1
                    logger.info(f"Camera {cam['name']}: location updated '{old_name}' -> '{new_name}'")
        
        if updated_count > 0:
            cls._write_cameras(cameras)
            logger.info(f"Synced location name for {updated_count} camera(s)")
        
        return updated_count

    @classmethod
    def sync_camtype_name(cls, old_name: str, new_name: str) -> int:
        """
        Update cameras that have this camera type with the new type name.
        Returns number of cameras updated.
        """
        cameras = cls._read_cameras()
        updated_count = 0
        
        for cam in cameras:
            if cam.get('type') == old_name:
                cam['type'] = new_name
                updated_count += 1
                logger.info(f"Camera {cam['name']}: type updated '{old_name}' -> '{new_name}'")
        
        if updated_count > 0:
            cls._write_cameras(cameras)
            logger.info(f"Synced camera type name for {updated_count} camera(s)")
        
        return updated_count

    @classmethod
    def remove_location_references(cls, location_id: str) -> int:
        """
        Clear location references for cameras when a location is deleted.
        Returns number of cameras affected.
        """
        cameras = cls._read_cameras()
        affected_count = 0
        
        for cam in cameras:
            if cam.get('location_id') == location_id:
                cam['location'] = ''
                cam['location_id'] = ''
                affected_count += 1
                logger.info(f"Camera {cam['name']}: location reference cleared")
        
        if affected_count > 0:
            cls._write_cameras(cameras)
            logger.info(f"Cleared location for {affected_count} camera(s)")
        
        return affected_count

    @classmethod
    def remove_camtype_references(cls, type_name: str) -> int:
        """
        Clear camera type for cameras when a type is deleted.
        Returns number of cameras affected.
        """
        cameras = cls._read_cameras()
        affected_count = 0
        
        for cam in cameras:
            if cam.get('type') == type_name:
                cam['type'] = ''
                affected_count += 1
                logger.info(f"Camera {cam['name']}: type reference cleared")
        
        if affected_count > 0:
            cls._write_cameras(cameras)
            logger.info(f"Cleared type for {affected_count} camera(s)")
        
        return affected_count

    @classmethod
    def full_sync(cls, locations_data: list, camtypes_data: list) -> Dict[str, int]:
        """
        Full sync: Update all cameras with correct location and type names
        based on their location_id and type references.
        Call this on startup or when you want to fix mismatches.
        """
        cameras = cls._read_cameras()
        updated_locations = 0
        updated_types = 0
        
        # Build lookup maps
        location_map = {loc['id']: loc['name'] for loc in locations_data}
        type_map = {t['name']: t['name'] for t in camtypes_data}  # Just for validation
        
        for cam in cameras:
            # Sync location name from location_id
            loc_id = cam.get('location_id', '')
            if loc_id and loc_id in location_map:
                correct_name = location_map[loc_id]
                if cam.get('location') != correct_name:
                    logger.info(f"Camera {cam['name']}: location '{cam.get('location')}' -> '{correct_name}'")
                    cam['location'] = correct_name
                    updated_locations += 1
        
        if updated_locations > 0 or updated_types > 0:
            cls._write_cameras(cameras)
            logger.info(f"Full sync: {updated_locations} locations, {updated_types} types updated")
        
        return {"locations": updated_locations, "types": updated_types}

