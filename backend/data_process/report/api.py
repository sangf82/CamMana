from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Response, Request
import logging

from .logic import ReportLogic
from backend.api.user import get_current_user
from backend.schemas import User as UserSchema
from backend.data_process.sync.proxy import is_client_mode, proxy_get, proxy_post

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])
logic = ReportLogic()

@router.get("/today")
async def get_today_report(request: Request, user: UserSchema = Depends(get_current_user)):
    """Get today's report. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("Client mode: Fetching today's report from master")
        result = await proxy_get("/api/report/today", token=token)
        if result is not None:
            return result
    
    today = datetime.now().strftime("%d-%m-%Y")
    report = logic.get_report(today)
    if not report:
        report = logic.generate_report(today)
    return report

@router.get("/history")
async def get_report_history(request: Request, user: UserSchema = Depends(get_current_user)):
    """Get report history. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("Client mode: Fetching report history from master")
        result = await proxy_get("/api/report/history", token=token)
        if result is not None:
            return result
    
    return logic.list_reports()

@router.get("/detail")
async def get_report_detail(
    request: Request,
    date: str = Query(..., description="Date in dd-mm-yyyy format"),
    user: UserSchema = Depends(get_current_user)
):
    """Get report detail for a specific date. Proxies to Master when in Client mode."""
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"Client mode: Fetching report detail for {date} from master")
        result = await proxy_get(f"/api/report/detail?date={date}", token=token)
        if result is not None:
            return result
    
    report = logic.get_report(date)
    if not report:
        report = logic.generate_report(date)
    return report

@router.post("/generate")
async def generate_report(
    request: Request,
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format. Defaults to today."),
    user: UserSchema = Depends(get_current_user)
):
    # Proxy to master if in client mode
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        query = f"?date={date}" if date else ""
        result = await proxy_post(f"/api/report/generate{query}", {}, token=token)
        if result is not None:
            return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")

    if not date:
        date = datetime.now().strftime("%d-%m-%Y")
    return logic.generate_report(date)

@router.get("/export/pdf")
async def export_report_pdf(
    request: Request,
    date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format. Defaults to today."),
    user: UserSchema = Depends(get_current_user)
):
    # CLIENT MODE PROXY for PDF
    if is_client_mode():
        from backend.data_process.sync.proxy import get_master_url
        import httpx
        master_url = get_master_url()
        if not master_url:
             raise HTTPException(503, "Master URL not configured")
        
        query = f"?date={date}" if date else ""
        url = f"{master_url.rstrip('/')}/api/report/export/pdf{query}"
        
        try:
            token = request.headers.get("authorization", "").replace("Bearer ", "")
            headers = {}
            if token: headers["Authorization"] = f"Bearer {token}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                     return Response(
                        content=response.content,
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": response.headers.get("Content-Disposition", f"attachment; filename=report.pdf")
                        }
                    )
                else:
                     raise HTTPException(response.status_code, "Master failed to generate PDF")
        except Exception as e:
            logger.error(f"PDF Proxy failed: {e}")
            raise HTTPException(503, f"Failed to fetch PDF from master: {e}")

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

