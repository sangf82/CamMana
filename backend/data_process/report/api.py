from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Response
import logging

from .logic import ReportLogic
from backend.api.user import get_current_user
from backend.schemas import User as UserSchema
from backend.data_process.sync.proxy import is_client_mode, proxy_get

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])
logic = ReportLogic()

@router.get("/today")
async def get_today_report(user: UserSchema = Depends(get_current_user)):
    """Get today's report. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info("Client mode: Fetching today's report from master")
        result = await proxy_get("/api/report/today")
        if result is not None:
            return result
    
    today = datetime.now().strftime("%d-%m-%Y")
    report = logic.get_report(today)
    if not report:
        report = logic.generate_report(today)
    return report

@router.get("/history")
async def get_report_history(user: UserSchema = Depends(get_current_user)):
    """Get report history. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info("Client mode: Fetching report history from master")
        result = await proxy_get("/api/report/history")
        if result is not None:
            return result
    
    return logic.list_reports()

@router.get("/detail")
async def get_report_detail(
    date: str = Query(..., description="Date in dd-mm-yyyy format"),
    user: UserSchema = Depends(get_current_user)
):
    """Get report detail for a specific date. Proxies to Master when in Client mode."""
    if is_client_mode():
        logger.info(f"Client mode: Fetching report detail for {date} from master")
        result = await proxy_get(f"/api/report/detail?date={date}")
        if result is not None:
            return result
    
    report = logic.get_report(date)
    if not report:
        report = logic.generate_report(date)
    return report

@router.post("/generate")
async def generate_report(
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format. Defaults to today."),
    user: UserSchema = Depends(get_current_user)
):
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")
    return logic.generate_report(date)

@router.get("/export/pdf")
async def export_report_pdf(
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format. Defaults to today."),
    user: UserSchema = Depends(get_current_user)
):
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")
    
    pdf_content = logic.export_pdf(date)
    if not pdf_content:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{date}.pdf"
        }
    )

