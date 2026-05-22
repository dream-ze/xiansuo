from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.core.time import shanghai_now
from app.models import AiDraft, AutoTask, ModelConfig, Note, Post, PublishJob, User
from app.schemas.common import paginated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/xhs/auto-ops", tags=["xhs-auto-ops"])


class AutoTaskCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    keywords: list[str] = Field(min_length=1, max_length=50)
    pc_account_id: Optional[int] = None
    creator_account_id: Optional[int] = None
    ai_instruction: str = ""
    schedule_type: str = "manual"
    schedule_time: str = ""
    schedule_days: str = ""
    schedule_interval_hours: int = 0


class AutoTaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    keywords: Optional[list[str]] = Field(default=None, min_length=1, max_length=50)
    ai_instruction: Optional[str] = None
    status: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_days: Optional[str] = None
    schedule_interval_hours: Optional[int] = None


def _serialize_task(task: AutoTask) -> dict:
    config = json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
    return {
        "id": task.id,
        "user_id": task.user_id,
        "name": task.name,
        "keywords": config.get("keywords", []),
        "pc_account_id": config.get("pc_account_id"),
        "creator_account_id": config.get("creator_account_id"),
        "ai_instruction": config.get("ai_instruction", ""),
        "status": task.status,
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
        "total_published": config.get("total_published", 0),
        "created_at": task.created_at.isoformat(),
        "schedule_type": config.get("schedule_type", "manual"),
        "schedule_time": config.get("schedule_time", ""),
        "schedule_days": config.get("schedule_days", ""),
        "schedule_interval_hours": config.get("schedule_interval_hours", 0),
    }


def _find_source_note(db: Session, user_id: int, keywords: list[str]) -> Note | None:
    for kw in keywords[:3]:
        pattern = f"%{kw}%"
        note = db.scalars(
            select(Note)
            .where(
                (Note.user_id == user_id) | (Note.user_id.is_(None)),
                Note.title.ilike(pattern),
            )
            .order_by(Note.created_at.desc())
            .limit(1)
        ).first()
        if note:
            return note
        note = db.scalars(
            select(Note)
            .where(
                (Note.user_id == user_id) | (Note.user_id.is_(None)),
                Note.content.ilike(pattern),
            )
            .order_by(Note.created_at.desc())
            .limit(1)
        ).first()
        if note:
            return note
    return db.scalars(
        select(Note)
        .where((Note.user_id == user_id) | (Note.user_id.is_(None)))
        .order_by(Note.created_at.desc())
        .limit(1)
    ).first()


def _find_source_post(db: Session, keywords: list[str]) -> Post | None:
    for kw in keywords[:3]:
        pattern = f"%{kw}%"
        post = db.scalars(
            select(Post)
            .where(Post.title.ilike(pattern))
            .order_by(Post.created_at.desc())
            .limit(1)
        ).first()
        if post:
            return post
        post = db.scalars(
            select(Post)
            .where(Post.content.ilike(pattern))
            .order_by(Post.created_at.desc())
            .limit(1)
        ).first()
        if post:
            return post
    return db.scalars(
        select(Post).order_by(Post.created_at.desc()).limit(1)
    ).first()


def _get_text_model_and_key(db: Session, user_id: int) -> tuple[ModelConfig | None, str]:
    model_config = db.scalars(
        select(ModelConfig).where(
            ModelConfig.user_id == user_id,
            ModelConfig.model_type == "text",
            ModelConfig.is_default.is_(True),
        )
    ).first()
    if model_config is None:
        return None, ""
    api_key = decrypt_text(model_config.encrypted_api_key) if model_config.encrypted_api_key else ""
    return model_config, api_key


def _generate_draft_content(
    db: Session,
    user_id: int,
    keywords: list[str],
    source_note: Note | None,
    ai_instruction: str,
) -> AiDraft:
    model_config, api_key = _get_text_model_and_key(db, user_id)

    source_title = source_note.title if source_note else ""
    source_body = source_note.content if source_note else ""
    keyword_text = "、".join(keywords[:5])

    if model_config and api_key and model_config.base_url:
        from app.services.ai_service import OpenAICompatibleTextClient
        client = OpenAICompatibleTextClient()
        try:
            result = client.generate_note(
                model_config=model_config,
                api_key=api_key,
                topic=f"助贷行业选题：{keyword_text}",
                reference=f"参考标题：{source_title}\n参考正文：{source_body[:800]}" if source_title or source_body else "",
                instruction=ai_instruction or "生成一篇面向有贷款需求的用户的小红书种草笔记，自然、有信息密度，避免硬广",
            )
            draft_title = result.get("title", f"助贷选题：{keyword_text}")
            draft_body = result.get("body", "")
        except Exception as exc:
            logger.warning("AI generation failed for auto-ops, falling back to template: %s", exc)
            draft_title = f"助贷选题：{keyword_text}"
            draft_body = _build_template_body(keyword_text, source_title, source_body)
    else:
        draft_title = f"助贷选题：{keyword_text}"
        draft_body = _build_template_body(keyword_text, source_title, source_body)

    draft = AiDraft(
        user_id=user_id,
        platform="xhs",
        title=draft_title,
        body=draft_body,
        content=draft_body,
        source_note_id=source_note.id if source_note else None,
        intent="publish",
        status="draft",
    )
    db.add(draft)
    db.flush()
    return draft


def _build_template_body(keyword_text: str, source_title: str, source_body: str) -> str:
    lines = [
        f"📌 选题方向：{keyword_text}",
        "",
        "💡 很多朋友在贷款方面有疑问，今天整理了一些实用信息分享给大家：",
        "",
        "1️⃣ 了解自己的征信状况，避免盲目申请",
        "2️⃣ 选择正规渠道，远离高息陷阱",
        "3️⃣ 根据实际需求选择贷款产品",
        "",
    ]
    if source_title:
        lines.append(f"📝 参考内容：{source_title}")
    if source_body:
        lines.append(source_body[:300])
        lines.append("")
    lines.append("#助贷 #贷款 #征信 #金融知识")
    return "\n".join(lines)


def _create_publish_job(db: Session, user_id: int, draft: AiDraft, creator_account_id: int | None) -> PublishJob | None:
    if not creator_account_id:
        return None
    job = PublishJob(
        user_id=user_id,
        platform_account_id=creator_account_id,
        source_draft_id=draft.id,
        platform="xhs",
        title=draft.title,
        body=draft.body or draft.content or "",
        publish_mode="immediate",
        status="pending",
    )
    db.add(job)
    db.flush()
    return job


@router.get("/tasks")
def list_auto_tasks(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    tasks = db.scalars(
        select(AutoTask)
        .where(AutoTask.user_id == current_user.id)
        .order_by(AutoTask.created_at.desc())
    ).all()
    return paginated([_serialize_task(t) for t in tasks], page, page_size)


@router.post("/tasks")
def create_auto_task(
    payload: AutoTaskCreateRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    config = {
        "keywords": payload.keywords,
        "pc_account_id": payload.pc_account_id,
        "creator_account_id": payload.creator_account_id,
        "ai_instruction": payload.ai_instruction,
        "schedule_type": payload.schedule_type,
        "schedule_time": payload.schedule_time,
        "schedule_days": payload.schedule_days,
        "schedule_interval_hours": payload.schedule_interval_hours,
        "total_published": 0,
    }
    task = AutoTask(
        user_id=current_user.id,
        name=payload.name,
        task_type="auto_publish",
        config=json.dumps(config, ensure_ascii=False),
        status="active",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.patch("/tasks/{task_id}")
def update_auto_task(
    task_id: int,
    payload: AutoTaskUpdateRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    task = db.get(AutoTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    config = json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
    if payload.name is not None:
        task.name = payload.name
    if payload.keywords is not None:
        config["keywords"] = payload.keywords
    if payload.ai_instruction is not None:
        config["ai_instruction"] = payload.ai_instruction
    if payload.status is not None:
        task.status = payload.status
    if payload.schedule_type is not None:
        config["schedule_type"] = payload.schedule_type
    if payload.schedule_time is not None:
        config["schedule_time"] = payload.schedule_time
    if payload.schedule_days is not None:
        config["schedule_days"] = payload.schedule_days
    if payload.schedule_interval_hours is not None:
        config["schedule_interval_hours"] = payload.schedule_interval_hours
    task.config = json.dumps(config, ensure_ascii=False)
    task.updated_at = shanghai_now()
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.delete("/tasks/{task_id}")
def delete_auto_task(
    task_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    task = db.get(AutoTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"id": task_id, "status": "deleted"}


@router.post("/tasks/{task_id}/run")
def run_auto_task(
    task_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    task = db.get(AutoTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    config = json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
    keywords = config.get("keywords", [])
    ai_instruction = config.get("ai_instruction", "")
    creator_account_id = config.get("creator_account_id")

    source_note = _find_source_note(db, current_user.id, keywords)
    if source_note is None:
        source_post = _find_source_post(db, keywords)
        if source_post is not None:
            from app.models import Note
            source_note = db.scalars(
                select(Note).where(
                    Note.platform == source_post.platform,
                    Note.note_id == source_post.post_id,
                ).limit(1)
            ).first()

    keyword_text = "、".join(keywords[:3]) if keywords else "助贷"

    draft = _generate_draft_content(db, current_user.id, keywords, source_note, ai_instruction)

    publish_job = _create_publish_job(db, current_user.id, draft, creator_account_id)

    config["total_published"] = config.get("total_published", 0)
    task.config = json.dumps(config, ensure_ascii=False)
    task.last_run_at = shanghai_now()
    db.commit()
    db.refresh(task)

    return {
        "auto_task": _serialize_task(task),
        "keyword": keyword_text,
        "source_note": {
            "id": source_note.id,
            "title": source_note.title,
            "content": (source_note.content or "")[:200],
        } if source_note else {"id": None, "title": "", "content": ""},
        "draft": {
            "id": draft.id,
            "title": draft.title,
            "body": (draft.body or "")[:300],
            "status": draft.status,
        },
        "publish_job": {
            "id": publish_job.id,
            "status": publish_job.status,
            "title": publish_job.title,
        } if publish_job else {"id": None, "status": "skipped", "title": ""},
    }


@router.post("/run-due")
def run_due_tasks(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    active_tasks = db.scalars(
        select(AutoTask).where(
            AutoTask.user_id == current_user.id,
            AutoTask.status == "active",
        )
    ).all()

    results = []
    errors = []
    executed_count = 0
    failed_count = 0

    for task in active_tasks:
        config = json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
        schedule_type = config.get("schedule_type", "manual")
        if schedule_type == "manual":
            continue

        try:
            keywords = config.get("keywords", [])
            ai_instruction = config.get("ai_instruction", "")
            creator_account_id = config.get("creator_account_id")

            source_note = _find_source_note(db, current_user.id, keywords)
            draft = _generate_draft_content(db, current_user.id, keywords, source_note, ai_instruction)
            publish_job = _create_publish_job(db, current_user.id, draft, creator_account_id)

            config["total_published"] = config.get("total_published", 0)
            task.config = json.dumps(config, ensure_ascii=False)
            task.last_run_at = shanghai_now()
            db.commit()

            results.append({
                "auto_task_id": task.id,
                "draft_id": draft.id,
                "publish_job_id": publish_job.id if publish_job else None,
            })
            executed_count += 1
        except Exception as exc:
            logger.exception("auto-ops run-due task %d failed", task.id)
            errors.append({"auto_task_id": task.id, "error": str(exc)})
            failed_count += 1

    return {
        "executed_count": executed_count,
        "failed_count": failed_count,
        "results": results,
        "errors": errors,
    }
