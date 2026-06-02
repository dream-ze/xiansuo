from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeEntry, Note, Post
from app.rag.embedding import EmbeddingClient
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RagIndexer:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
    ) -> None:
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    def index_note(self, *, db: Session, note: Note, user_id: int) -> KnowledgeEntry | None:
        existing = db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.user_id == user_id,
                KnowledgeEntry.source_type == "material",
                KnowledgeEntry.source_id == note.id,
            )
        )
        if existing is not None:
            return existing

        content = f"{note.title or ''}\n{note.content or ''}".strip()
        if not content:
            return None

        return self._index_content(
            db=db,
            user_id=user_id,
            source_type="material",
            source_id=note.id,
            content=content,
            metadata={
                "platform": note.platform,
                "note_id": note.note_id,
                "author_name": note.author_name,
            },
        )

    def index_post(self, *, db: Session, post: Post, user_id: int) -> KnowledgeEntry | None:
        existing = db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.user_id == user_id,
                KnowledgeEntry.source_type == "material",
                KnowledgeEntry.source_id == post.id,
            )
        )
        if existing is not None:
            return existing

        content = f"{post.title or ''}\n{post.content or ''}".strip()
        if not content:
            return None

        return self._index_content(
            db=db,
            user_id=user_id,
            source_type="material",
            source_id=post.id,
            content=content,
            metadata={
                "platform": post.platform,
                "post_id": post.post_id,
                "author_name": post.author_name,
            },
        )

    def index_compliance_rule(self, *, db: Session, rule_id: int, rule_text: str, category: str, severity: str, user_id: int) -> KnowledgeEntry | None:
        existing = db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.user_id == user_id,
                KnowledgeEntry.source_type == "platform_rule",
                KnowledgeEntry.source_id == rule_id,
            )
        )
        if existing is not None:
            return existing

        return self._index_content(
            db=db,
            user_id=user_id,
            source_type="platform_rule",
            source_id=rule_id,
            content=rule_text,
            metadata={
                "category": category,
                "severity": severity,
            },
        )

    def index_quality_script(self, *, db: Session, script_text: str, lead_id: int | None, demand_type: str, user_id: int) -> KnowledgeEntry | None:
        return self._index_content(
            db=db,
            user_id=user_id,
            source_type="quality_script",
            source_id=lead_id,
            content=script_text,
            metadata={
                "demand_type": demand_type,
            },
        )

    def _index_content(
        self,
        *,
        db: Session,
        user_id: int,
        source_type: str,
        source_id: int | None,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeEntry | None:
        try:
            embedding = self._embedding_client.embed(content)
        except Exception as exc:
            logger.error("Failed to embed content for indexing: %s", exc)
            return None

        if not embedding:
            return None

        return self._vector_store.store(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            embedding=embedding,
            metadata=metadata,
        )

    def index_notes_batch(self, *, db: Session, user_id: int, limit: int = 100) -> dict[str, int]:
        notes = db.scalars(
            select(Note).where(Note.user_id == user_id).limit(limit)
        ).all()

        indexed = 0
        skipped = 0
        failed = 0

        for note in notes:
            try:
                result = self.index_note(db=db, note=note, user_id=user_id)
                if result is not None:
                    indexed += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.error("Failed to index note %d: %s", note.id, exc)
                failed += 1

        db.commit()
        return {"indexed": indexed, "skipped": skipped, "failed": failed}
