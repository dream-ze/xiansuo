from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.core.deps import require_current_user
from app.schemas.daily_report import DailyReportOut
from app.services.daily_report_service import (
    generate_daily_report,
    get_today_report,
    list_daily_reports,
)
from app.services.report_export_service import export_report_markdown
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/daily-reports", tags=["daily-reports"], dependencies=[Depends(require_current_user)])


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


@router.get("/today/export")
def export_today_report_endpoint(
    format: str = "markdown",
    platform: str | None = None,
    db: Session = Depends(get_db),
):
    report = get_today_report(db, platform=platform)
    if report is None:
        return JSONResponse(
            status_code=404,
            content=error_response("今日尚未生成报告，请先生成报告后再导出"),
        )

    if format == "markdown" or format == "md":
        md_content = export_report_markdown(report)
        report_date = report.report_date.isoformat()
        filename = f"loan-radar-report-{report_date}.md"
        return Response(
            content=md_content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    return JSONResponse(
        status_code=400,
        content=error_response(f"不支持的导出格式: {format}，目前仅支持 markdown"),
    )


@router.get("")
def list_daily_reports_endpoint(
    platform: str | None = None,
    db: Session = Depends(get_db),
):
    reports = list_daily_reports(db, platform=platform)
    items = [DailyReportOut.model_validate(r).model_dump(mode="json") for r in reports]
    return success_response(items)
