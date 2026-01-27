
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import pandas as pd
import io
import logging

from backend.data_process.user.api import get_current_user
from backend.schemas import User as UserSchema

from backend.data_process.history.logic import HistoryLogic
from backend.sync_process.sync.proxy import is_client_mode, proxy_get, proxy_post, proxy_put
from backend.schemas import HistoryRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["History"])
logic = HistoryLogic()

class HistoryResponse(BaseModel):
    id: str
    plate: str
    location: str
    time_in: str
    time_out: str
    vol_std: str
    vol_measured: str
    status: str
    verify: str
    note: str
    folder_path: str

@router.get("/dates")
async def get_available_dates(request: Request):
    """
    Get available history dates.
    When in client mode, fetches from master node.
    """
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("Client mode: Fetching history dates from master")
        result = await proxy_get("/api/history/dates", token=token)
        if result is not None:
            return result
        logger.warning("Failed to fetch dates from master, falling back to local")
    
    return logic.get_available_dates()

@router.get("")
async def get_history(
    request: Request,
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format"),
    user: UserSchema = Depends(get_current_user)
):
    """
    Get history records. If date is None, returns today's records.
    When in client mode, fetches from master node.
    """
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"Client mode: Fetching history for date {date} from master")
        endpoint = "/api/history" if not date else f"/api/history?date={date}"
        result = await proxy_get(endpoint, token=token)
        if result is not None:
            return result
        logger.warning("Failed to fetch history from master, falling back to local")
    
    all_records = logic.get_records(date)
    return all_records

@router.post("")
async def add_history_record(request: Request, record: Dict[str, Any]):
    """
    Add a new history record.
    When in client mode, proxies to master node.
    """
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("Client mode: Adding history record via master")
        result = await proxy_post("/api/history", record, token=token)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
        
    try:
        new_record = logic.add_record(record)
        return new_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{record_id}")
async def update_history_record(request: Request, record_id: str, update_data: Dict[str, Any]):
    """
    Update a history record.
    When in client mode, proxies to master node.
    """
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"Client mode: Updating history record {record_id} via master")
        result = await proxy_put(f"/api/history/{record_id}", update_data, token=token)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")
    
    updated = logic.update_record(record_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found")
    return updated


# Status and verify mappings for export
STATUS_MAP = {
    'in': 'Đang trong',
    'out': 'Đã ra',
    'pending': 'Chờ xử lý'
}

VERIFY_MAP = {
    'verified': 'Đã xác minh',
    'unverified': 'Chưa xác minh',
    'rejected': 'Từ chối'
}


@router.get("/export/excel")
async def export_history_excel(
    request: Request,
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format")
):
    """
    Export history records to Excel (CSV format with UTF-8 BOM).
    Returns the file as a download.
    """
    records = logic.get_records(date)
    if not records:
        raise HTTPException(status_code=404, detail="No data to export")
    
    # Create DataFrame
    df = pd.DataFrame(records)
    
    # Map status and verify to Vietnamese labels
    if 'status' in df.columns:
        df['status'] = df['status'].map(lambda x: STATUS_MAP.get(x, x))
    if 'verify' in df.columns:
        df['verify'] = df['verify'].map(lambda x: VERIFY_MAP.get(x, x))
    
    # Rename columns for Vietnamese headers
    column_map = {
        'plate': 'Biển số',
        'location': 'Vị trí',
        'time_in': 'Thời gian Vào',
        'time_out': 'Thời gian Ra',
        'vol_std': 'Thể tích tiêu chuẩn (m3)',
        'vol_measured': 'Thể tích đo được (m3)',
        'status': 'Trạng thái',
        'verify': 'Xác minh',
        'note': 'Ghi chú',
    }
    df = df.rename(columns=column_map)
    
    # Select only needed columns in order
    cols = ['Biển số', 'Vị trí', 'Thời gian Vào', 'Thời gian Ra', 'Thể tích tiêu chuẩn (m3)', 'Thể tích đo được (m3)', 'Trạng thái', 'Xác minh', 'Ghi chú']
    existing_cols = [c for c in cols if c in df.columns]
    df = df[existing_cols]
    
    # Create CSV with UTF-8 BOM
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    csv_content = '\ufeff' + output.getvalue()
    
    date_str = date or datetime.now().strftime("%d-%m-%Y")
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=Lich_su_ra_vao_{date_str}.csv"
        }
    )


@router.post("/export/excel/save")
async def save_history_excel_to_downloads(
    request: Request,
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format"),
    user: UserSchema = Depends(get_current_user)
):
    """
    Export history records and save directly to user's Downloads folder.
    This endpoint is for desktop app usage where we can access local filesystem.
    """
    records = logic.get_records(date)
    if not records:
        raise HTTPException(status_code=404, detail="No data to export")
    
    # Create DataFrame
    df = pd.DataFrame(records)
    
    # Map status and verify to Vietnamese labels
    if 'status' in df.columns:
        df['status'] = df['status'].map(lambda x: STATUS_MAP.get(x, x))
    if 'verify' in df.columns:
        df['verify'] = df['verify'].map(lambda x: VERIFY_MAP.get(x, x))
    
    # Rename columns for Vietnamese headers
    column_map = {
        'plate': 'Biển số',
        'location': 'Vị trí',
        'time_in': 'Thời gian Vào',
        'time_out': 'Thời gian Ra',
        'vol_std': 'Thể tích tiêu chuẩn (m3)',
        'vol_measured': 'Thể tích đo được (m3)',
        'status': 'Trạng thái',
        'verify': 'Xác minh',
        'note': 'Ghi chú',
    }
    df = df.rename(columns=column_map)
    
    # Select only needed columns
    cols = ['Biển số', 'Vị trí', 'Thời gian Vào', 'Thời gian Ra', 'Thể tích tiêu chuẩn (m3)', 'Thể tích đo được (m3)', 'Trạng thái', 'Xác minh', 'Ghi chú']
    existing_cols = [c for c in cols if c in df.columns]
    df = df[existing_cols]
    
    try:
        # Get user's Downloads folder
        downloads_folder = Path.home() / "Downloads"
        if not downloads_folder.exists():
            downloads_folder = Path.home() / "Desktop"
        
        # Create filename with timestamp
        date_str = date or datetime.now().strftime("%d-%m-%Y")
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = f"Lich_su_ra_vao_{date_str}_{timestamp}.csv"
        file_path = downloads_folder / filename
        
        # Write CSV with UTF-8 BOM
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            df.to_csv(f, index=False)
        
        logger.info(f"History Excel saved to: {file_path}")
        return {
            "success": True,
            "message": "File saved successfully",
            "file_path": str(file_path)
        }
    except Exception as e:
        logger.error(f"Error saving history Excel to downloads: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

