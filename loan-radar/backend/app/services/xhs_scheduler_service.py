from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.xhs.creator_api_adapter import XhsCreatorApiAdapter
from app.adapters.xhs.creator_login_adapter import XhsCreatorLoginAdapter
from app.adapters.xhs.pc_login_adapter import XhsPcLoginAdapter
from app.core.database import SessionLocal
from app.core.security import decrypt_text
from app.core.time import shanghai_now
from app.models import (
    AccountCookieVersion,
    Notification,
    PlatformAccount,
    PublishAsset,
    PublishJob,
    Task,
    User,
)
from app.services.account_service import decode_cookie_text

logger = logging.getLogger(__name__)


def _cookies_to_string(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return stripped
    if stripped.startswith("{"):
        cookies = json.loads(stripped)
        return "; ".join(f"{key}={cookie_value}" for key, cookie_value in cookies.items())
    return stripped


def _latest_account_cookies(db: Session, account_id: int) -> str:
    cookie_version = db.scalars(
        select(AccountCookieVersion)
        .where(AccountCookieVersion.platform_account_id == account_id)
        .order_by(AccountCookieVersion.created_at.desc(), AccountCookieVersion.id.desc())
    ).first()
    if cookie_version is None:
        raise RuntimeError("Account has no cookies")
    return _cookies_to_string(decrypt_text(cookie_version.encrypted_cookies))


def _asset_upload_info(asset: PublishAsset) -> dict[str, Any]:
    try:
        payload = json.loads(asset.creator_upload_info or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Uploaded asset metadata is invalid") from exc
    if not payload.get("fileIds"):
        raise RuntimeError("Uploaded asset is missing Creator upload info")
    return payload


def _external_note_id(payload: dict[str, Any]) -> str:
    for key in ("note_id", "noteId", "id"):
        value = payload.get(key)
        if value:
            return str(value)
    data = payload.get("data")
    if isinstance(data, dict):
        return _external_note_id(data)
    return ""


def _load_publish_options(job: PublishJob) -> dict[str, Any]:
    try:
        options = json.loads(job.publish_options or "{}")
    except json.JSONDecodeError:
        return {}
    return options if isinstance(options, dict) else {}


def _clean_topics(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [topic.strip() for topic in value if isinstance(topic, str) and topic.strip()]


def _apply_publish_options(note_info: dict[str, Any], options: dict[str, Any]) -> None:
    topics = _clean_topics(options.get("topics"))
    if topics:
        note_info["topics"] = topics
    location = options.get("location")
    if isinstance(location, str) and location.strip():
        note_info["location"] = location.strip()
    if options.get("privacy_type") in (0, 1):
        note_info["type"] = options["privacy_type"]


def _run_one_due_publish_job(db: Session, current_user: User, job: PublishJob) -> tuple[bool, dict[str, Any]]:
    account = db.get(PlatformAccount, job.platform_account_id)
    if account is None or account.user_id != current_user.id:
        raise RuntimeError("Account not found")
    if account.platform != "xhs" or account.sub_type != "creator":
        raise RuntimeError("Creator account required")

    task = Task(
        user_id=current_user.id,
        platform=job.platform,
        task_type="creator_publish_scheduler",
        status="running",
        progress=20,
        payload={"publish_job_id": job.id, "platform_account_id": account.id, "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None},
    )
    db.add(task)
    job.status = "publishing"
    job.publish_error = ""
    db.commit()

    try:
        assets = db.scalars(
            select(PublishAsset).where(PublishAsset.publish_job_id == job.id).order_by(PublishAsset.id.asc())
        ).all()
        uploaded_assets = [asset for asset in assets if asset.upload_status == "uploaded"]
        if not uploaded_assets:
            raise RuntimeError("At least one uploaded image asset is required")

        note_info = {
            "title": job.title,
            "desc": job.body,
            "media_type": "image",
            "image_file_infos": [_asset_upload_info(asset) for asset in uploaded_assets],
            "type": 1,
            "postTime": None,
        }
        _apply_publish_options(note_info, _load_publish_options(job))

        cookies = _latest_account_cookies(db, account.id)
        payload = XhsCreatorApiAdapter(cookies).post_note(note_info)
        job.status = "published"
        job.external_note_id = _external_note_id(payload)
        job.publish_error = ""
        job.published_at = shanghai_now()
        task.status = "completed"
        task.progress = 100
        task.payload = {**(task.payload or {}), "external_note_id": job.external_note_id, "published_at": job.published_at.isoformat()}
        db.commit()
        return True, {"id": job.id, "status": job.status, "external_note_id": job.external_note_id}
    except Exception as exc:
        job.status = "failed"
        job.publish_error = str(exc)
        task.status = "failed"
        task.progress = 100
        task.payload = {**(task.payload or {}), "error": str(exc)}
        db.commit()
        return False, {"id": job.id, "status": job.status, "error": str(exc)}


def run_due_publish_jobs(
    *,
    db: Session,
    current_user: User,
    now: Optional[datetime],
    platform: str,
) -> dict[str, Any]:
    now = now or shanghai_now()
    due_jobs = db.scalars(
        select(PublishJob)
        .join(PlatformAccount, PublishJob.platform_account_id == PlatformAccount.id)
        .where(
            PlatformAccount.user_id == current_user.id,
            PublishJob.platform == platform,
            PublishJob.publish_mode == "scheduled",
            PublishJob.status == "pending",
            PublishJob.scheduled_at.is_not(None),
            PublishJob.scheduled_at <= now,
        )
        .order_by(PublishJob.scheduled_at.asc(), PublishJob.id.asc())
    ).all()

    items: list[dict[str, Any]] = []
    failed_count = 0
    for job in due_jobs:
        succeeded, item = _run_one_due_publish_job(db, current_user, job)
        items.append(item)
        if not succeeded:
            failed_count += 1
    return {"executed_count": len(items), "failed_count": failed_count, "items": items}


def run_due_publish_jobs_for_all_users(
    *,
    db: Session,
    now: Optional[datetime],
    platform: str,
) -> dict[str, Any]:
    now = now or shanghai_now()
    users = db.scalars(
        select(User)
        .join(PlatformAccount, PlatformAccount.user_id == User.id)
        .join(PublishJob, PublishJob.platform_account_id == PlatformAccount.id)
        .where(
            PublishJob.platform == platform,
            PublishJob.publish_mode == "scheduled",
            PublishJob.status == "pending",
            PublishJob.scheduled_at.is_not(None),
            PublishJob.scheduled_at <= now,
        )
        .distinct()
        .order_by(User.id.asc())
    ).all()

    items: list[dict[str, Any]] = []
    failed_count = 0
    for user in users:
        result = run_due_publish_jobs(db=db, current_user=user, now=now, platform=platform)
        items.extend(result["items"])
        failed_count += result["failed_count"]
    return {"executed_count": len(items), "failed_count": failed_count, "items": items}


def run_due_publish_jobs_once() -> dict[str, Any]:
    db = SessionLocal()
    try:
        return run_due_publish_jobs_for_all_users(db=db, now=None, platform="xhs")
    finally:
        db.close()


def _check_single_account(db: Session, account: PlatformAccount, now: datetime) -> str:
    cookie_version = db.scalars(
        select(AccountCookieVersion)
        .where(AccountCookieVersion.platform_account_id == account.id)
        .order_by(AccountCookieVersion.created_at.desc())
    ).first()
    if cookie_version is None:
        account.status = "expired"
        account.status_message = "No stored cookie version"
        account.updated_at = now
        return "expired"

    adapter = XhsCreatorLoginAdapter() if account.sub_type == "creator" else XhsPcLoginAdapter()
    try:
        cookies_text = decrypt_text(cookie_version.encrypted_cookies)
        adapter.get_user_info(decode_cookie_text(cookies_text))
        old_status = account.status
        account.status = "active"
        account.status_message = ""
        account.updated_at = now
        return old_status
    except Exception as exc:
        old_status = account.status
        account.status = "expired"
        account.status_message = str(exc)
        account.updated_at = now
        return old_status


def check_all_account_cookies_once() -> None:
    db = SessionLocal()
    try:
        now = shanghai_now()
        accounts = db.scalars(select(PlatformAccount).order_by(PlatformAccount.id.asc())).all()
        checked = 0
        newly_expired = 0
        for account in accounts:
            try:
                old_status = _check_single_account(db, account, now)
                checked += 1
                if account.status == "expired" and old_status != "expired":
                    newly_expired += 1
                    db.add(Notification(
                        user_id=account.user_id,
                        type="warning",
                        title="账号 Cookie 过期",
                        message=f"账号「{account.nickname or account.external_user_id or account.id}」({account.sub_type or 'pc'}) Cookie 已失效，请重新绑定。",
                        body=f"账号「{account.nickname or account.external_user_id or account.id}」({account.sub_type or 'pc'}) Cookie 已失效，请重新绑定。",
                        level="warning",
                    ))
            except Exception as exc:
                logger.warning("Cookie check failed for account %d: %s", account.id, exc)
        db.commit()
        logger.info("Cookie check completed: %d accounts checked, %d newly expired", checked, newly_expired)
    except Exception as exc:
        logger.error("check_all_account_cookies_once failed: %s", exc)
    finally:
        db.close()
