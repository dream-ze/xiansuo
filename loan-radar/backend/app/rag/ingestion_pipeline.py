from __future__ import annotations

import logging
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import SummaryExtractor, KeywordExtractor
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.rag.llama_index_config import build_embed_model

logger = logging.getLogger(__name__)


class LlamaIndexIngestionPipeline:
    def __init__(
        self,
        *,
        chroma_persist_dir: str = "./storage/chroma",
        embed_model=None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> None:
        self._chroma_persist_dir = chroma_persist_dir
        self._embed_model = embed_model
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._chroma_client: chromadb.HttpClient | chromadb.PersistentClient | None = None

    def _get_chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=self._chroma_persist_dir)
        return self._chroma_client

    def _get_collection(self, user_id: int):
        client = self._get_chroma_client()
        collection_name = f"user_{user_id}_knowledge"
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _build_splitter(self) -> SentenceSplitter:
        return SentenceSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separator="\n",
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^，。！？；]+[，。！？；]?",
        )

    def index_documents(
        self,
        *,
        documents: list[Document],
        user_id: int,
    ) -> dict[str, int]:
        if not documents:
            return {"indexed": 0, "skipped": 0, "failed": 0}

        collection = self._get_collection(user_id)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        splitter = self._build_splitter()

        pipeline = IngestionPipeline(
            transformations=[
                splitter,
                self._embed_model,
            ],
            vector_store=vector_store,
        )

        indexed = 0
        skipped = 0
        failed = 0

        for doc in documents:
            try:
                doc_id = doc.doc_id
                existing = collection.get(ids=[doc_id])
                if existing and existing["ids"]:
                    skipped += 1
                    continue

                nodes = splitter.get_nodes_from_documents([doc])
                if not nodes:
                    skipped += 1
                    continue

                index = VectorStoreIndex(
                    nodes=nodes,
                    storage_context=storage_context,
                    embed_model=self._embed_model,
                )
                indexed += 1

            except Exception as exc:
                logger.error("Failed to index document %s: %s", doc.doc_id, exc)
                failed += 1

        return {"indexed": indexed, "skipped": skipped, "failed": failed}

    def index_note(
        self,
        *,
        note_id: int,
        title: str,
        content: str,
        platform: str = "xhs",
        author_name: str = "",
        note_id_str: str = "",
        user_id: int,
    ) -> dict[str, Any]:
        full_content = f"{title}\n{content}".strip()
        if not full_content:
            return {"status": "skipped", "reason": "empty_content"}

        doc = Document(
            text=full_content,
            doc_id=f"note_{note_id}",
            metadata={
                "source_type": "material",
                "source_id": str(note_id),
                "platform": platform,
                "author_name": author_name,
                "note_id": note_id_str,
                "title": title,
            },
        )

        result = self.index_documents(documents=[doc], user_id=user_id)
        return {
            "status": "indexed" if result["indexed"] > 0 else "skipped",
            "detail": result,
        }

    def index_compliance_rule(
        self,
        *,
        rule_id: int,
        rule_text: str,
        category: str,
        severity: str,
        user_id: int,
    ) -> dict[str, Any]:
        if not rule_text.strip():
            return {"status": "skipped", "reason": "empty_content"}

        doc = Document(
            text=rule_text,
            doc_id=f"rule_{rule_id}",
            metadata={
                "source_type": "platform_rule",
                "source_id": str(rule_id),
                "category": category,
                "severity": severity,
            },
        )

        result = self.index_documents(documents=[doc], user_id=user_id)
        return {
            "status": "indexed" if result["indexed"] > 0 else "skipped",
            "detail": result,
        }

    def index_quality_script(
        self,
        *,
        script_text: str,
        lead_id: int | None,
        demand_type: str,
        user_id: int,
    ) -> dict[str, Any]:
        if not script_text.strip():
            return {"status": "skipped", "reason": "empty_content"}

        doc_id = f"script_{lead_id or 'manual'}_{hash(script_text) % 100000}"
        doc = Document(
            text=script_text,
            doc_id=doc_id,
            metadata={
                "source_type": "quality_script",
                "source_id": str(lead_id) if lead_id else "0",
                "demand_type": demand_type,
            },
        )

        result = self.index_documents(documents=[doc], user_id=user_id)
        return {
            "status": "indexed" if result["indexed"] > 0 else "skipped",
            "detail": result,
        }

    def delete_by_source(
        self,
        *,
        user_id: int,
        source_type: str,
        source_id: int,
    ) -> int:
        collection = self._get_collection(user_id)
        doc_id = f"{source_type}_{source_id}"

        try:
            existing = collection.get(ids=[doc_id])
            if existing and existing["ids"]:
                collection.delete(ids=[doc_id])
                return 1
        except Exception as exc:
            logger.error("Failed to delete document %s: %s", doc_id, exc)

        return 0

    def batch_index_notes(
        self,
        *,
        notes: list[dict[str, Any]],
        user_id: int,
    ) -> dict[str, int]:
        documents = []
        for note in notes:
            title = note.get("title", "")
            content = note.get("content", "")
            full_content = f"{title}\n{content}".strip()
            if not full_content:
                continue

            doc = Document(
                text=full_content,
                doc_id=f"note_{note['id']}",
                metadata={
                    "source_type": "material",
                    "source_id": str(note["id"]),
                    "platform": note.get("platform", "xhs"),
                    "author_name": note.get("author_name", ""),
                },
            )
            documents.append(doc)

        return self.index_documents(documents=documents, user_id=user_id)
