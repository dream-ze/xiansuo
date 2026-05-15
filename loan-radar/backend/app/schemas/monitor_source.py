from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class MonitorSourceBase(BaseModel):
    source_type: str
    platform: str
    name: str
    value: str
    config: Any | None = None
    enabled: bool = True
    schedule_enabled: bool = False
    schedule_cron: str | None = None
    last_scheduled_at: datetime | None = None
    last_crawled_at: datetime | None = None


class MonitorSourceCreate(MonitorSourceBase):
    pass


class MonitorSourceUpdate(BaseModel):
    source_type: str | None = None
    platform: str | None = None
    name: str | None = None
    value: str | None = None
    config: Any | None = None
    enabled: bool | None = None
    schedule_enabled: bool | None = None
    schedule_cron: str | None = None
    last_scheduled_at: datetime | None = None
    last_crawled_at: datetime | None = None


class MonitorSourceOut(MonitorSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
