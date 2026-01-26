from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from datetime import datetime
from typing import List, Dict, Any, Optional

from .logic import ReportLogic

router = APIRouter(prefix="/api/report", tags=["report"])
logic = ReportLogic()

@router.get("/today")
async def get_today_report():
    today = datetime.now().strftime("%d-%m-%Y")
    report = logic.get_report(today)
    if not report:
        report = logic.generate_report(today)
    return report

@router.get("/history")
async def get_report_history():
    return logic.list_reports()

@router.get("/detail")
async def get_report_detail(date: str = Query(..., description="Date in dd-mm-yyyy format")):
    report = logic.get_report(date)
    if not report:
        report = logic.generate_report(date)
    return report

@router.post("/generate")
async def generate_report(date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format. Defaults to today.")):
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")
    return logic.generate_report(date)

@router.get("/export/pdf")
async def export_report_pdf(date: Optional[str] = Query(None, description="Date in dd-mm-yyyy format. Defaults to today.")):
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
