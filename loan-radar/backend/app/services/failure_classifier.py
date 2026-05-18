from __future__ import annotations

import re
from enum import Enum

from app.collectors.base import CollectionAuthError, CollectionNoDataError, CollectionRequestError


class FailureType(str, Enum):
    MEDIA_CRAWLER_UNREACHABLE = "media_crawler_unreachable"
    PLATFORM_NOT_SUPPORTED = "platform_not_supported"
    AUTH_REQUIRED = "auth_required"
    CAPTCHA_OR_RISK_CONTROL = "captcha_or_risk_control"
    TIMEOUT = "timeout"
    EMPTY_RESULT = "empty_result"
    PARSER_ERROR = "parser_error"
    UNKNOWN = "unknown"


FAILURE_TYPE_META: dict[FailureType, dict[str, str]] = {
    FailureType.MEDIA_CRAWLER_UNREACHABLE: {
        "label": "采集服务不可用",
        "description": "MediaCrawler API 服务未启动或无法连接",
        "suggestion": "请启动 MediaCrawler 服务，或切换为演示模式（设置 ENABLE_MOCK_COLLECTOR=true）",
    },
    FailureType.PLATFORM_NOT_SUPPORTED: {
        "label": "平台不支持",
        "description": "当前采集器不支持该平台",
        "suggestion": "请选择支持的平台（小红书、抖音、知乎），或等待后续版本开放更多平台",
    },
    FailureType.AUTH_REQUIRED: {
        "label": "登录态失效",
        "description": "Cookie 已过期或账号登录态失效",
        "suggestion": "请重新获取目标平台的 Cookie，更新监控源配置中的 cookies 字段",
    },
    FailureType.CAPTCHA_OR_RISK_CONTROL: {
        "label": "疑似风控拦截",
        "description": "目标平台可能触发了验证码或风控策略",
        "suggestion": "请稍后重试，或更换账号/Cookie 后重新采集",
    },
    FailureType.TIMEOUT: {
        "label": "采集超时",
        "description": "采集任务在规定时间内未完成",
        "suggestion": "请检查网络连接，减少采集数量，或稍后重试",
    },
    FailureType.EMPTY_RESULT: {
        "label": "采集无结果",
        "description": "采集完成但未获取到任何数据",
        "suggestion": "请检查关键词是否正确，或目标平台是否有相关内容",
    },
    FailureType.PARSER_ERROR: {
        "label": "数据解析失败",
        "description": "采集到数据但解析过程出错",
        "suggestion": "可能是平台页面结构变更，请联系管理员或稍后重试",
    },
    FailureType.UNKNOWN: {
        "label": "未知错误",
        "description": "发生了未预期的错误",
        "suggestion": "请查看详细错误信息，或联系管理员排查",
    },
}

_STRONG_RISK_CONTROL_PATTERNS = [
    "验证码",
    "captcha",
    "频繁",
    "too many",
    "rate limit",
    "429",
    "限制",
    "throttl",
    "当前账号存在异常",
    "请切换账号",
    "P2:request",
]

_WEAK_RISK_CONTROL_PATTERNS = [
    "风控",
    "risk control",
    "异常",
]

_UNREACHABLE_PATTERNS = [
    "服务不可用",
    "无法连接",
    "connection refused",
    "connecterror",
    "connectionerror",
    "服务无法连接",
    "connect_error",
    "unreachable",
]

_TIMEOUT_PATTERNS = [
    "超时",
    "timeout",
    "timed out",
    "timeoutexception",
]


def _matches_patterns(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(pattern.lower() in lower for pattern in patterns)


def classify_failure_type(error: Exception | str) -> FailureType:
    error_type = type(error).__name__ if isinstance(error, Exception) else ""
    error_msg = str(error)

    if isinstance(error, CollectionAuthError):
        if _matches_patterns(error_msg, _STRONG_RISK_CONTROL_PATTERNS):
            return FailureType.CAPTCHA_OR_RISK_CONTROL
        return FailureType.AUTH_REQUIRED

    if isinstance(error, CollectionNoDataError):
        return FailureType.EMPTY_RESULT

    if isinstance(error, ConnectionError):
        return FailureType.MEDIA_CRAWLER_UNREACHABLE

    if error_type in ("TimeoutError", "httpx.TimeoutException"):
        return FailureType.TIMEOUT

    if isinstance(error, ValueError):
        msg = error_msg.lower()
        if "不支持" in msg and "平台" in msg:
            return FailureType.PLATFORM_NOT_SUPPORTED
        if "不支持" in msg and "source_type" in msg:
            return FailureType.PLATFORM_NOT_SUPPORTED
        return FailureType.UNKNOWN

    if isinstance(error, CollectionRequestError):
        if _matches_patterns(error_msg, _STRONG_RISK_CONTROL_PATTERNS):
            return FailureType.CAPTCHA_OR_RISK_CONTROL
        if _matches_patterns(error_msg, _WEAK_RISK_CONTROL_PATTERNS):
            return FailureType.CAPTCHA_OR_RISK_CONTROL
        if _matches_patterns(error_msg, _UNREACHABLE_PATTERNS):
            return FailureType.MEDIA_CRAWLER_UNREACHABLE
        if _matches_patterns(error_msg, _TIMEOUT_PATTERNS):
            return FailureType.TIMEOUT
        return FailureType.UNKNOWN

    if _matches_patterns(error_msg, _UNREACHABLE_PATTERNS):
        return FailureType.MEDIA_CRAWLER_UNREACHABLE

    if _matches_patterns(error_msg, _TIMEOUT_PATTERNS):
        return FailureType.TIMEOUT

    if _matches_patterns(error_msg, _STRONG_RISK_CONTROL_PATTERNS):
        return FailureType.CAPTCHA_OR_RISK_CONTROL

    if _matches_patterns(error_msg, _WEAK_RISK_CONTROL_PATTERNS):
        return FailureType.CAPTCHA_OR_RISK_CONTROL

    if "解析" in error_msg.lower() or "parse" in error_msg.lower() or "json" in error_msg.lower():
        return FailureType.PARSER_ERROR

    return FailureType.UNKNOWN
