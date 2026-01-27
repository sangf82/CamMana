"""
File Sync API Endpoints

Handles file/folder uploads from Client nodes to Master node.
This enables full data sync including images and evidence files.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

from backend.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

file_sync_router = APIRouter(prefix="/api/sync/files", tags=["file-sync"])

# Base directory for synced car history
CAR_HISTORY_DIR = PROJECT_ROOT / "database" / "car_history"


@file_sync_router.post("/upload-folder")
async def upload_folder(
    folder_name: str = Form(...),
    date_folder: str = Form(...),
    source_pc: str = Form(default="unknown"),
    files: List[UploadFile] = File(...)
):
    """
    Receive a car history folder from a Client node.
    
    Creates the same folder structure on Master and saves all files.
    
    Args:
        folder_name: The folder name (uuid_direction_time format)
        date_folder: The date folder (dd-mm-yyyy format)
        source_pc: The hostname/IP of the source PC
        files: List of files to upload
    
    Returns:
        The new folder path on Master
    """
    try:
        # Validate inputs
        if not folder_name or not date_folder:
            raise HTTPException(status_code=400, detail="folder_name and date_folder required")
        
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Create folder structure
        date_path = CAR_HISTORY_DIR / date_folder
        date_path.mkdir(parents=True, exist_ok=True)
        
        folder_path = date_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        # Save each file
        for upload_file in files:
            try:
                file_path = folder_path / upload_file.filename
                
                # Read and write file content
                content = await upload_file.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                
                saved_files.append(upload_file.filename)
                logger.debug(f"Saved file: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to save file {upload_file.filename}: {e}")
                continue
        
        logger.info(f"[FileSync] Received folder from {source_pc}: {folder_name} with {len(saved_files)} files")
        
        return {
            "success": True,
            "folder_path": str(folder_path),
            "date_folder": date_folder,
            "folder_name": folder_name,
            "files_received": saved_files,
            "file_count": len(saved_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FileSync] Upload folder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@file_sync_router.post("/upload-file")
async def upload_single_file(
    folder_path: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a single file to an existing folder on Master.
    
    Args:
        folder_path: Relative path from car_history (e.g., "dd-mm-yyyy/uuid_in_time")
        file: The file to upload
    """
    try:
        target_folder = CAR_HISTORY_DIR / folder_path
        target_folder.mkdir(parents=True, exist_ok=True)
        
        file_path = target_folder / file.filename
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"[FileSync] Saved single file: {file_path}")
        
        return {
            "success": True,
            "file_path": str(file_path)
        }
        
    except Exception as e:
        logger.error(f"[FileSync] Upload file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@file_sync_router.get("/health")
async def file_sync_health():
    """Check if file sync is available"""
    return {
        "available": True,
        "car_history_dir": str(CAR_HISTORY_DIR),
        "exists": CAR_HISTORY_DIR.exists()
    }
