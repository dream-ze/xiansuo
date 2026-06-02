from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.PENDING: {WorkflowState.RUNNING},
    WorkflowState.RUNNING: {WorkflowState.PAUSED, WorkflowState.COMPLETED, WorkflowState.FAILED},
    WorkflowState.PAUSED: {WorkflowState.RUNNING, WorkflowState.CANCELLED},
    WorkflowState.FAILED: {WorkflowState.RUNNING},
    WorkflowState.COMPLETED: set(),
    WorkflowState.CANCELLED: set(),
}


class NodeResult(BaseModel):
    node_name: str
    success: bool = True
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int | None = None
    llm_tokens_used: int | None = None
    llm_cost_estimate: float | None = None

    class Config:
        arbitrary_types_allowed = True


class WorkflowContext(BaseModel):
    workflow_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    workflow_type: str
    user_id: int | None = None
    state: WorkflowState = WorkflowState.PENDING
    input_data: dict[str, Any] = Field(default_factory=dict)
    node_results: dict[str, NodeResult] = Field(default_factory=dict)
    current_node: str | None = None
    paused_at_node: str | None = None
    error_node: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    parent_workflow_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

    def can_transition_to(self, target: WorkflowState) -> bool:
        allowed = VALID_TRANSITIONS.get(self.state, set())
        return target in allowed

    def transition_to(self, target: WorkflowState) -> None:
        if not self.can_transition_to(target):
            raise ValueError(f"Cannot transition from {self.state.value} to {target.value}")
        self.state = target
        self.updated_at = datetime.utcnow()

    def set_node_result(self, result: NodeResult) -> None:
        self.node_results[result.node_name] = result
        self.updated_at = datetime.utcnow()

    def get_node_output(self, node_name: str) -> dict[str, Any]:
        result = self.node_results.get(node_name)
        return result.output if result else {}

    def to_db_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "user_id": self.user_id,
            "state": self.state.value,
            "input_data": self.input_data,
            "output_data": {
                name: result.output for name, result in self.node_results.items()
            },
            "current_node": self.current_node,
            "paused_at_node": self.paused_at_node,
            "error_node": self.error_node,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "parent_workflow_id": self.parent_workflow_id,
        }
