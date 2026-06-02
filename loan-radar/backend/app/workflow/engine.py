from __future__ import annotations

import logging
import time
from typing import Any, Protocol, runtime_checkable

from app.workflow.context import NodeResult, WorkflowContext, WorkflowState

logger = logging.getLogger(__name__)


@runtime_checkable
class WorkflowNode(Protocol):
    name: str

    async def execute(self, context: WorkflowContext) -> NodeResult: ...

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True


class WorkflowEngine:
    def __init__(self, nodes: list[WorkflowNode], *, name: str = "") -> None:
        self.nodes = nodes
        self.name = name or "unnamed"
        self._node_map: dict[str, WorkflowNode] = {n.name: n for n in nodes}

    async def run(self, context: WorkflowContext) -> WorkflowContext:
        if context.state == WorkflowState.PAUSED and context.paused_at_node:
            start_index = self._find_node_index(context.paused_at_node)
            if start_index < 0:
                raise ValueError(f"Paused at unknown node: {context.paused_at_node}")
            context.paused_at_node = None
            context.transition_to(WorkflowState.RUNNING)
        elif context.state == WorkflowState.FAILED and context.error_node:
            start_index = self._find_node_index(context.error_node)
            if start_index < 0:
                raise ValueError(f"Failed at unknown node: {context.error_node}")
            context.error_node = None
            context.error_message = None
            context.retry_count += 1
            context.transition_to(WorkflowState.RUNNING)
        else:
            start_index = 0
            context.transition_to(WorkflowState.RUNNING)

        for i in range(start_index, len(self.nodes)):
            node = self.nodes[i]
            context.current_node = node.name

            if hasattr(node, 'should_proceed') and not node.should_proceed(context):
                logger.info(
                    "Workflow %s skipped node %s (should_proceed=False)",
                    context.workflow_id,
                    node.name,
                )
                context.set_node_result(NodeResult(
                    node_name=node.name,
                    success=True,
                    output={"skipped": True},
                ))
                continue

            logger.info(
                "Workflow %s executing node %s (%d/%d)",
                context.workflow_id,
                node.name,
                i + 1,
                len(self.nodes),
            )

            start_time = time.monotonic()
            try:
                result = await node.execute(context)
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                result.duration_ms = elapsed_ms
                context.set_node_result(result)

                if not result.success:
                    context.error_node = node.name
                    context.error_message = result.error or "Node returned failure"
                    context.transition_to(WorkflowState.FAILED)
                    logger.error(
                        "Workflow %s node %s returned failure: %s",
                        context.workflow_id,
                        node.name,
                        result.error,
                    )
                    return context

                logger.info(
                    "Workflow %s node %s completed in %dms",
                    context.workflow_id,
                    node.name,
                    elapsed_ms,
                )
            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                context.set_node_result(NodeResult(
                    node_name=node.name,
                    success=False,
                    error=str(exc),
                    duration_ms=elapsed_ms,
                ))
                context.error_node = node.name
                context.error_message = str(exc)

                if isinstance(exc, PauseWorkflow):
                    context.paused_at_node = node.name
                    context.transition_to(WorkflowState.PAUSED)
                    logger.info(
                        "Workflow %s paused at node %s",
                        context.workflow_id,
                        node.name,
                    )
                    return context

                context.transition_to(WorkflowState.FAILED)
                logger.error(
                    "Workflow %s failed at node %s: %s",
                    context.workflow_id,
                    node.name,
                    exc,
                )
                return context

        context.current_node = None
        context.transition_to(WorkflowState.COMPLETED)
        logger.info("Workflow %s completed successfully", context.workflow_id)
        return context

    def _find_node_index(self, node_name: str) -> int:
        for i, node in enumerate(self.nodes):
            if node.name == node_name:
                return i
        return -1


class PauseWorkflow(Exception):
    def __init__(self, reason: str = "Workflow paused for human approval") -> None:
        self.reason = reason
        super().__init__(reason)
