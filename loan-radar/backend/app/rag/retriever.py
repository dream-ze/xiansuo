from __future__ import annotations

import logging
from typing import Any

from app.rag.embedding import EmbeddingClient
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RagRetriever:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
    ) -> None:
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    def retrieve(
        self,
        *,
        query: str,
        user_id: int,
        top_k: int = 5,
        source_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        try:
            query_embedding = self._embedding_client.embed(query)
        except Exception as exc:
            logger.error("Failed to embed query: %s", exc)
            return []

        if not query_embedding:
            return []

        results = self._vector_store.search(
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=top_k,
            source_types=source_types,
        )

        if filters:
            filtered = []
            for r in results:
                metadata = r.get("metadata", {})
                match = True
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(r)
            results = filtered

        return results
