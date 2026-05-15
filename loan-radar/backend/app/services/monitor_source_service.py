from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.collectors.config import CollectorConfig
from app.models.monitor_source import MonitorSource
from app.schemas.monitor_source import MonitorSourceCreate, MonitorSourceUpdate

SUPPORTED_SOURCE_TYPES = {
    "keyword",
    "competitor_account",
    "manual_post",
    "hot_post_rule",
}

SOURCE_TYPE_ALIASES = {
    "account": "competitor_account",
    "post_url": "manual_post",
}

SUPPORTED_PLATFORMS = {
    "xhs",
    "douyin",
    "kuaishou",
    "bilibili",
    "weibo",
    "tieba",
    "zhihu",
    "other",
}


def _collector_type(config) -> str:
    if isinstance(config, dict):
        return str(config.get("collector_type", "mock"))
    return "mock"


def validate_source_type(source_type: str) -> None:
    normalized = SOURCE_TYPE_ALIASES.get(source_type, source_type)
    if normalized not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"unsupported source_type: {source_type}")


def normalize_source_type(source_type: str | None) -> str | None:
    if source_type is None:
        return None
    return SOURCE_TYPE_ALIASES.get(source_type, source_type)


def validate_platform(platform: str) -> None:
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")


def validate_monitor_source_payload(payload: MonitorSourceCreate | MonitorSourceUpdate) -> None:
    source_type = normalize_source_type(payload.source_type)
    platform = payload.platform

    if source_type is not None:
        validate_source_type(source_type)
    if platform is not None:
        validate_platform(platform)

    collector_type = _collector_type(payload.config).strip().lower()
    config_obj = CollectorConfig.parse(payload.config)
    is_valid, error_message = config_obj.validate_collector_type()
    if not is_valid:
        raise ValueError(error_message)


def create_monitor_source(db: Session, payload: MonitorSourceCreate) -> MonitorSource:
    validate_monitor_source_payload(payload)

    create_data = payload.model_dump()
    create_data["source_type"] = normalize_source_type(payload.source_type)

    monitor_source = MonitorSource(**create_data)
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
        source_type = normalize_source_type(source_type)
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

    if "source_type" in update_data:
        update_data["source_type"] = normalize_source_type(update_data["source_type"])

    if "source_type" in update_data and update_data["source_type"] is not None:
        validate_source_type(update_data["source_type"])
    if "platform" in update_data and update_data["platform"] is not None:
        validate_platform(update_data["platform"])

    next_payload = MonitorSourceUpdate(
        source_type=update_data.get("source_type", monitor_source.source_type),
        platform=update_data.get("platform", monitor_source.platform),
        name=update_data.get("name", monitor_source.name),
        value=update_data.get("value", monitor_source.value),
        config=update_data.get("config", monitor_source.config),
        enabled=update_data.get("enabled", monitor_source.enabled),
        last_crawled_at=update_data.get("last_crawled_at", monitor_source.last_crawled_at),
    )
    validate_monitor_source_payload(next_payload)

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
