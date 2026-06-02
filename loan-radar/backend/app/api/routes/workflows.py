from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.models import AiDraft, ApprovalQueue, Lead, ModelConfig, PublishJob, User, WorkflowLog, WorkflowRun
from app.rag.llama_index_config import build_embed_model, build_llm
from app.rag.query_engine import LlamaIndexQueryEngine
from app.schemas.workflow import (
    ContentPublishCheckRequest,
    LeadScoringRequest,
    ScriptGenerationRequest,
    WorkflowLogOut,
    WorkflowResumeRequest,
    WorkflowRunOut,
)
from app.services.structured_llm import StructuredLLMClient
from app.utils.response import error_response, success_response
from app.workflow.context import NodeResult, WorkflowContext, WorkflowState
from app.workflow.graphs.lead_scoring import build_lead_scoring_graph, _init_state as init_lead_scoring_state
from app.workflow.graphs.script_generation import build_script_generation_graph, _init_state as init_script_generation_state
from app.workflow.graphs.content_publish import build_content_publish_graph, _init_state as init_content_publish_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

_USE_LANGGRAPH = True

_CHROMA_PERSIST_DIR = "./storage/chroma"


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


def _get_structured_llm(db: Session, current_user: User) -> tuple[StructuredLLMClient, ModelConfig, str]:
    model_config, api_key = _get_text_model_context(db, current_user)
    return StructuredLLMClient(), model_config, api_key


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


def _persist_workflow_run(db: Session, context: WorkflowContext, user_id: int) -> WorkflowRun:
    run = db.scalar(
        select(WorkflowRun).where(WorkflowRun.workflow_id == context.workflow_id)
    )
    db_data = context.to_db_dict()
    if run is not None:
        run.state = db_data["state"]
        run.output_data = db_data["output_data"]
        run.current_node = db_data["current_node"]
        run.paused_at_node = db_data["paused_at_node"]
        run.error_node = db_data["error_node"]
        run.error_message = db_data["error_message"]
        run.retry_count = db_data["retry_count"]
        if context.state == WorkflowState.COMPLETED:
            from app.core.time import shanghai_now
            run.completed_at = shanghai_now()
    else:
        run = WorkflowRun(
            user_id=user_id,
            **db_data,
        )
        db.add(run)
    db.flush()
    return run


def _persist_workflow_logs(db: Session, context: WorkflowContext) -> None:
    for node_name, result in context.node_results.items():
        existing = db.scalar(
            select(WorkflowLog).where(
                WorkflowLog.workflow_id == context.workflow_id,
                WorkflowLog.node_name == node_name,
            )
        )
        log_data = {
            "event_type": "completed" if result.success else "failed",
            "input_snapshot": None,
            "output_snapshot": result.output,
            "error_message": result.error,
            "duration_ms": result.duration_ms,
            "llm_tokens_used": result.llm_tokens_used,
            "llm_cost_estimate": result.llm_cost_estimate,
        }
        if existing is not None:
            for key, value in log_data.items():
                setattr(existing, key, value)
        else:
            db.add(WorkflowLog(
                workflow_id=context.workflow_id,
                node_name=node_name,
                **log_data,
            ))
    db.flush()


def _persist_langgraph_run(
    db: Session,
    workflow_id: str,
    workflow_type: str,
    user_id: int,
    state: dict[str, Any],
    final_state: str = "completed",
) -> None:
    node_results = final_state_data = state.get("node_results", {})

    run = db.scalar(
        select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id)
    )

    output_data = {}
    for key, value in state.items():
        if key.startswith("_") or key in ("node_results",):
            continue
        output_data[key] = value

    if run is not None:
        run.state = final_state
        run.output_data = output_data
        run.current_node = None
        run.paused_at_node = None
        run.error_node = None
        run.error_message = state.get("error")
    else:
        run = WorkflowRun(
            user_id=user_id,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            state=final_state,
            input_data={k: v for k, v in state.items() if not k.startswith("_") and k not in ("node_results",)},
            output_data=output_data,
        )
        db.add(run)
    db.flush()

    for node_name, result_data in node_results.items():
        existing = db.scalar(
            select(WorkflowLog).where(
                WorkflowLog.workflow_id == workflow_id,
                WorkflowLog.node_name == node_name,
            )
        )
        log_data = {
            "event_type": "completed",
            "input_snapshot": None,
            "output_snapshot": result_data,
            "error_message": None,
            "duration_ms": None,
            "llm_tokens_used": None,
            "llm_cost_estimate": None,
        }
        if existing is not None:
            for key, value in log_data.items():
                setattr(existing, key, value)
        else:
            db.add(WorkflowLog(
                workflow_id=workflow_id,
                node_name=node_name,
                **log_data,
            ))
    db.flush()


def _create_approval_if_needed(db: Session, context: WorkflowContext, user_id: int) -> None:
    risk_gate_output = context.get_node_output("risk_gate")
    if not risk_gate_output or risk_gate_output.get("auto_approve", True):
        return

    input_data = context.input_data
    compliance_output = context.get_node_output("compliance_check")
    script_output = context.get_node_output("ai_script_generate")

    content_snapshot = {
        "workflow_id": context.workflow_id,
        "workflow_type": context.workflow_type,
    }
    if script_output:
        content_snapshot["script_candidates"] = script_output.get("candidates", [])
        content_snapshot["recommended_index"] = script_output.get("recommended_index", 0)
    else:
        content_snapshot["text"] = input_data.get("text", "")
        content_snapshot["body"] = input_data.get("body", "")

    content_type = "follow_up_script"
    content_id = input_data.get("lead_id")
    if context.workflow_type == "content_publish":
        content_type = "draft"
        content_id = input_data.get("draft_id") or input_data.get("publish_job_id")

    existing = db.scalar(
        select(ApprovalQueue).where(
            ApprovalQueue.workflow_id == context.workflow_id,
            ApprovalQueue.status == "pending",
        )
    )
    if existing is not None:
        return

    approval = ApprovalQueue(
        user_id=user_id,
        workflow_id=context.workflow_id,
        workflow_type=context.workflow_type,
        content_type=content_type,
        content_id=content_id,
        content_snapshot=content_snapshot,
        risk_level=risk_gate_output.get("risk_level", "medium"),
        compliance_result=compliance_output,
        status="pending",
    )
    db.add(approval)
    db.flush()


@router.post("/lead-scoring")
async def run_lead_scoring(
    payload: LeadScoringRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    structured_llm, model_config, api_key = _get_structured_llm(db, current_user)

    if _USE_LANGGRAPH:
        graph = build_lead_scoring_graph(
            db=db,
            structured_llm_client=structured_llm,
        )

        init_state = init_lead_scoring_state(
            text=payload.text,
            platform=payload.platform,
            source_id=payload.source_id,
            source_type=payload.source_type,
            source_post_id=payload.source_post_id,
            source_comment_id=payload.source_comment_id,
            user_name=payload.user_name,
            user_profile_url=payload.user_profile_url,
            model_config=model_config,
            api_key=api_key,
            user_id=current_user.id,
        )

        config = {"configurable": {"thread_id": init_state["workflow_id"]}}
        result = await graph.ainvoke(init_state, config=config)

        _persist_langgraph_run(
            db,
            workflow_id=init_state["workflow_id"],
            workflow_type="lead_scoring",
            user_id=current_user.id,
            state=result,
            final_state="completed",
        )
        db.commit()

        return success_response({
            "workflow_id": init_state["workflow_id"],
            "state": "completed",
            "rule_score": result.get("rule_score", 0),
            "rule_level": result.get("rule_level", "D"),
            "ai_result": {
                "is_potential_lead": result.get("is_potential_lead", False),
                "confidence": result.get("ai_confidence", 0.0),
                "lead_level": result.get("ai_lead_level", "D"),
                "demand_type": result.get("ai_demand_type", ""),
                "urgency": result.get("ai_urgency", "low"),
                "demand_summary": result.get("ai_demand_summary", ""),
                "key_evidence": result.get("ai_key_evidence", []),
                "estimated_amount": result.get("ai_estimated_amount"),
                "risk_flags": result.get("ai_risk_flags", []),
                "reasoning": result.get("ai_reasoning", ""),
            },
            "lead_id": result.get("lead_id"),
        })

    from app.workflow.definitions.lead_scoring import create_lead_scoring_context, create_lead_scoring_workflow

    context = create_lead_scoring_context(
        text=payload.text,
        platform=payload.platform,
        source_id=payload.source_id,
        source_type=payload.source_type,
        source_post_id=payload.source_post_id,
        source_comment_id=payload.source_comment_id,
        user_name=payload.user_name,
        user_profile_url=payload.user_profile_url,
        model_config=model_config,
        api_key=api_key,
        user_id=current_user.id,
    )

    engine = create_lead_scoring_workflow(db=db, structured_llm_client=structured_llm)
    context = await engine.run(context)
    _persist_workflow_run(db, context, current_user.id)
    _persist_workflow_logs(db, context)
    db.commit()

    rule_output = context.get_node_output("rule_prescreen")
    ai_output = context.get_node_output("ai_lead_identify")
    persist_output = context.get_node_output("lead_persist")

    return success_response({
        "workflow_id": context.workflow_id,
        "state": context.state.value,
        "rule_score": rule_output.get("rule_score", 0),
        "rule_level": rule_output.get("lead_level", "D"),
        "ai_result": ai_output,
        "lead_id": persist_output.get("lead_id") if persist_output else None,
    })


@router.post("/script-generation")
async def run_script_generation(
    payload: ScriptGenerationRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    structured_llm, model_config, api_key = _get_structured_llm(db, current_user)

    lead = db.get(Lead, payload.lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="线索未找到")

    if _USE_LANGGRAPH:
        query_engine = _build_query_engine(model_config, api_key)

        graph = build_script_generation_graph(
            query_engine=query_engine,
            structured_llm_client=structured_llm,
        )

        init_state = init_script_generation_state(
            text=lead.content or "",
            demand_type=payload.demand_type or lead.demand_type or "",
            lead_level=payload.lead_level or lead.lead_level or "C",
            lead_id=lead.id,
            model_config=model_config,
            api_key=api_key,
            user_id=current_user.id,
        )

        config = {"configurable": {"thread_id": init_state["workflow_id"]}}
        result = await graph.ainvoke(init_state, config=config)

        final_state = "completed"
        if not result.get("auto_approve", True) and not result.get("approved", True):
            final_state = "paused"

        _persist_langgraph_run(
            db,
            workflow_id=init_state["workflow_id"],
            workflow_type="script_generation",
            user_id=current_user.id,
            state=result,
            final_state=final_state,
        )
        db.commit()

        return success_response({
            "workflow_id": init_state["workflow_id"],
            "state": final_state,
            "scripts": result.get("node_results", {}).get("ai_script_generate", {}),
            "compliance": result.get("node_results", {}).get("compliance_check", {}),
            "risk_gate": result.get("node_results", {}).get("risk_gate", {}),
        })

    from app.workflow.definitions.script_generation import create_script_generation_context, create_script_generation_workflow

    context = create_script_generation_context(
        text=lead.content or "",
        demand_type=payload.demand_type or lead.demand_type or "",
        lead_level=payload.lead_level or lead.lead_level or "C",
        lead_id=lead.id,
        model_config=model_config,
        api_key=api_key,
        user_id=current_user.id,
    )

    engine = create_script_generation_workflow(structured_llm_client=structured_llm)
    context = await engine.run(context)
    _persist_workflow_run(db, context, current_user.id)
    _persist_workflow_logs(db, context)
    _create_approval_if_needed(db, context, current_user.id)
    db.commit()

    script_output = context.get_node_output("ai_script_generate")
    compliance_output = context.get_node_output("compliance_check")
    risk_gate_output = context.get_node_output("risk_gate")

    return success_response({
        "workflow_id": context.workflow_id,
        "state": context.state.value,
        "scripts": script_output,
        "compliance": compliance_output,
        "risk_gate": risk_gate_output,
    })


@router.post("/content-publish-check")
async def run_content_publish_check(
    payload: ContentPublishCheckRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    structured_llm, model_config, api_key = _get_structured_llm(db, current_user)

    title = payload.title
    body = payload.body

    if payload.draft_id is not None:
        draft = db.get(AiDraft, payload.draft_id)
        if draft is None or draft.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="草稿未找到")
        title = title or draft.title
        body = body or draft.body

    if payload.publish_job_id is not None:
        job = db.get(PublishJob, payload.publish_job_id)
        if job is None or job.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发布任务未找到")
        title = title or job.title
        body = body or job.body

    if _USE_LANGGRAPH:
        graph = build_content_publish_graph(structured_llm_client=structured_llm)

        init_state = init_content_publish_state(
            title=title,
            body=body,
            draft_id=payload.draft_id,
            publish_job_id=payload.publish_job_id,
            model_config=model_config,
            api_key=api_key,
            user_id=current_user.id,
        )

        config = {"configurable": {"thread_id": init_state["workflow_id"]}}
        result = await graph.ainvoke(init_state, config=config)

        final_state = "completed"
        if not result.get("auto_approve", True) and not result.get("approved", True):
            final_state = "paused"

        _persist_langgraph_run(
            db,
            workflow_id=init_state["workflow_id"],
            workflow_type="content_publish",
            user_id=current_user.id,
            state=result,
            final_state=final_state,
        )
        db.commit()

        return success_response({
            "workflow_id": init_state["workflow_id"],
            "state": final_state,
            "quality": result.get("node_results", {}).get("ai_quality_eval", {}),
            "compliance": result.get("node_results", {}).get("compliance_check", {}),
            "risk_gate": result.get("node_results", {}).get("risk_gate", {}),
        })

    from app.workflow.definitions.content_publish import create_content_publish_context, create_content_publish_workflow

    context = create_content_publish_context(
        title=title,
        body=body,
        draft_id=payload.draft_id,
        publish_job_id=payload.publish_job_id,
        model_config=model_config,
        api_key=api_key,
        user_id=current_user.id,
    )

    engine = create_content_publish_workflow(structured_llm_client=structured_llm)
    context = await engine.run(context)
    _persist_workflow_run(db, context, current_user.id)
    _persist_workflow_logs(db, context)
    _create_approval_if_needed(db, context, current_user.id)
    db.commit()

    quality_output = context.get_node_output("ai_quality_eval")
    compliance_output = context.get_node_output("compliance_check")
    risk_gate_output = context.get_node_output("risk_gate")

    return success_response({
        "workflow_id": context.workflow_id,
        "state": context.state.value,
        "quality": quality_output,
        "compliance": compliance_output,
        "risk_gate": risk_gate_output,
    })


@router.get("/runs")
def list_workflow_runs(
    workflow_type: str | None = None,
    state: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    statement = select(WorkflowRun).where(WorkflowRun.user_id == current_user.id)
    if workflow_type:
        statement = statement.where(WorkflowRun.workflow_type == workflow_type)
    if state:
        statement = statement.where(WorkflowRun.state == state)

    runs = db.scalars(
        statement.order_by(WorkflowRun.created_at.desc(), WorkflowRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    from app.schemas.common import paginated
    return paginated(
        [WorkflowRunOut.model_validate(r).model_dump(mode="json") for r in runs],
        page,
        page_size,
    )


@router.get("/runs/{workflow_id}")
def get_workflow_run(
    workflow_id: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    run = db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.user_id == current_user.id,
        )
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流运行记录未找到")
    return success_response(WorkflowRunOut.model_validate(run).model_dump(mode="json"))


@router.get("/runs/{workflow_id}/logs")
def get_workflow_logs(
    workflow_id: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    run = db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.user_id == current_user.id,
        )
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流运行记录未找到")

    logs = db.scalars(
        select(WorkflowLog).where(
            WorkflowLog.workflow_id == workflow_id
        ).order_by(WorkflowLog.id.asc())
    ).all()

    return success_response([
        WorkflowLogOut.model_validate(log).model_dump(mode="json") for log in logs
    ])


@router.post("/runs/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: str,
    payload: WorkflowResumeRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    run = db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.user_id == current_user.id,
        )
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流运行记录未找到")

    if run.state != "paused":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能恢复暂停状态的工作流")

    approval = db.scalar(
        select(ApprovalQueue).where(
            ApprovalQueue.workflow_id == workflow_id,
            ApprovalQueue.status == "pending",
        )
    )

    if approval is not None:
        approval.status = "approved" if payload.approved else "rejected"
        approval.reviewer_id = current_user.id
        approval.review_comment = payload.review_comment
        approval.reviewed_at = __import__("datetime").datetime.utcnow()

    if not payload.approved:
        run.state = "cancelled"
        db.commit()
        return success_response({"workflow_id": workflow_id, "state": "cancelled", "approved": False})

    if _USE_LANGGRAPH:
        structured_llm, model_config, api_key = _get_structured_llm(db, current_user)

        if run.workflow_type == "script_generation":
            query_engine = _build_query_engine(model_config, api_key)
            graph = build_script_generation_graph(
                query_engine=query_engine,
                structured_llm_client=structured_llm,
            )
        elif run.workflow_type == "content_publish":
            graph = build_content_publish_graph(structured_llm_client=structured_llm)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持恢复此类型的工作流")

        config = {"configurable": {"thread_id": workflow_id}}
        result = await graph.ainvoke(
            Command(resume={"approved": True, "reviewer_id": current_user.id, "review_comment": payload.review_comment}),
            config=config,
        )

        _persist_langgraph_run(
            db,
            workflow_id=workflow_id,
            workflow_type=run.workflow_type,
            user_id=current_user.id,
            state=result,
            final_state="completed",
        )
        db.commit()

        return success_response({
            "workflow_id": workflow_id,
            "state": "completed",
        })

    context = WorkflowContext(
        workflow_id=run.workflow_id,
        workflow_type=run.workflow_type,
        user_id=run.user_id,
        state=WorkflowState.PAUSED,
        input_data=run.input_data or {},
        paused_at_node=run.paused_at_node,
    )

    if run.output_data:
        for name, output in run.output_data.items():
            context.set_node_result(NodeResult(node_name=name, success=True, output=output))

    structured_llm, model_config, api_key = _get_structured_llm(db, current_user)
    context.input_data["model_config"] = model_config
    context.input_data["api_key"] = api_key

    if run.workflow_type == "script_generation":
        from app.workflow.definitions.script_generation import create_script_generation_workflow
        engine = create_script_generation_workflow(structured_llm_client=structured_llm)
    elif run.workflow_type == "content_publish":
        from app.workflow.definitions.content_publish import create_content_publish_workflow
        engine = create_content_publish_workflow(structured_llm_client=structured_llm)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持恢复此类型的工作流")

    context = await engine.run(context)
    _persist_workflow_run(db, context, current_user.id)
    _persist_workflow_logs(db, context)
    db.commit()

    return success_response({
        "workflow_id": context.workflow_id,
        "state": context.state.value,
    })


@router.post("/runs/{workflow_id}/retry")
async def retry_workflow(
    workflow_id: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    run = db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.user_id == current_user.id,
        )
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流运行记录未找到")

    if run.state != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能重试失败状态的工作流")

    structured_llm, model_config, api_key = _get_structured_llm(db, current_user)

    if _USE_LANGGRAPH:
        if run.workflow_type == "lead_scoring":
            graph = build_lead_scoring_graph(db=db, structured_llm_client=structured_llm)
            init_state = init_lead_scoring_state(**run.input_data, model_config=model_config, api_key=api_key)
        elif run.workflow_type == "script_generation":
            query_engine = _build_query_engine(model_config, api_key)
            graph = build_script_generation_graph(query_engine=query_engine, structured_llm_client=structured_llm)
            init_state = init_script_generation_state(**run.input_data, model_config=model_config, api_key=api_key)
        elif run.workflow_type == "content_publish":
            graph = build_content_publish_graph(structured_llm_client=structured_llm)
            init_state = init_content_publish_state(**run.input_data, model_config=model_config, api_key=api_key)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持重试此类型的工作流")

        init_state["workflow_id"] = workflow_id
        config = {"configurable": {"thread_id": workflow_id}}
        result = await graph.ainvoke(init_state, config=config)

        _persist_langgraph_run(
            db,
            workflow_id=workflow_id,
            workflow_type=run.workflow_type,
            user_id=current_user.id,
            state=result,
            final_state="completed",
        )
        db.commit()

        return success_response({
            "workflow_id": workflow_id,
            "state": "completed",
        })

    context = WorkflowContext(
        workflow_id=run.workflow_id,
        workflow_type=run.workflow_type,
        user_id=run.user_id,
        state=WorkflowState.FAILED,
        input_data=run.input_data or {},
        error_node=run.error_node,
        error_message=run.error_message,
        retry_count=run.retry_count,
    )

    if run.output_data:
        for name, output in run.output_data.items():
            context.set_node_result(NodeResult(node_name=name, success=True, output=output))

    context.input_data["model_config"] = model_config
    context.input_data["api_key"] = api_key

    if run.workflow_type == "lead_scoring":
        from app.workflow.definitions.lead_scoring import create_lead_scoring_workflow
        engine = create_lead_scoring_workflow(db=db, structured_llm_client=structured_llm)
    elif run.workflow_type == "script_generation":
        from app.workflow.definitions.script_generation import create_script_generation_workflow
        engine = create_script_generation_workflow(structured_llm_client=structured_llm)
    elif run.workflow_type == "content_publish":
        from app.workflow.definitions.content_publish import create_content_publish_workflow
        engine = create_content_publish_workflow(structured_llm_client=structured_llm)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持重试此类型的工作流")

    context = await engine.run(context)
    _persist_workflow_run(db, context, current_user.id)
    _persist_workflow_logs(db, context)
    db.commit()

    return success_response({
        "workflow_id": context.workflow_id,
        "state": context.state.value,
    })
