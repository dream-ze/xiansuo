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
    last_crawled_at: datetime | None = None


class MonitorSourceOut(MonitorSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
