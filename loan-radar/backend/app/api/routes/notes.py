from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.xhs.pc_api_adapter import XhsPcApiAdapter
from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.models import (
    AccountCookieVersion,
    Note,
    NoteAsset,
    NoteComment,
    PlatformAccount,
    Tag,
    User,
    note_tags,
)
from app.schemas.common import paginated

router = APIRouter(prefix="/api/notes", tags=["notes"])


class BatchSaveNotesRequest(BaseModel):
    account_id: int
    note_ids: list[str] = Field(min_length=1, max_length=100)
    fetch_comments: bool = False


class TagRequest(BaseModel):
    tag_ids: list[int] = Field(min_length=1)


class ExportRequest(BaseModel):
    note_ids: list[str] = Field(min_length=1, max_length=500)
    format: str = Field(pattern="^(json|csv)$", default="json")


def _serialize_note(note: Note, *, include_raw: bool = False) -> dict[str, Any]:
    result = {
        "id": note.id,
        "platform": note.platform,
        "note_id": note.note_id,
        "title": note.title,
        "content": note.content,
        "author_name": note.author_name,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }
    if include_raw:
        result["raw_json"] = note.raw_json
    return result


def _serialize_comment(comment: NoteComment) -> dict[str, Any]:
    return {
        "id": comment.id,
        "comment_id": comment.comment_id,
        "user_name": comment.user_name,
        "content": comment.content,
        "like_count": comment.like_count,
        "parent_comment_id": comment.parent_comment_id,
        "created_at_remote": comment.created_at_remote,
    }


def _get_owned_account(db: Session, current_user: User, account_id: int) -> PlatformAccount:
    account = db.get(PlatformAccount, account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _get_latest_account_cookies(db: Session, account: PlatformAccount) -> str:
    cookie_version = db.scalars(
        select(AccountCookieVersion)
        .where(AccountCookieVersion.platform_account_id == account.id)
        .order_by(AccountCookieVersion.created_at.desc())
    ).first()
    if cookie_version is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No cookies found for account")
    return decrypt_text(cookie_version.encrypted_cookies)


def _get_owned_note(db: Session, current_user: User, note_id: int) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.get("")
def list_notes(
    platform: Optional[str] = None,
    keyword: Optional[str] = None,
    tag_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Note).where(Note.user_id == current_user.id)
    if platform:
        statement = statement.where(Note.platform == platform)
    if keyword:
        statement = statement.where(Note.title.contains(keyword) | Note.content.contains(keyword))
    if tag_id:
        statement = statement.join(note_tags, Note.id == note_tags.c.note_id).where(note_tags.c.tag_id == tag_id)
    notes = db.scalars(statement.order_by(Note.created_at.desc(), Note.id.desc())).all()
    return paginated([_serialize_note(note) for note in notes], page, page_size)


@router.get("/{note_db_id}")
def get_note(
    note_db_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(db, current_user, note_db_id)
    result = _serialize_note(note, include_raw=True)
    assets = db.scalars(select(NoteAsset).where(NoteAsset.note_id == note.id).order_by(NoteAsset.sort_order)).all()
    result["assets"] = [
        {"id": a.id, "asset_type": a.asset_type, "url": a.url, "local_path": a.local_path, "sort_order": a.sort_order}
        for a in assets
    ]
    comments = db.scalars(select(NoteComment).where(NoteComment.note_id == note.id)).all()
    result["comments"] = [_serialize_comment(c) for c in comments]
    tags = db.scalars(select(Tag).join(note_tags, Tag.id == note_tags.c.tag_id).where(note_tags.c.note_id == note.id)).all()
    result["tags"] = [{"id": t.id, "name": t.name, "color": t.color} for t in tags]
    return result


@router.post("/batch-save")
def batch_save_notes(
    payload: BatchSaveNotesRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = _get_owned_account(db, current_user, payload.account_id)
    cookies_text = _get_latest_account_cookies(db, account)
    adapter = XhsPcApiAdapter(cookies_text)

    saved_count = 0
    for external_note_id in payload.note_ids:
        existing = db.scalar(
            select(Note).where(
                Note.user_id == current_user.id,
                Note.platform == account.platform,
                Note.note_id == external_note_id,
            )
        )
        if existing is not None:
            continue
        try:
            note_data = adapter.get_note_detail(external_note_id)
            if not note_data:
                continue
            note = Note(
                user_id=current_user.id,
                platform_account_id=account.id,
                platform=account.platform,
                note_id=external_note_id,
                title=note_data.get("title", ""),
                content=note_data.get("desc", note_data.get("content", "")),
                author_name=note_data.get("nickname", note_data.get("author_name", "")),
                raw_json=note_data,
            )
            db.add(note)
            db.flush()
            for idx, image_item in enumerate(note_data.get("image_list", [])):
                url = image_item.get("url_default") or image_item.get("url") or image_item.get("info_list", [{}])[-1].get("url", "")
                if url:
                    db.add(NoteAsset(note_id=note.id, asset_type="image", url=url, sort_order=idx))
            if note_data.get("video"):
                video_url = note_data["video"].get("media", {}).get("stream", [{}])[-1].get("master_url", "")
                if video_url:
                    db.add(NoteAsset(note_id=note.id, asset_type="video", url=video_url, sort_order=0))
            if payload.fetch_comments:
                try:
                    comments_data = adapter.get_note_comments(external_note_id)
                    for comment_item in comments_data:
                        db.add(
                            NoteComment(
                                note_id=note.id,
                                comment_id=str(comment_item.get("id", "")),
                                user_name=comment_item.get("nickname", comment_item.get("user_name", "")),
                                user_id=str(comment_item.get("user_id", "")),
                                content=comment_item.get("content", ""),
                                like_count=int(comment_item.get("like_count", 0) or 0),
                                parent_comment_id=str(comment_item.get("sub_comment_id", "")) if comment_item.get("sub_comment_id") else None,
                                raw_json=comment_item,
                            )
                        )
                except Exception:
                    pass
            saved_count += 1
        except Exception:
            continue

    db.commit()
    return {"saved_count": saved_count, "total_requested": len(payload.note_ids)}


@router.post("/{note_db_id}/tags")
def add_tags_to_note(
    note_db_id: int,
    payload: TagRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(db, current_user, note_db_id)
    for tag_id in payload.tag_ids:
        tag = db.get(Tag, tag_id)
        if tag is None or tag.user_id != current_user.id:
            continue
        existing = db.scalar(
            select(note_tags).where(note_tags.c.note_id == note.id, note_tags.c.tag_id == tag.id)
        )
        if existing is None:
            db.execute(note_tags.insert().values(note_id=note.id, tag_id=tag.id))
    db.commit()
    return {"status": "ok"}


@router.delete("/{note_db_id}/tags")
def remove_tags_from_note(
    note_db_id: int,
    payload: TagRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(db, current_user, note_db_id)
    for tag_id in payload.tag_ids:
        db.execute(note_tags.delete().where(note_tags.c.note_id == note.id, note_tags.c.tag_id == tag_id))
    db.commit()
    return {"status": "ok"}


@router.delete("/{note_db_id}")
def delete_note(
    note_db_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(db, current_user, note_db_id)
    db.execute(delete(NoteAsset).where(NoteAsset.note_id == note.id))
    db.execute(delete(NoteComment).where(NoteComment.note_id == note.id))
    db.execute(note_tags.delete().where(note_tags.c.note_id == note.id))
    db.delete(note)
    db.commit()
    return {"id": note_db_id, "status": "deleted"}


@router.post("/batch-delete")
def batch_delete_notes(
    payload: dict,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    note_ids = payload.get("note_ids", [])
    deleted = 0
    for note_db_id in note_ids:
        note = db.get(Note, note_db_id)
        if note is None or note.user_id != current_user.id:
            continue
        db.execute(delete(NoteAsset).where(NoteAsset.note_id == note.id))
        db.execute(delete(NoteComment).where(NoteComment.note_id == note.id))
        db.execute(note_tags.delete().where(note_tags.c.note_id == note.id))
        db.delete(note)
        deleted += 1
    db.commit()
    return {"deleted_count": deleted}
