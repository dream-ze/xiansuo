from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    tool_name: str = Field(description="工具名称")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolResult(BaseModel):
    tool_name: str = Field(description="工具名称")
    success: bool = Field(default=True, description="是否成功")
    output: Any = Field(default=None, description="工具输出")
    error: str | None = Field(default=None, description="错误信息")


class KnowledgeSearchArgs(BaseModel):
    query: str = Field(description="检索查询文本")
    source_types: list[str] | None = Field(default=None, description="素材类型过滤，如 material/platform_rule/quality_script")
    top_k: int = Field(default=5, description="返回结果数量")


class ComplianceCheckArgs(BaseModel):
    content: str = Field(description="待审核内容")


class ScriptGenerateArgs(BaseModel):
    text: str = Field(description="客户评论/线索文本")
    demand_type: str = Field(default="", description="需求类型")
    lead_level: str = Field(default="C", description="线索等级 A/B/C/D")


class LeadScoreArgs(BaseModel):
    text: str = Field(description="待评分文本")


class QualityEvalArgs(BaseModel):
    content: str = Field(description="待评估内容")
    topic: str = Field(default="", description="内容主题")


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "knowledge_search",
        "description": (
            "检索知识库素材。可以搜索产品资料、平台规则、优质话术等。"
            "当需要获取产品信息、政策规则、历史话术参考时使用。"
            "source_types 可选值: material(产品素材), platform_rule(平台规则), quality_script(优质话术)"
        ),
        "parameters": KnowledgeSearchArgs.model_json_schema(),
    },
    {
        "name": "compliance_check",
        "description": (
            "合规审核工具。检查营销内容是否包含违规表述，如虚假承诺、夸大宣传、违规引导等。"
            "在生成话术或发布内容前，应使用此工具进行合规检查。"
            "返回风险等级(low/medium/high/critical)和违规详情。"
        ),
        "parameters": ComplianceCheckArgs.model_json_schema(),
    },
    {
        "name": "script_generate",
        "description": (
            "话术生成工具。根据客户评论和需求类型生成个性化跟进话术。"
            "会生成 2-3 个不同风格版本，并标注合规注意事项。"
            "lead_level: A=高意向, B=中等, C=弱意向, D=无意向"
        ),
        "parameters": ScriptGenerateArgs.model_json_schema(),
    },
    {
        "name": "lead_score",
        "description": (
            "线索评分工具。使用规则引擎对文本进行快速评分，判断是否为潜在贷款需求。"
            "返回评分(0-100)、线索等级(A/B/C/D)、需求类型等。"
            "适合对大量文本进行初步筛选。"
        ),
        "parameters": LeadScoreArgs.model_json_schema(),
    },
    {
        "name": "quality_eval",
        "description": (
            "内容质量评估工具。评估营销内容的整体质量，包括相关性、完整性、可读性。"
            "返回 0-1 评分和改进建议。"
        ),
        "parameters": QualityEvalArgs.model_json_schema(),
    },
]


def _format_tool_definitions() -> str:
    parts = []
    for tool in TOOL_DEFINITIONS:
        params = tool["parameters"]
        required = params.get("required", [])
        properties = params.get("properties", {})

        param_strs = []
        for pname, pdef in properties.items():
            ptype = pdef.get("type", "string")
            pdesc = pdef.get("description", "")
            is_req = pname in required
            param_strs.append(f"  - {pname} ({ptype}, {'必填' if is_req else '可选'}): {pdesc}")

        parts.append(
            f"### {tool['name']}\n{tool['description']}\n参数:\n" + "\n".join(param_strs)
        )

    return "\n\n".join(parts)


def execute_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    *,
    query_engine=None,
    structured_llm_client=None,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
) -> ToolResult:
    if tool_name == "knowledge_search":
        return _tool_knowledge_search(
            tool_args,
            query_engine=query_engine,
            user_id=user_id,
        )
    elif tool_name == "compliance_check":
        return _tool_compliance_check(
            tool_args,
            structured_llm_client=structured_llm_client,
            model_config=model_config,
            api_key=api_key,
        )
    elif tool_name == "script_generate":
        return _tool_script_generate(
            tool_args,
            structured_llm_client=structured_llm_client,
            model_config=model_config,
            api_key=api_key,
        )
    elif tool_name == "lead_score":
        return _tool_lead_score(tool_args)
    elif tool_name == "quality_eval":
        return _tool_quality_eval(
            tool_args,
            structured_llm_client=structured_llm_client,
            model_config=model_config,
            api_key=api_key,
        )
    else:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            error=f"未知工具: {tool_name}",
        )


def _tool_knowledge_search(
    args: dict[str, Any],
    *,
    query_engine=None,
    user_id: int | None = None,
) -> ToolResult:
    if query_engine is None:
        return ToolResult(
            tool_name="knowledge_search",
            success=False,
            error="知识库未配置，无法检索",
        )

    query = args.get("query", "")
    source_types = args.get("source_types")
    top_k = args.get("top_k", 5)

    if not query:
        return ToolResult(
            tool_name="knowledge_search",
            success=False,
            error="查询文本不能为空",
        )

    try:
        results = query_engine.retrieve(
            query=query,
            user_id=user_id or 0,
            top_k=top_k,
            source_types=source_types,
        )

        if not results:
            return ToolResult(
                tool_name="knowledge_search",
                success=True,
                output={"results": [], "total": 0, "message": "未找到相关素材"},
            )

        formatted = []
        for r in results:
            formatted.append({
                "source_type": r.get("source_type", ""),
                "content": r.get("content", "")[:500],
                "score": r.get("score", 0),
            })

        return ToolResult(
            tool_name="knowledge_search",
            success=True,
            output={"results": formatted, "total": len(formatted)},
        )
    except Exception as exc:
        logger.error("Knowledge search tool failed: %s", exc)
        return ToolResult(
            tool_name="knowledge_search",
            success=False,
            error=str(exc),
        )


def _tool_compliance_check(
    args: dict[str, Any],
    *,
    structured_llm_client=None,
    model_config=None,
    api_key: str = "",
) -> ToolResult:
    content = args.get("content", "")
    if not content:
        return ToolResult(
            tool_name="compliance_check",
            success=False,
            error="待审核内容不能为空",
        )

    try:
        from app.workflow.nodes.compliance_check import ComplianceCheckNode

        node = ComplianceCheckNode(structured_llm_client=structured_llm_client)
        keyword_result = node._keyword_check(content)

        risk_level = keyword_result.get("risk_level", "low")

        if structured_llm_client is not None and risk_level in ("medium", "high", "critical") and model_config is not None:
            try:
                from app.workflow.nodes.compliance_check import ComplianceResult, ComplianceViolation

                system_prompt = ComplianceCheckNode._build_system_prompt()
                result, metadata = structured_llm_client.complete_structured(
                    model_config=model_config,
                    api_key=api_key,
                    system_prompt=system_prompt,
                    user_prompt=f"请审核以下内容的合规性：\n\n{content}",
                    response_model=ComplianceResult,
                    max_retries=1,
                )

                if not result.violations and keyword_result.get("violations"):
                    result.violations = [ComplianceViolation(**v) for v in keyword_result["violations"]]
                    result.is_compliant = False
                    result.risk_level = ComplianceCheckNode._higher_risk(
                        result.risk_level, keyword_result.get("risk_level", "low")
                    )

                return ToolResult(
                    tool_name="compliance_check",
                    success=True,
                    output=result.model_dump(),
                )
            except Exception as exc:
                logger.error("AI compliance check failed: %s", exc)

        return ToolResult(
            tool_name="compliance_check",
            success=True,
            output=keyword_result,
        )
    except Exception as exc:
        logger.error("Compliance check tool failed: %s", exc)
        return ToolResult(
            tool_name="compliance_check",
            success=False,
            error=str(exc),
        )


def _tool_script_generate(
    args: dict[str, Any],
    *,
    structured_llm_client=None,
    model_config=None,
    api_key: str = "",
) -> ToolResult:
    text = args.get("text", "")
    demand_type = args.get("demand_type", "")
    lead_level = args.get("lead_level", "C")

    if not text:
        return ToolResult(
            tool_name="script_generate",
            success=False,
            error="线索文本不能为空",
        )

    if structured_llm_client is None or model_config is None:
        from app.workflow.nodes.ai_script_generate import AiScriptGenerateNode
        fallback = AiScriptGenerateNode._fallback_script(text, demand_type, lead_level)
        return ToolResult(
            tool_name="script_generate",
            success=True,
            output=fallback,
        )

    try:
        from app.workflow.nodes.ai_script_generate import AiScriptGenerateNode, ScriptGenerateResult

        rag_output = {"references": [], "rules": [], "top_scripts": []}
        system_prompt = AiScriptGenerateNode._build_system_prompt(rag_output)
        user_prompt = AiScriptGenerateNode._build_user_prompt(text, demand_type, lead_level, rag_output)

        result, metadata = structured_llm_client.complete_structured(
            model_config=model_config,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ScriptGenerateResult,
            max_retries=2,
        )

        return ToolResult(
            tool_name="script_generate",
            success=True,
            output=result.model_dump(),
        )
    except Exception as exc:
        logger.error("Script generate tool failed: %s", exc)
        from app.workflow.nodes.ai_script_generate import AiScriptGenerateNode
        fallback = AiScriptGenerateNode._fallback_script(text, demand_type, lead_level)
        return ToolResult(
            tool_name="script_generate",
            success=True,
            output=fallback,
            error=str(exc),
        )


def _tool_lead_score(args: dict[str, Any]) -> ToolResult:
    text = args.get("text", "")
    if not text:
        return ToolResult(
            tool_name="lead_score",
            success=False,
            error="待评分文本不能为空",
        )

    try:
        from app.services.lead_scoring_service import LeadScoringService

        service = LeadScoringService()
        result = service.score(text)

        return ToolResult(
            tool_name="lead_score",
            success=True,
            output={
                "lead_level": result.lead_level,
                "lead_score": result.lead_score,
                "demand_type": result.demand_type,
                "risk_level": result.risk_level,
                "is_suspected_demand": result.is_suspected_demand,
                "matched_words": result.evidence.get("matched_words", []),
                "reason": result.reason,
            },
        )
    except Exception as exc:
        logger.error("Lead score tool failed: %s", exc)
        return ToolResult(
            tool_name="lead_score",
            success=False,
            error=str(exc),
        )


def _tool_quality_eval(
    args: dict[str, Any],
    *,
    structured_llm_client=None,
    model_config=None,
    api_key: str = "",
) -> ToolResult:
    content = args.get("content", "")
    topic = args.get("topic", "")

    if not content:
        return ToolResult(
            tool_name="quality_eval",
            success=False,
            error="待评估内容不能为空",
        )

    if structured_llm_client is None or model_config is None:
        from app.workflow.nodes.ai_quality_eval import AiQualityEvalNode
        heuristic = AiQualityEvalNode._heuristic_eval(content, topic)
        return ToolResult(
            tool_name="quality_eval",
            success=True,
            output=heuristic,
        )

    try:
        from app.workflow.nodes.ai_quality_eval import AiQualityEvalNode, QualityEvalResult

        system_prompt = AiQualityEvalNode._build_system_prompt()
        result, metadata = structured_llm_client.complete_structured(
            model_config=model_config,
            api_key=api_key,
            system_prompt=system_prompt,
            user_prompt=f"请评估以下内容的质量：\n\n主题：{topic}\n内容：{content}",
            response_model=QualityEvalResult,
            max_retries=1,
        )

        return ToolResult(
            tool_name="quality_eval",
            success=True,
            output=result.model_dump(),
        )
    except Exception as exc:
        logger.error("Quality eval tool failed: %s", exc)
        from app.workflow.nodes.ai_quality_eval import AiQualityEvalNode
        heuristic = AiQualityEvalNode._heuristic_eval(content, topic)
        return ToolResult(
            tool_name="quality_eval",
            success=True,
            output=heuristic,
            error=str(exc),
        )
