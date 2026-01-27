"""
File Sync Module - File/folder uploads between nodes

Handles file synchronization for car history images and evidence files.
"""

from backend.sync_process.file_sync.api import file_sync_router

__all__ = ['file_sync_router']
