from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.xhs.creator_login_adapter import XhsCreatorLoginAdapter
from app.adapters.xhs.pc_api_adapter import XhsPcApiAdapter
from app.adapters.xhs.pc_login_adapter import XhsPcLoginAdapter
from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.core.time import shanghai_now
from app.models import AccountCookieVersion, PlatformAccount, User
from app.schemas.common import paginated
from app.services.account_service import (
    cookie_header_from_text,
    decode_cookie_text,
    enrich_user_info_with_xhs_self_profile,
    serialize_account,
    upsert_platform_account_from_login,
)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class CookieImportRequest(BaseModel):
    platform: str = Field(pattern="^xhs$")
    sub_type: str = Field(pattern="^(pc|creator)$")
    cookie_string: str = Field(min_length=3)
    sync_creator: bool = False


def get_pc_account_adapter() -> XhsPcLoginAdapter:
    return XhsPcLoginAdapter()


def get_creator_account_adapter() -> XhsCreatorLoginAdapter:
    return XhsCreatorLoginAdapter()


class XhsSelfProfileAdapter:
    def get_self_profile(self, cookies_text: str):
        return XhsPcApiAdapter(cookies_text).get_self_info()


def get_xhs_self_profile_adapter() -> XhsSelfProfileAdapter:
    return XhsSelfProfileAdapter()


def _select_adapter(sub_type: str, pc_adapter: XhsPcLoginAdapter, creator_adapter: XhsCreatorLoginAdapter):
    return creator_adapter if sub_type == "creator" else pc_adapter


def _sync_creator_account_from_pc_cookie(
    *,
    db: Session,
    user_id: int,
    platform: str,
    cookie_string: str,
    creator_adapter: XhsCreatorLoginAdapter,
):
    try:
        creator_result = creator_adapter.exchange_from_user_cookies(decode_cookie_text(cookie_string))
        creator_cookies_text = json.dumps(creator_result["cookies"], ensure_ascii=False, separators=(",", ":"))
        creator_user_info = creator_adapter.get_user_info(creator_result["cookies"])
        upsert_platform_account_from_login(
            db=db,
            user_id=user_id,
            platform=platform,
            sub_type="creator",
            user_info=creator_user_info,
            cookies_text=creator_cookies_text,
        )
    except Exception:
        return None
    return True


@router.get("")
def get_accounts(
    platform: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    statement = select(PlatformAccount).where(PlatformAccount.user_id == current_user.id)
    if platform:
        statement = statement.where(PlatformAccount.platform == platform)
    accounts = db.scalars(statement.order_by(PlatformAccount.created_at.desc())).all()
    return paginated(
        [serialize_account(account) for account in accounts],
        page,
        page_size,
    )


@router.post("/import-cookie")
def import_cookie(
    payload: CookieImportRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
    pc_adapter: XhsPcLoginAdapter = Depends(get_pc_account_adapter),
    creator_adapter: XhsCreatorLoginAdapter = Depends(get_creator_account_adapter),
    self_profile_adapter: XhsSelfProfileAdapter = Depends(get_xhs_self_profile_adapter),
):
    adapter = _select_adapter(payload.sub_type, pc_adapter, creator_adapter)
    try:
        user_info = adapter.get_user_info(decode_cookie_text(payload.cookie_string))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cookie is invalid or expired") from exc

    if payload.sub_type == "pc":
        try:
            self_profile = self_profile_adapter.get_self_profile(cookie_header_from_text(payload.cookie_string))
            user_info = enrich_user_info_with_xhs_self_profile(user_info, self_profile)
        except Exception:
            pass

    account, action = upsert_platform_account_from_login(
        db=db,
        user_id=current_user.id,
        platform=payload.platform,
        sub_type=payload.sub_type,
        user_info=user_info,
        cookies_text=payload.cookie_string,
    )
    if payload.sub_type == "pc" and payload.sync_creator:
        _sync_creator_account_from_pc_cookie(
            db=db,
            user_id=current_user.id,
            platform=payload.platform,
            cookie_string=payload.cookie_string,
            creator_adapter=creator_adapter,
        )
    db.commit()
    db.refresh(account)
    return serialize_account(account, action)


@router.post("/{account_id}/check")
def check_account(
    account_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
    pc_adapter: XhsPcLoginAdapter = Depends(get_pc_account_adapter),
    creator_adapter: XhsCreatorLoginAdapter = Depends(get_creator_account_adapter),
    self_profile_adapter: XhsSelfProfileAdapter = Depends(get_xhs_self_profile_adapter),
):
    account = db.get(PlatformAccount, account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    cookie_version = db.scalars(
        select(AccountCookieVersion)
        .where(AccountCookieVersion.platform_account_id == account.id)
        .order_by(AccountCookieVersion.created_at.desc())
    ).first()
    if cookie_version is None:
        account.status = "expired"
        account.status_message = "No stored cookie version"
        db.commit()
        db.refresh(account)
        return serialize_account(account)

    adapter = _select_adapter(account.sub_type or "pc", pc_adapter, creator_adapter)
    try:
        cookies_text = decrypt_text(cookie_version.encrypted_cookies)
        user_info = adapter.get_user_info(decode_cookie_text(cookies_text))
        try:
            self_profile = self_profile_adapter.get_self_profile(cookie_header_from_text(cookies_text))
            user_info = enrich_user_info_with_xhs_self_profile(user_info, self_profile)
        except Exception:
            pass
        account.status = "active"
        account.status_message = ""
        account.nickname = user_info.get("nickname", account.nickname)
        account.avatar_url = user_info.get("avatar_url", account.avatar_url)
        account.external_user_id = user_info.get("external_user_id", account.external_user_id)
        account.profile_json = json.dumps(
            {"red_id": "", "description": "", "ip_location": "", "followers": None, "following": None, "likes": None},
            ensure_ascii=False,
        )
        account.updated_at = shanghai_now()
    except Exception as exc:
        account.status = "expired"
        account.status_message = str(exc)
        account.updated_at = shanghai_now()

    db.commit()
    db.refresh(account)
    return serialize_account(account)


@router.patch("/{account_id}")
def update_account(account_id: int):
    return {"id": account_id, "status": "updated"}


@router.delete("/{account_id}")
def delete_account(
    account_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = db.get(PlatformAccount, account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    for cookie_version in db.scalars(
        select(AccountCookieVersion).where(AccountCookieVersion.platform_account_id == account.id)
    ).all():
        db.delete(cookie_version)
    db.delete(account)
    db.commit()
    return {"id": account_id, "status": "deleted"}


@router.get("/cookie-status")
def get_cookie_status(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    from app.services.cookie_resolution_service import resolve_cookies_for_platform

    accounts = db.scalars(
        select(PlatformAccount)
        .where(PlatformAccount.user_id == current_user.id)
        .order_by(PlatformAccount.platform.asc(), PlatformAccount.sub_type.asc())
    ).all()

    platforms = sorted(set(a.platform for a in accounts))
    platform_status: list[dict[str, Any]] = []

    for platform in platforms:
        platform_accounts = [a for a in accounts if a.platform == platform]
        active_accounts = [a for a in platform_accounts if a.status == "active"]
        expired_accounts = [a for a in platform_accounts if a.status == "expired"]

        has_cookies = False
        if active_accounts:
            resolved = resolve_cookies_for_platform(db, platform, user_id=current_user.id)
            has_cookies = bool(resolved)

        platform_status.append({
            "platform": platform,
            "total_accounts": len(platform_accounts),
            "active_accounts": len(active_accounts),
            "expired_accounts": len(expired_accounts),
            "cookies_available": has_cookies,
            "crawl_ready": has_cookies,
        })

    return {"platforms": platform_status}
