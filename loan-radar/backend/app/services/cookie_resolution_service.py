from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_text
from app.models import AccountCookieVersion, PlatformAccount

logger = logging.getLogger(__name__)


def _cookies_to_header_string(encrypted_cookies: str) -> str:
    cookies_text = decrypt_text(encrypted_cookies)
    stripped = cookies_text.strip()
    if not stripped:
        return ""
    if stripped.startswith("{"):
        try:
            cookies = json.loads(stripped)
            if isinstance(cookies, dict):
                return "; ".join(f"{key}={value}" for key, value in cookies.items())
        except json.JSONDecodeError:
            pass
    return stripped


def resolve_cookies_for_platform(
    db: Session,
    platform: str,
    user_id: int | None = None,
    sub_type: str | None = None,
) -> str:
    query = select(PlatformAccount).where(
        PlatformAccount.platform == platform,
        PlatformAccount.status == "active",
    )
    if user_id is not None:
        query = query.where(PlatformAccount.user_id == user_id)
    if sub_type is not None:
        query = query.where(PlatformAccount.sub_type == sub_type)

    accounts = db.scalars(query.order_by(PlatformAccount.updated_at.desc())).all()

    for account in accounts:
        cookie_version = db.scalars(
            select(AccountCookieVersion)
            .where(AccountCookieVersion.platform_account_id == account.id)
            .order_by(AccountCookieVersion.created_at.desc(), AccountCookieVersion.id.desc())
        ).first()
        if cookie_version is None:
            continue

        try:
            cookie_header = _cookies_to_header_string(cookie_version.encrypted_cookies)
            if cookie_header:
                logger.info(
                    "Resolved cookies from account %s (id=%d, sub_type=%s) for platform=%s",
                    account.nickname or account.external_user_id,
                    account.id,
                    account.sub_type,
                    platform,
                )
                return cookie_header
        except Exception:
            logger.warning("Failed to decrypt cookies for account %d", account.id, exc_info=True)

    return ""


def resolve_cookies_for_source(
    db: Session,
    source: Any,
) -> str:
    platform = getattr(source, "platform", "")
    config = getattr(source, "config", None) or {}

    if isinstance(config, dict) and config.get("cookies"):
        return config["cookies"]

    sub_type = None
    if isinstance(config, dict):
        sub_type = config.get("cookie_sub_type")

    return resolve_cookies_for_platform(db, platform, sub_type=sub_type)


def inject_cookies_into_config(
    db: Session,
    source: Any,
) -> dict:
    config = dict(getattr(source, "config", None) or {})
    platform = getattr(source, "platform", "")

    if config.get("cookies"):
        return config

    resolved = resolve_cookies_for_platform(db, platform)
    if resolved:
        config["cookies"] = resolved
        logger.info("Injected resolved cookies into config for source platform=%s", platform)

    return config


def check_and_notify_expired_cookies(db: Session) -> int:
    from datetime import datetime, timedelta, timezone

    from app.models.notification import Notification

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    accounts = db.scalars(
        select(PlatformAccount).where(
            PlatformAccount.status.in_(["expired", "cookie_invalid"]),
        )
    ).all()

    notified_count = 0
    for account in accounts:
        existing = db.scalar(
            select(Notification).where(
                Notification.source_type == "account_expired",
                Notification.source_id == account.id,
                Notification.created_at > cutoff,
            )
        )
        if existing is not None:
            continue

        from app.services.notification_service import _create as _notify
        _notify(
            db,
            user_id=account.user_id,
            title=f"账号 Cookie 过期: {account.nickname or account.external_user_id}",
            body=f"平台 {account.platform}，请重新登录或更新 Cookie",
            level="error",
            source_type="account_expired",
            source_id=account.id,
        )
        notified_count += 1

    if notified_count > 0:
        db.commit()
    return notified_count
