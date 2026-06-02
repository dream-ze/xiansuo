from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.models import ModelConfig, User, WorkflowLog, WorkflowRun
from app.models.agent import AgentConversation
from app.rag.llama_index_config import build_embed_model, build_llm
from app.rag.query_engine import LlamaIndexQueryEngine
from app.services.structured_llm import StructuredLLMClient
from app.utils.response import success_response
from app.agent.react_agent import build_react_agent, _init_agent_state
from app.agent.memory import ConversationBufferMemory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

_CHROMA_PERSIST_DIR = "./storage/chroma"


class AgentChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=6000, description="用户问题")
    thread_id: str | None = Field(default=None, max_length=128, description="对话线程 ID，传入则继续多轮对话")
    max_iterations: int = Field(default=8, ge=1, le=20, description="最大迭代次数")


class AgentChatResponse(BaseModel):
    thread_id: str
    final_answer: str
    iterations: int
    tool_history: list[dict[str, Any]]


def _get_text_model_context(db: Session, current_user: User) -> tuple[ModelConfig, str]:
    config = db.scalars(
        select(ModelConfig).where(
            ModelConfig.user_id == current_user.id,
            ModelConfig.model_type == "text",
            ModelConfig.is_default.is_(True),
        )
    ).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先配置默认文本模型")
    api_key = decrypt_text(config.encrypted_api_key) if config.encrypted_api_key else ""
    return config, api_key


def _build_query_engine(model_config: ModelConfig, api_key: str) -> LlamaIndexQueryEngine:
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


def _persist_agent_run(
    db: Session,
    thread_id: str,
    user_id: int,
    query: str,
    result: dict[str, Any],
) -> None:
    workflow_id = f"agent_{thread_id}"

    run = db.scalar(
        select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id)
    )

    output_data = {
        "final_answer": result.get("final_answer", ""),
        "iterations": result.get("iteration", 0),
        "tool_history": result.get("tool_history", []),
    }

    if run is not None:
        run.state = "completed"
        run.output_data = output_data
    else:
        run = WorkflowRun(
            user_id=user_id,
            workflow_id=workflow_id,
            workflow_type="agent_react",
            state="completed",
            input_data={"query": query},
            output_data=output_data,
        )
        db.add(run)
    db.flush()

    tool_history = result.get("tool_history", [])
    for idx, entry in enumerate(tool_history):
        existing = db.scalar(
            select(WorkflowLog).where(
                WorkflowLog.workflow_id == workflow_id,
                WorkflowLog.node_name == f"tool_{idx}_{entry.get('action', 'unknown')}",
            )
        )
        log_data = {
            "event_type": "completed" if entry.get("success", True) else "failed",
            "input_snapshot": {"action": entry.get("action"), "action_input": entry.get("action_input")},
            "output_snapshot": {"observation": entry.get("observation", "")[:1000]},
            "error_message": None if entry.get("success", True) else entry.get("observation", ""),
        }
        if existing is not None:
            for key, value in log_data.items():
                setattr(existing, key, value)
        else:
            db.add(WorkflowLog(
                workflow_id=workflow_id,
                node_name=f"tool_{idx}_{entry.get('action', 'unknown')}",
                **log_data,
            ))
    db.flush()


@router.post("/chat")
async def agent_chat(
    payload: AgentChatRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    model_config, api_key = _get_text_model_context(db, current_user)
    structured_llm = StructuredLLMClient()
    query_engine = _build_query_engine(model_config, api_key)

    thread_id = payload.thread_id
    conversation_history: list[dict[str, Any]] = []

    if thread_id:
        memory = ConversationBufferMemory.load_from_db(
            db=db,
            thread_id=thread_id,
            user_id=current_user.id,
        )
        conversation_history = memory.get_context_messages()
    else:
        memory = ConversationBufferMemory()

    graph = build_react_agent(
        query_engine=query_engine,
        structured_llm_client=structured_llm,
        max_iterations=payload.max_iterations,
    )

    init_state = _init_agent_state(
        query=payload.query,
        model_config=model_config,
        api_key=api_key,
        user_id=current_user.id,
        max_iterations=payload.max_iterations,
        thread_id=thread_id,
        conversation_history=conversation_history,
    )

    actual_thread_id = init_state["thread_id"]

    config = {"configurable": {"thread_id": actual_thread_id}}
    result = await graph.ainvoke(init_state, config=config)

    if result.get("new_user_message", True):
        memory.add_user_message(payload.query)

    final_answer = result.get("final_answer", "")
    if final_answer:
        tool_calls = []
        for entry in result.get("tool_history", []):
            tool_calls.append({
                "action": entry.get("action"),
                "action_input": entry.get("action_input", {}),
                "success": entry.get("success", True),
            })

        memory.add_assistant_message(
            final_answer,
            tool_calls=tool_calls if tool_calls else None,
            iterations=result.get("iteration", 0),
        )

        for entry in result.get("tool_history", []):
            memory.add_tool_result(
                tool_name=entry.get("action", "unknown"),
                observation=entry.get("observation", "")[:500],
                success=entry.get("success", True),
            )

    memory.save_to_db(
        db=db,
        thread_id=actual_thread_id,
        user_id=current_user.id,
        only_new=True,
    )

    _persist_agent_run(
        db,
        thread_id=actual_thread_id,
        user_id=current_user.id,
        query=payload.query,
        result=result,
    )
    db.commit()

    return success_response({
        "thread_id": actual_thread_id,
        "final_answer": final_answer,
        "iterations": result.get("iteration", 0),
        "tool_history": result.get("tool_history", []),
    })


@router.get("/tools")
def list_agent_tools():
    from app.agent.tools import TOOL_DEFINITIONS
    return success_response(TOOL_DEFINITIONS)


@router.get("/conversations")
def list_conversations(
    limit: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    threads = ConversationBufferMemory.list_threads(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )
    return success_response(threads)


@router.get("/conversations/{thread_id}")
def get_conversation(
    thread_id: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    memory = ConversationBufferMemory.load_from_db(
        db=db,
        thread_id=thread_id,
        user_id=current_user.id,
    )

    messages = [m.to_dict() for m in memory.messages]

    return success_response({
        "thread_id": thread_id,
        "message_count": memory.message_count,
        "messages": messages,
    })


@router.delete("/conversations/{thread_id}")
def delete_conversation(
    thread_id: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    deleted = ConversationBufferMemory.delete_thread(
        db=db,
        thread_id=thread_id,
        user_id=current_user.id,
    )
    db.commit()
    return success_response({"thread_id": thread_id, "deleted_count": deleted})
