from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import List


class PlatformId(str, Enum):
    XHS = "xhs"
    DOUYIN = "douyin"
    ZHIHU = "zhihu"


@dataclass(frozen=True)
class PlatformMeta:
    id: PlatformId
    name_cn: str
    name_en: str
    enabled: bool
    status: str
    accent_color: str
    icon: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["id"] = self.id.value
        return payload


_PLATFORMS: List[PlatformMeta] = [
    PlatformMeta(PlatformId.XHS, "小红书", "XiaoHongShu", True, "enabled", "#ff2442", "xhs"),
    PlatformMeta(PlatformId.DOUYIN, "抖音", "Douyin", True, "enabled", "#111111", "douyin"),
    PlatformMeta(PlatformId.ZHIHU, "知乎", "Zhihu", True, "enabled", "#0066ff", "zhihu"),
]


def get_platforms() -> List[PlatformMeta]:
    return list(_PLATFORMS)


def get_platform(platform_id: PlatformId) -> PlatformMeta:
    for platform in _PLATFORMS:
        if platform.id == platform_id:
            return platform
    raise KeyError(platform_id)
