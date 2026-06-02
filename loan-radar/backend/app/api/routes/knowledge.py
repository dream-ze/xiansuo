from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.models import KnowledgeEntry, ModelConfig, Note, User
from app.rag.llama_index_config import build_embed_model, build_llm
from app.rag.ingestion_pipeline import LlamaIndexIngestionPipeline
from app.rag.query_engine import LlamaIndexQueryEngine
from app.schemas.common import paginated
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_CHROMA_PERSIST_DIR = "./storage/chroma"


class KnowledgeIndexRequest(BaseModel):
    source_type: str = Field(default="material", max_length=64)
    note_ids: list[int] = Field(default_factory=list, max_length=100)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    source_types: list[str] = Field(default_factory=list)


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    similarity_top_k: int = Field(default=5, ge=1, le=20)
    response_mode: str = Field(default="tree_summarize")


def _get_model_config(db: Session, current_user: User) -> tuple[ModelConfig, str]:
    config = db.scalars(
        select(ModelConfig).where(
            ModelConfig.user_id == current_user.id,
            ModelConfig.model_type == "text",
            ModelConfig.is_default.is_(True),
        )
    ).first()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先配置默认文本模型",
        )
    api_key = decrypt_text(config.encrypted_api_key) if config.encrypted_api_key else ""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key 未配置",
        )
    return config, api_key


def _build_ingestion_pipeline(
    model_config: ModelConfig,
    api_key: str,
) -> LlamaIndexIngestionPipeline:
    embed_model = build_embed_model(model_config=model_config, api_key=api_key)
    return LlamaIndexIngestionPipeline(
        chroma_persist_dir=_CHROMA_PERSIST_DIR,
        embed_model=embed_model,
        chunk_size=512,
        chunk_overlap=50,
    )


def _build_query_engine(
    model_config: ModelConfig,
    api_key: str,
) -> LlamaIndexQueryEngine:
    embed_model = build_embed_model(model_config=model_config, api_key=api_key)
    llm = build_llm(model_config=model_config, api_key=api_key)
    return LlamaIndexQueryEngine(
        chroma_persist_dir=_CHROMA_PERSIST_DIR,
        embed_model=embed_model,
        llm=llm,
        similarity_top_k=10,
        rerank_top_n=5,
        use_reranker=True,
    )


@router.get("/entries")
def list_knowledge_entries(
    source_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    statement = select(KnowledgeEntry).where(KnowledgeEntry.user_id == current_user.id)
    if source_type:
        statement = statement.where(KnowledgeEntry.source_type == source_type)

    entries = db.scalars(
        statement.order_by(KnowledgeEntry.created_at.desc(), KnowledgeEntry.id.desc())
    ).all()

    return paginated([
        {
            "id": e.id,
            "source_type": e.source_type,
            "source_id": e.source_id,
            "content": e.content[:200] + ("..." if len(e.content) > 200 else ""),
            "embedding_id": e.embedding_id,
            "metadata": e.entry_metadata,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ], page, page_size)


@router.get("/stats")
def get_knowledge_stats(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.user_id == current_user.id
    ).count()

    by_type = {}
    rows = db.query(
        KnowledgeEntry.source_type,
        func.count(KnowledgeEntry.id),
    ).filter(
        KnowledgeEntry.user_id == current_user.id,
    ).group_by(KnowledgeEntry.source_type).all()

    for source_type, count in rows:
        by_type[source_type] = count

    model_config, api_key = _get_model_config(db, current_user)
    query_engine = _build_query_engine(model_config, api_key)
    chroma_stats = query_engine.get_collection_stats(current_user.id)

    return success_response({
        "total": total,
        "by_type": by_type,
        "chroma": chroma_stats,
    })


@router.post("/index")
def index_knowledge(
    payload: KnowledgeIndexRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    model_config, api_key = _get_model_config(db, current_user)
    pipeline = _build_ingestion_pipeline(model_config, api_key)

    results = {"indexed": 0, "skipped": 0, "failed": 0}

    if payload.source_type == "material" and payload.note_ids:
        for note_id in payload.note_ids:
            note = db.get(Note, note_id)
            if note is None or note.user_id != current_user.id:
                results["skipped"] += 1
                continue
            try:
                result = pipeline.index_note(
                    note_id=note.id,
                    title=note.title or "",
                    content=note.content or "",
                    platform=note.platform or "xhs",
                    author_name=note.author_name or "",
                    note_id_str=note.note_id or "",
                    user_id=current_user.id,
                )
                if result["status"] == "indexed":
                    results["indexed"] += 1
                else:
                    results["skipped"] += 1
            except Exception:
                results["failed"] += 1

    return success_response(results)


@router.post("/index-all-notes")
def index_all_notes(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    model_config, api_key = _get_model_config(db, current_user)
    pipeline = _build_ingestion_pipeline(model_config, api_key)

    notes = db.scalars(
        select(Note).where(Note.user_id == current_user.id).limit(100)
    ).all()

    note_dicts = [
        {
            "id": n.id,
            "title": n.title or "",
            "content": n.content or "",
            "platform": n.platform or "xhs",
            "author_name": n.author_name or "",
        }
        for n in notes
    ]

    results = pipeline.batch_index_notes(notes=note_dicts, user_id=current_user.id)
    return success_response(results)


@router.post("/search")
def search_knowledge(
    payload: KnowledgeSearchRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    model_config, api_key = _get_model_config(db, current_user)
    query_engine = _build_query_engine(model_config, api_key)

    source_types = payload.source_types if payload.source_types else None
    results = query_engine.retrieve(
        query=payload.query,
        user_id=current_user.id,
        top_k=payload.top_k,
        source_types=source_types,
    )

    return success_response({"results": results, "count": len(results)})


@router.post("/query")
def query_knowledge(
    payload: KnowledgeQueryRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    model_config, api_key = _get_model_config(db, current_user)
    query_engine = _build_query_engine(model_config, api_key)

    result = query_engine.query_with_response(
        query=payload.query,
        user_id=current_user.id,
        response_mode=payload.response_mode,
        similarity_top_k=payload.similarity_top_k,
    )

    return success_response(result)


@router.delete("/entries/{entry_id}")
def delete_knowledge_entry(
    entry_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    entry = db.scalar(
        select(KnowledgeEntry).where(
            KnowledgeEntry.id == entry_id,
            KnowledgeEntry.user_id == current_user.id,
        )
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目未找到")

    try:
        model_config, api_key = _get_model_config(db, current_user)
        pipeline = _build_ingestion_pipeline(model_config, api_key)
        pipeline.delete_by_source(
            user_id=current_user.id,
            source_type=entry.source_type,
            source_id=entry.source_id or 0,
        )
    except Exception as exc:
        logger.warning("Failed to delete from Chroma: %s", exc)

    db.delete(entry)
    db.commit()
    return success_response({"id": entry_id, "status": "deleted"})
