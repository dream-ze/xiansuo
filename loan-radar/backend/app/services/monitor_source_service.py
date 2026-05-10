from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.monitor_source import MonitorSource
from app.schemas.monitor_source import MonitorSourceCreate, MonitorSourceUpdate

SUPPORTED_SOURCE_TYPES = {
    "keyword",
    "competitor_account",
    "manual_post",
    "hot_post_rule",
}

SUPPORTED_PLATFORMS = {
    "xhs",
    "douyin",
    "zhihu",
    "other",
}


def validate_source_type(source_type: str) -> None:
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"unsupported source_type: {source_type}")


def validate_platform(platform: str) -> None:
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")


def create_monitor_source(db: Session, payload: MonitorSourceCreate) -> MonitorSource:
    validate_source_type(payload.source_type)
    validate_platform(payload.platform)

    monitor_source = MonitorSource(**payload.model_dump())
    db.add(monitor_source)
    db.commit()
    db.refresh(monitor_source)
    return monitor_source


def list_monitor_sources(
    db: Session,
    source_type: str | None = None,
    platform: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
) -> list[MonitorSource]:
    if source_type is not None:
        validate_source_type(source_type)
    if platform is not None:
        validate_platform(platform)

    query = db.query(MonitorSource)

    if source_type is not None:
        query = query.filter(MonitorSource.source_type == source_type)
    if platform is not None:
        query = query.filter(MonitorSource.platform == platform)
    if enabled is not None:
        query = query.filter(MonitorSource.enabled == enabled)
    if keyword:
        keyword_pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                MonitorSource.name.ilike(keyword_pattern),
                MonitorSource.value.ilike(keyword_pattern),
            )
        )

    return query.order_by(MonitorSource.id.desc()).all()


def get_monitor_source(db: Session, monitor_source_id: int) -> MonitorSource | None:
    return db.query(MonitorSource).filter(MonitorSource.id == monitor_source_id).first()


def update_monitor_source(
    db: Session,
    monitor_source: MonitorSource,
    payload: MonitorSourceUpdate,
) -> MonitorSource:
    update_data = payload.model_dump(exclude_unset=True)

    if "source_type" in update_data and update_data["source_type"] is not None:
        validate_source_type(update_data["source_type"])
    if "platform" in update_data and update_data["platform"] is not None:
        validate_platform(update_data["platform"])

    for field, value in update_data.items():
        setattr(monitor_source, field, value)

    db.commit()
    db.refresh(monitor_source)
    return monitor_source


def toggle_monitor_source(
    db: Session,
    monitor_source: MonitorSource,
    enabled: bool | None = None,
) -> MonitorSource:
    monitor_source.enabled = (not monitor_source.enabled) if enabled is None else enabled
    db.commit()
    db.refresh(monitor_source)
    return monitor_source


def delete_monitor_source(db: Session, monitor_source: MonitorSource) -> None:
    db.delete(monitor_source)
    db.commit()
