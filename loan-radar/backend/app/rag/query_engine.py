from __future__ import annotations

import logging
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import KeywordNodePostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.rag.llama_index_config import build_embed_model, build_llm

logger = logging.getLogger(__name__)


class LlamaIndexQueryEngine:
    def __init__(
        self,
        *,
        chroma_persist_dir: str = "./storage/chroma",
        embed_model=None,
        llm=None,
        similarity_top_k: int = 10,
        rerank_top_n: int = 5,
        use_reranker: bool = False,
    ) -> None:
        self._chroma_persist_dir = chroma_persist_dir
        self._embed_model = embed_model
        self._llm = llm
        self._similarity_top_k = similarity_top_k
        self._rerank_top_n = rerank_top_n
        self._use_reranker = use_reranker
        self._chroma_client: chromadb.PersistentClient | None = None
        self._reranker = None

        if self._use_reranker:
            self._init_reranker()

    def _init_reranker(self) -> None:
        try:
            from llama_index.postprocessor.sentence_transformers import SentenceTransformerRerank

            self._reranker = SentenceTransformerRerank(
                model="cross-encoder/ms-marco-MiniLM-L-2-v2",
                top_n=self._rerank_top_n,
            )
            logger.info("Reranker initialized: cross-encoder/ms-marco-MiniLM-L-2-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed, reranker disabled")
            self._use_reranker = False
            self._reranker = None
        except Exception as exc:
            logger.warning("Failed to init reranker: %s", exc)
            self._use_reranker = False
            self._reranker = None

    def _get_chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=self._chroma_persist_dir)
        return self._chroma_client

    def _get_index(self, user_id: int) -> VectorStoreIndex | None:
        client = self._get_chroma_client()
        collection_name = f"user_{user_id}_knowledge"

        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            logger.warning("Collection %s not found for user %d", collection_name, user_id)
            return None

        if collection.count() == 0:
            return None

        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=self._embed_model,
        )
        return index

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

        index = self._get_index(user_id)
        if index is None:
            return []

        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=self._similarity_top_k,
        )

        nodes = retriever.retrieve(query)

        if self._use_reranker and self._reranker is not None:
            nodes = self._reranker.postprocess_nodes(nodes, query_str=query)

        results: list[dict[str, Any]] = []
        for node in nodes[:top_k]:
            metadata = node.node.metadata or {}
            source_type = metadata.get("source_type", "unknown")

            if source_types and source_type not in source_types:
                continue

            if filters:
                match = True
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            results.append({
                "id": metadata.get("source_id", ""),
                "source_type": source_type,
                "source_id": metadata.get("source_id", ""),
                "content": node.node.text,
                "metadata": metadata,
                "score": node.score if node.score is not None else 0.0,
            })

        return results

    def query_with_response(
        self,
        *,
        query: str,
        user_id: int,
        response_mode: str = "tree_summarize",
        similarity_top_k: int = 5,
    ) -> dict[str, Any]:
        index = self._get_index(user_id)
        if index is None:
            return {"response": "", "source_nodes": []}

        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=similarity_top_k,
        )

        node_postprocessors = []
        if self._use_reranker and self._reranker is not None:
            node_postprocessors.append(self._reranker)

        query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            llm=self._llm,
            response_mode=response_mode,
            node_postprocessors=node_postprocessors,
        )

        response = query_engine.query(query)

        source_nodes = []
        for source_node in response.source_nodes:
            metadata = source_node.node.metadata or {}
            source_nodes.append({
                "content": source_node.node.text,
                "score": source_node.score if source_node.score is not None else 0.0,
                "metadata": metadata,
            })

        return {
            "response": str(response),
            "source_nodes": source_nodes,
        }

    def get_collection_stats(self, user_id: int) -> dict[str, Any]:
        client = self._get_chroma_client()
        collection_name = f"user_{user_id}_knowledge"

        try:
            collection = client.get_collection(name=collection_name)
            count = collection.count()
            return {"total": count, "collection_name": collection_name}
        except Exception:
            return {"total": 0, "collection_name": collection_name}
