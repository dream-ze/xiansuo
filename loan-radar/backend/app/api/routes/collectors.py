"""采集器能力接口和配置校验"""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.collectors.config import CollectorConfig
from app.collectors.factory import CollectorFactory

router = APIRouter(prefix="/api/collectors", tags=["collectors"])


@router.get("")
def get_collectors() -> dict[str, Any]:
    """
    获取所有支持的采集器能力列表

    返回各采集器的名称、描述、状态、支持的 source_type、推荐配置等
    """
    collectors = CollectorFactory.get_supported_collectors()
    return {
        "collectors": collectors,
        "summary": {
            "ready": [name for name, info in collectors.items() if info["status"] == "ready"],
            "implementing": [name for name, info in collectors.items() if info["status"] == "implementing"],
            "planned": [name for name, info in collectors.items() if info["status"] == "planned"],
        },
    }


@router.post("/validate-config")
def validate_collector_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    校验采集器配置是否合法

    Args:
        config: 采集器配置字典，应包含 collector_type 等字段

    Returns:
        {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "config": CollectorConfig (已规范化)
        }
    """
    errors = []
    warnings = []

    try:
        config_obj = CollectorConfig.parse(config)
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Config parse error: {str(e)}"],
            "warnings": [],
            "config": None,
        }

    # 验证 collector_type
    is_valid, msg = config_obj.validate_collector_type()
    if not is_valid:
        errors.append(msg)

    # 针对采集器类型的具体校验
    is_valid, msg = config_obj.validate_for_collector_type()
    if not is_valid:
        errors.append(msg)

    # 检查实现状态
    collectors = CollectorFactory.get_supported_collectors()
    if config_obj.collector_type in collectors:
        status = collectors[config_obj.collector_type]["status"]
        if status == "implementing":
            warnings.append(
                f"{config_obj.collector_type} is still implementing, may not work properly"
            )
        elif status == "planned":
            errors.append(
                f"{config_obj.collector_type} is planned but not implemented yet"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config": config_obj.dict() if len(errors) == 0 else None,
    }


@router.get("/health")
def collector_health() -> dict[str, Any]:
    """采集器模块健康检查"""
    collectors = CollectorFactory.get_supported_collectors()
    ready_count = sum(1 for c in collectors.values() if c["status"] == "ready")
    return {
        "status": "ok",
        "ready_collectors": ready_count,
        "total_collectors": len(collectors),
    }
