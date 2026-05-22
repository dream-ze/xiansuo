from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.core.deps import require_current_user
from app.schemas.monitor_source import MonitorSourceOut
from app.schemas.pending_competitor import PendingCompetitorOut
from app.services.competitor_discovery_service import CompetitorDiscoveryService
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/pending-competitors", tags=["pending-competitors"], dependencies=[Depends(require_current_user)])
service = CompetitorDiscoveryService()


def not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_response("同行账号未找到"),
    )


def validation_error_response(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_response(message),
    )


@router.get("")
def list_pending_competitors_endpoint(
    platform: str | None = None,
    status: str | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    db: Session = Depends(get_db),
):
    items = service.list_pending_competitors(
        db=db,
        platform=platform,
        status=status,
        min_score=min_score,
    )
    data = [PendingCompetitorOut.model_validate(item).model_dump(mode="json") for item in items]
    return success_response(data)


@router.post("/{id}/approve")
def approve_pending_competitor_endpoint(
    id: int,
    db: Session = Depends(get_db),
):
    competitor = service.get_pending_competitor(db, id)
    if competitor is None:
        return not_found_response()

    try:
        approved_competitor, monitor_source = service.approve_pending_competitor(db, competitor)
    except ValueError as error:
        return validation_error_response(str(error))

    data = {
        "pending_competitor": PendingCompetitorOut.model_validate(approved_competitor).model_dump(mode="json"),
        "monitor_source": MonitorSourceOut.model_validate(monitor_source).model_dump(mode="json"),
    }
    return success_response(data)


@router.post("/{id}/ignore")
def ignore_pending_competitor_endpoint(
    id: int,
    db: Session = Depends(get_db),
):
    competitor = service.get_pending_competitor(db, id)
    if competitor is None:
        return not_found_response()

    try:
        ignored_competitor = service.ignore_pending_competitor(db, competitor)
    except ValueError as error:
        return validation_error_response(str(error))

    data = PendingCompetitorOut.model_validate(ignored_competitor).model_dump(mode="json")
    return success_response(data)
