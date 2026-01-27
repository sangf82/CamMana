"""
Sync Module - Master/Client synchronization logic

Handles Zeroconf discovery, data synchronization, and sync configuration.
"""

from backend.sync_process.sync.logic import SyncLogic
from backend.sync_process.sync.proxy import (
    is_client_mode,
    get_master_url,
    get_sync_config,
    proxy_get,
    proxy_post,
    proxy_put,
    proxy_delete,
    upload_folder_to_master,
    sync_folder_and_update_record
)

__all__ = [
    'SyncLogic',
    'is_client_mode',
    'get_master_url',
    'get_sync_config',
    'proxy_get',
    'proxy_post',
    'proxy_put',
    'proxy_delete',
    'upload_folder_to_master',
    'sync_folder_and_update_record'
]
