from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.models import Comment, Lead, Note, NoteComment, Post, User
from app.services.dedup_service import compute_content_hash
from app.services.lead_scoring_service import LeadScoringService

router = APIRouter(prefix="/api/content-pools", tags=["content-pools"])


class ConvertNoteToPostRequest(BaseModel):
    note_ids: list[int] = Field(min_length=1, max_length=100)
    source_id: int = 0
    source_type: str = "xhs_library"


class ConvertPostToNoteRequest(BaseModel):
    post_ids: list[int] = Field(min_length=1, max_length=100)
    platform_account_id: int | None = None


class ConvertResult(BaseModel):
    converted_count: int
    skipped_count: int
    failed_count: int
    details: list[dict[str, Any]]


def _extract_interact_info(note: Note) -> dict[str, int]:
    raw = note.raw_json or {}
    interaction = raw.get("interact_info") if isinstance(raw.get("interact_info"), dict) else {}
    merged = {**raw, **interaction}

    def _as_int(value: Any) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if cleaned.isdigit():
                return int(cleaned)
        return 0

    def _first_metric(keys: tuple[str, ...]) -> int:
        for key in keys:
            if key in merged:
                return _as_int(merged.get(key))
        return 0

    return {
        "likes": _first_metric(("likes", "liked_count", "like_count", "likedCount")),
        "collects": _first_metric(("collects", "collected_count", "collect_count", "collectedCount")),
        "comments": _first_metric(("comments", "comment_count", "commentCount")),
        "shares": _first_metric(("shares", "share_count", "shareCount")),
    }


@router.post("/notes-to-posts", response_model=ConvertResult)
def convert_notes_to_posts(
    payload: ConvertNoteToPostRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    scoring_service = LeadScoringService()
    converted = 0
    skipped = 0
    failed = 0
    details: list[dict[str, Any]] = []

    for note_db_id in payload.note_ids:
        note = db.get(Note, note_db_id)
        if note is None or note.user_id != current_user.id:
            skipped += 1
            details.append({"note_id": note_db_id, "status": "skipped", "reason": "not found"})
            continue

        existing = db.scalar(
            select(Post).where(
                Post.platform == note.platform,
                Post.post_id == note.note_id,
            )
        )
        if existing is not None:
            skipped += 1
            details.append({"note_id": note_db_id, "status": "skipped", "reason": "post already exists", "post_id": existing.id})
            continue

        try:
            metrics = _extract_interact_info(note)
            content_hash = compute_content_hash(note.content)

            post = Post(
                platform=note.platform,
                source_id=payload.source_id,
                source_type=payload.source_type,
                post_id=note.note_id,
                content_hash=content_hash,
                title=note.title,
                content=note.content,
                author_name=note.author_name,
                like_count=metrics["likes"],
                comment_count=metrics["comments"],
                collect_count=metrics["collects"],
                is_hot=metrics["likes"] + metrics["collects"] + metrics["comments"] > 1000,
                raw_data=note.raw_json,
            )
            db.add(post)
            db.flush()

            note_comments = db.scalars(
                select(NoteComment).where(NoteComment.note_id == note.id)
            ).all()

            lead_count = 0
            for nc in note_comments:
                existing_comment = db.scalar(
                    select(Comment).where(
                        Comment.platform == note.platform,
                        Comment.comment_id == nc.comment_id,
                    )
                )
                if existing_comment is not None:
                    continue

                comment_hash = compute_content_hash(nc.content)
                scoring_result = scoring_service.score(nc.content or "")

                comment = Comment(
                    platform=note.platform,
                    post_id=note.note_id,
                    comment_id=nc.comment_id,
                    content_hash=comment_hash,
                    user_name=nc.user_name,
                    content=nc.content,
                    like_count=nc.like_count,
                    is_suspected_demand=scoring_result.is_suspected_demand,
                    demand_type=scoring_result.demand_type,
                    risk_level=scoring_result.risk_level,
                    raw_data=nc.raw_json,
                )
                db.add(comment)
                db.flush()

                if scoring_result.is_suspected_demand:
                    lead_content_hash = compute_content_hash(nc.content)
                    lead = Lead(
                        platform=note.platform,
                        source_id=payload.source_id,
                        source_type=payload.source_type,
                        source_post_id=post.id,
                        source_comment_id=comment.id,
                        user_name=nc.user_name,
                        content_hash=lead_content_hash,
                        content=nc.content,
                        lead_level=scoring_result.lead_level,
                        lead_score=scoring_result.lead_score,
                        demand_type=scoring_result.demand_type,
                        risk_level=scoring_result.risk_level,
                        evidence=scoring_result.evidence,
                        reason=scoring_result.reason,
                        follow_up_script=scoring_result.follow_up_script,
                        status="new",
                        is_duplicate=False,
                    )
                    db.add(lead)
                    lead_count += 1

            converted += 1
            details.append({
                "note_id": note_db_id,
                "status": "converted",
                "post_id": post.id,
                "comments_converted": len(note_comments),
                "leads_created": lead_count,
            })
        except Exception as exc:
            failed += 1
            details.append({"note_id": note_db_id, "status": "failed", "reason": str(exc)[:200]})

    db.commit()
    return ConvertResult(converted_count=converted, skipped_count=skipped, failed_count=failed, details=details)


class CheckSavedRequest(BaseModel):
    post_ids: list[int] = Field(min_length=1, max_length=200)


class CheckSavedResult(BaseModel):
    saved_post_ids: list[int]


@router.post("/check-saved", response_model=CheckSavedResult)
def check_posts_saved(
    payload: CheckSavedRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    posts = db.query(Post).filter(Post.id.in_(payload.post_ids)).all()
    platform_note_ids = [p.post_id for p in posts]
    if not platform_note_ids:
        return CheckSavedResult(saved_post_ids=[])

    saved_note_ids = db.execute(
        select(Note.note_id).where(
            Note.user_id == current_user.id,
            Note.note_id.in_(platform_note_ids),
        )
    ).scalars().all()

    saved_set = set(saved_note_ids)
    saved_post_db_ids = [p.id for p in posts if p.post_id in saved_set]
    return CheckSavedResult(saved_post_ids=saved_post_db_ids)


@router.post("/posts-to-notes", response_model=ConvertResult)
def convert_posts_to_notes(
    payload: ConvertPostToNoteRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    converted = 0
    skipped = 0
    failed = 0
    details: list[dict[str, Any]] = []

    for post_db_id in payload.post_ids:
        post = db.get(Post, post_db_id)
        if post is None:
            skipped += 1
            details.append({"post_id": post_db_id, "status": "skipped", "reason": "not found"})
            continue

        existing = db.scalar(
            select(Note).where(
                Note.user_id == current_user.id,
                Note.platform == post.platform,
                Note.note_id == post.post_id,
            )
        )
        if existing is not None:
            skipped += 1
            details.append({"post_id": post_db_id, "status": "skipped", "reason": "note already exists", "note_id": existing.id})
            continue

        try:
            raw_json = post.raw_data if isinstance(post.raw_data, dict) else {}
            if raw_json:
                interact_info = raw_json.get("interact_info", {})
                if isinstance(interact_info, dict):
                    raw_json.setdefault("interact_info", interact_info)
            else:
                raw_json = {
                    "liked_count": post.like_count,
                    "collected_count": post.collect_count,
                    "comment_count": post.comment_count,
                }

            note = Note(
                user_id=current_user.id,
                platform_account_id=payload.platform_account_id or None,
                platform=post.platform,
                note_id=post.post_id,
                title=post.title or "",
                content=post.content or "",
                author_name=post.author_name or "",
                raw_json=raw_json,
            )
            db.add(note)
            db.flush()

            post_comments = db.scalars(
                select(Comment).where(
                    Comment.platform == post.platform,
                    Comment.post_id == post.post_id,
                )
            ).all()

            comments_converted = 0
            for comment in post_comments:
                existing_nc = db.scalar(
                    select(NoteComment).where(
                        NoteComment.note_id == note.id,
                        NoteComment.comment_id == comment.comment_id,
                    )
                )
                if existing_nc is not None:
                    continue

                nc = NoteComment(
                    note_id=note.id,
                    comment_id=comment.comment_id,
                    user_name=comment.user_name or "",
                    content=comment.content or "",
                    like_count=comment.like_count,
                    raw_json=comment.raw_data if isinstance(comment.raw_data, dict) else None,
                )
                db.add(nc)
                comments_converted += 1

            converted += 1
            details.append({
                "post_id": post_db_id,
                "status": "converted",
                "note_id": note.id,
                "comments_converted": comments_converted,
            })
        except Exception as exc:
            failed += 1
            details.append({"post_id": post_db_id, "status": "failed", "reason": str(exc)[:200]})

    db.commit()
    return ConvertResult(converted_count=converted, skipped_count=skipped, failed_count=failed, details=details)
