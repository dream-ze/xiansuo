from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadOut
from app.services.export_service import (
    VALID_LEAD_STATUSES,
    build_leads_query,
    export_leads_csv,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadStatusUpdate(BaseModel):
    status: str


def not_found_response() -> JSONResponse:
    return JSONResponse(status_code=404, content=error_response("lead not found"))


def validation_error_response(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_response(message))


# /export 必须在 /{lead_id} 之前注册，避免 FastAPI 将 "export" 当成 id 匹配
@router.get("/export")
def export_leads_endpoint(
    lead_level: str | None = None,
    demand_type: str | None = None,
    risk_level: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    query = build_leads_query(
        db=db,
        lead_level=lead_level,
        demand_type=demand_type,
        risk_level=risk_level,
        platform=platform,
        status=status,
        source_type=source_type,
        keyword=keyword,
    )
    leads = query.order_by(Lead.id.desc()).all()
    csv_bytes = export_leads_csv(leads)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.get("")
def list_leads_endpoint(
    lead_level: str | None = None,
    demand_type: str | None = None,
    risk_level: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = build_leads_query(
        db=db,
        lead_level=lead_level,
        demand_type=demand_type,
        risk_level=risk_level,
        platform=platform,
        status=status,
        source_type=source_type,
        keyword=keyword,
    )
    total = query.count()
    leads = (
        query.order_by(Lead.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [LeadOut.model_validate(lead).model_dump(mode="json") for lead in leads]
    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.patch("/{lead_id}/status")
def update_lead_status_endpoint(
    lead_id: int,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
):
    if payload.status not in VALID_LEAD_STATUSES:
        return validation_error_response(
            f"invalid status, must be one of: {', '.join(sorted(VALID_LEAD_STATUSES))}"
        )

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead is None:
        return not_found_response()

    lead.status = payload.status
    db.commit()
    db.refresh(lead)

    data = LeadOut.model_validate(lead).model_dump(mode="json")
    return success_response(data)
