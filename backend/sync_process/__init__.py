"""
Sync Process Package

Handles all synchronization, system monitoring, and file sync operations.
Modules:
- sync/: Master/Client sync logic, Zeroconf discovery, proxy helpers
- system/: System information, firewall management
- file_sync/: File/folder uploads between nodes
"""

from backend.sync_process.sync.api import sync_router
from backend.sync_process.system.api import system_router
from backend.sync_process.file_sync.api import file_sync_router

__all__ = [
    'sync_router',
    'system_router', 
    'file_sync_router',
]
