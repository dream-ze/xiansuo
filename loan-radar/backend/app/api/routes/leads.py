from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.models.lead import Lead
from app.models.post import Post
from app.schemas.crm import LeadConvertToCrmIn
from app.schemas.lead import LeadOut
from app.services.crm_service import convert_lead_to_crm, customer_to_dict, opportunity_to_dict, task_to_dict
from app.services.export_service import (
    VALID_LEAD_STATUSES,
    build_leads_query,
    export_leads_csv,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadStatusUpdate(BaseModel):
    status: str
    notes: str | None = None


def not_found_response() -> JSONResponse:
    return JSONResponse(status_code=404, content=error_response("lead not found"))


def validation_error_response(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_response(message))


def _enrich_lead_out(lead: Lead, db: Session) -> dict:
    data = LeadOut.model_validate(lead).model_dump(mode="json")
    if lead.source_post_id is not None:
        post = db.query(Post).filter(Post.id == lead.source_post_id).first()
        if post is not None:
            data["source_post_title"] = post.title or post.content
            data["source_post_url"] = post.post_url
    return data


@router.get("/export")
def export_leads_endpoint(
    lead_level: str | None = None,
    demand_type: str | None = None,
    risk_level: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
    source_post_id: int | None = None,
    source_comment_id: int | None = None,
    is_duplicate: bool | None = None,
    converted_to_crm: bool | None = None,
    created_after: str | None = None,
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
        source_post_id=source_post_id,
        source_comment_id=source_comment_id,
        is_duplicate=is_duplicate,
        converted_to_crm=converted_to_crm,
        created_after=created_after,
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
    source_post_id: int | None = None,
    source_comment_id: int | None = None,
    is_duplicate: bool | None = None,
    converted_to_crm: bool | None = None,
    created_after: str | None = None,
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
        source_post_id=source_post_id,
        source_comment_id=source_comment_id,
        is_duplicate=is_duplicate,
        converted_to_crm=converted_to_crm,
        created_after=created_after,
    )
    total = query.count()
    leads = (
        query.order_by(Lead.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_enrich_lead_out(lead, db) for lead in leads]
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
    if payload.notes is not None:
        lead.notes = payload.notes
    db.commit()
    db.refresh(lead)

    data = _enrich_lead_out(lead, db)
    return success_response(data)


@router.post("/{lead_id}/convert-to-crm")
def convert_lead_to_crm_endpoint(
    lead_id: int,
    payload: LeadConvertToCrmIn,
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead is None:
        return not_found_response()

    try:
        customer, opportunity, task = convert_lead_to_crm(
            db=db,
            lead=lead,
            owner_name=payload.owner_name,
            next_follow_up_at=payload.next_follow_up_at,
        )
    except ValueError as exc:
        return validation_error_response(str(exc))

    return success_response(
        {
            "customer": customer_to_dict(customer),
            "opportunity": opportunity_to_dict(opportunity, db),
            "task": task_to_dict(task, db),
        }
    )
