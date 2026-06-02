from __future__ import annotations

import logging
from typing import Any

from app.rag.query_engine import LlamaIndexQueryEngine
from app.workflow.context import NodeResult, WorkflowContext

logger = logging.getLogger(__name__)


class RagRetrieveNode:
    name = "rag_retrieve"

    def __init__(self, query_engine: LlamaIndexQueryEngine | None = None) -> None:
        self._query_engine = query_engine

    async def execute(self, context: WorkflowContext) -> NodeResult:
        if self._query_engine is None:
            return NodeResult(
                node_name=self.name,
                success=True,
                output={
                    "references": [],
                    "rules": [],
                    "top_scripts": [],
                    "rag_available": False,
                },
            )

        input_data = context.input_data
        query = input_data.get("text", "") or input_data.get("topic", "")
        demand_type = input_data.get("demand_type", "")
        user_id = context.user_id

        try:
            results = self._query_engine.retrieve(
                query=query,
                user_id=user_id,
                top_k=5,
                source_types=["material", "platform_rule", "quality_script"],
                filters={"demand_type": demand_type} if demand_type else {},
            )

            references = [r for r in results if r.get("source_type") == "material"]
            rules = [r for r in results if r.get("source_type") == "platform_rule"]
            top_scripts = [r for r in results if r.get("source_type") == "quality_script"]

            return NodeResult(
                node_name=self.name,
                success=True,
                output={
                    "references": references,
                    "rules": rules,
                    "top_scripts": top_scripts,
                    "rag_available": True,
                },
            )
        except Exception as exc:
            logger.error("RAG retrieval failed: %s", exc)
            return NodeResult(
                node_name=self.name,
                success=True,
                output={
                    "references": [],
                    "rules": [],
                    "top_scripts": [],
                    "rag_available": False,
                    "error": str(exc),
                },
            )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True
