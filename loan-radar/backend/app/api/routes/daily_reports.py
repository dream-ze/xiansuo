from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.schemas.daily_report import DailyReportOut
from app.services.daily_report_service import (
    generate_daily_report,
    get_today_report,
    list_daily_reports,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/daily-reports", tags=["daily-reports"])


@router.post("/generate")
def generate_daily_report_endpoint(
    platform: str | None = None,
    db: Session = Depends(get_db),
):
    report = generate_daily_report(db, platform=platform)
    data = DailyReportOut.model_validate(report).model_dump(mode="json")
    return success_response(data)


@router.get("/today")
def get_today_report_endpoint(
    platform: str | None = None,
    db: Session = Depends(get_db),
):
    report = get_today_report(db, platform=platform)
    if report is None:
        return JSONResponse(
            status_code=404,
            content=error_response("today's report not found, please generate first"),
        )
    data = DailyReportOut.model_validate(report).model_dump(mode="json")
    return success_response(data)


@router.get("")
def list_daily_reports_endpoint(
    platform: str | None = None,
    db: Session = Depends(get_db),
):
    reports = list_daily_reports(db, platform=platform)
    items = [DailyReportOut.model_validate(r).model_dump(mode="json") for r in reports]
    return success_response(items)
