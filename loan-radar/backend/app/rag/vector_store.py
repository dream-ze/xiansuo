from __future__ import annotations

import json
import logging
import math
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models import KnowledgeEntry

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, db: Session) -> None:
        self._db = db

    def store(
        self,
        *,
        user_id: int,
        source_type: str,
        content: str,
        embedding: list[float],
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeEntry:
        embedding_id = self._compute_embedding_id(embedding)

        entry = KnowledgeEntry(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            embedding_id=embedding_id,
            entry_metadata=metadata or {},
        )
        self._db.add(entry)
        self._db.flush()

        self._store_embedding_json(user_id, entry.id, embedding)

        return entry

    def search(
        self,
        *,
        query_embedding: list[float],
        user_id: int,
        top_k: int = 5,
        source_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        all_entries = self._db.scalars(
            select(KnowledgeEntry).where(KnowledgeEntry.user_id == user_id)
        ).all()

        if source_types:
            all_entries = [e for e in all_entries if e.source_type in source_types]

        if not all_entries:
            return []

        scored: list[tuple[float, KnowledgeEntry]] = []
        for entry in all_entries:
            embedding = self._load_embedding_json(user_id, entry.id)
            if not embedding:
                continue
            similarity = self._cosine_similarity(query_embedding, embedding)
            scored.append((similarity, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for similarity, entry in scored[:top_k]:
            results.append({
                "id": entry.id,
                "source_type": entry.source_type,
                "source_id": entry.source_id,
                "content": entry.content,
                "metadata": entry.entry_metadata or {},
                "score": similarity,
            })

        return results

    def delete_by_source(self, *, user_id: int, source_type: str, source_id: int) -> int:
        entries = self._db.scalars(
            select(KnowledgeEntry).where(
                KnowledgeEntry.user_id == user_id,
                KnowledgeEntry.source_type == source_type,
                KnowledgeEntry.source_id == source_id,
            )
        ).all()

        count = 0
        for entry in entries:
            self._delete_embedding_json(user_id, entry.id)
            self._db.delete(entry)
            count += 1

        self._db.flush()
        return count

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _compute_embedding_id(embedding: list[float]) -> str:
        import hashlib
        raw = json.dumps(embedding[:8]).encode()
        return hashlib.md5(raw).hexdigest()[:16]

    def _store_embedding_json(self, user_id: int, entry_id: int, embedding: list[float]) -> None:
        try:
            from pathlib import Path
            from app.core.config import get_settings
            settings = get_settings()
            embed_dir = Path(settings.storage_dir) / "embeddings" / str(user_id)
            embed_dir.mkdir(parents=True, exist_ok=True)
            embed_file = embed_dir / f"{entry_id}.json"
            embed_file.write_text(json.dumps(embedding), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to store embedding json for entry %d: %s", entry_id, exc)

    def _load_embedding_json(self, user_id: int, entry_id: int) -> list[float] | None:
        try:
            from pathlib import Path
            from app.core.config import get_settings
            settings = get_settings()
            embed_file = Path(settings.storage_dir) / "embeddings" / str(user_id) / f"{entry_id}.json"
            if embed_file.is_file():
                return json.loads(embed_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load embedding json for entry %d: %s", entry_id, exc)
        return None

    def _delete_embedding_json(self, user_id: int, entry_id: int) -> None:
        try:
            from pathlib import Path
            from app.core.config import get_settings
            settings = get_settings()
            embed_file = Path(settings.storage_dir) / "embeddings" / str(user_id) / f"{entry_id}.json"
            if embed_file.is_file():
                embed_file.unlink()
        except Exception as exc:
            logger.warning("Failed to delete embedding json for entry %d: %s", entry_id, exc)
