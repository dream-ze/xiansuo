from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    TRANSIENT = "transient"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    NO_DATA = "no_data"
    CONFIG = "config"
    NETWORK = "network"
    UNKNOWN = "unknown"


@dataclass
class RetryDecision:
    should_retry: bool
    category: ErrorCategory
    delay_seconds: float
    reason: str


TRANSIENT_EXCEPTIONS = {
    "ConnectionError": ErrorCategory.NETWORK,
    "TimeoutError": ErrorCategory.NETWORK,
    "ConnectionResetError": ErrorCategory.NETWORK,
    "ConnectionAbortedError": ErrorCategory.NETWORK,
    "OSError": ErrorCategory.NETWORK,
}

AUTH_EXCEPTIONS = {
    "CollectionAuthError": ErrorCategory.AUTH,
}

RATE_LIMIT_PATTERNS = ["rate limit", "too many", "429", "频繁", "限制", "throttl"]

NO_DATA_EXCEPTIONS = {
    "CollectionNoDataError": ErrorCategory.NO_DATA,
}

CONFIG_EXCEPTIONS = {
    "ValueError": ErrorCategory.CONFIG,
    "CollectionRequestError": ErrorCategory.CONFIG,
}

RETRY_DELAYS: dict[ErrorCategory, list[float]] = {
    ErrorCategory.NETWORK: [5, 15, 30],
    ErrorCategory.RATE_LIMIT: [30, 60, 120],
    ErrorCategory.TRANSIENT: [10, 30, 60],
    ErrorCategory.AUTH: [],
    ErrorCategory.NO_DATA: [],
    ErrorCategory.CONFIG: [],
    ErrorCategory.UNKNOWN: [10, 30, 60],
}

RETRYABLE_CATEGORIES = {
    ErrorCategory.NETWORK,
    ErrorCategory.RATE_LIMIT,
    ErrorCategory.TRANSIENT,
}


def classify_error(error: Exception) -> ErrorCategory:
    error_type = type(error).__name__

    if error_type in AUTH_EXCEPTIONS:
        return AUTH_EXCEPTIONS[error_type]

    if error_type in NO_DATA_EXCEPTIONS:
        return NO_DATA_EXCEPTIONS[error_type]

    if error_type in TRANSIENT_EXCEPTIONS:
        return TRANSIENT_EXCEPTIONS[error_type]

    error_msg = str(error).lower()
    for pattern in RATE_LIMIT_PATTERNS:
        if pattern in error_msg:
            return ErrorCategory.RATE_LIMIT

    if error_type in CONFIG_EXCEPTIONS:
        return CONFIG_EXCEPTIONS[error_type]

    return ErrorCategory.UNKNOWN


def should_retry(error: Exception, retry_count: int, max_retries: int = 3) -> RetryDecision:
    category = classify_error(error)
    delays = RETRY_DELAYS.get(category, [10, 30, 60])

    if category not in RETRYABLE_CATEGORIES:
        return RetryDecision(
            should_retry=False,
            category=category,
            delay_seconds=0,
            reason=f"error category '{category.value}' is not retryable",
        )

    if retry_count >= max_retries:
        return RetryDecision(
            should_retry=False,
            category=category,
            delay_seconds=0,
            reason=f"max retries ({max_retries}) exceeded",
        )

    delay_index = min(retry_count, len(delays) - 1)
    delay = delays[delay_index]

    return RetryDecision(
        should_retry=True,
        category=category,
        delay_seconds=delay,
        reason=f"retryable error (category={category.value}), attempt {retry_count + 1}/{max_retries}, delay={delay}s",
    )


def execute_with_retry(
    func,
    max_retries: int = 3,
    on_retry=None,
) -> tuple[bool, Exception | None]:
    last_error: Exception | None = None
    retry_count = 0

    while retry_count <= max_retries:
        try:
            func()
            return True, None
        except Exception as e:
            last_error = e
            decision = should_retry(e, retry_count, max_retries)

            logger.warning(
                "execution attempt %d failed: %s (category=%s, retry=%s)",
                retry_count + 1,
                str(e)[:200],
                decision.category.value,
                decision.should_retry,
            )

            if not decision.should_retry:
                break

            if on_retry:
                on_retry(retry_count, decision)

            logger.info("waiting %.1fs before retry...", decision.delay_seconds)
            time.sleep(decision.delay_seconds)
            retry_count += 1

    return False, last_error
