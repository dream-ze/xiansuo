from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.workflow.context import NodeResult, WorkflowContext

logger = logging.getLogger(__name__)


class QualityEvalResult(BaseModel):
    overall_score: float = Field(ge=0.0, le=1.0, description="综合质量评分")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="相关性评分")
    completeness_score: float = Field(default=0.5, ge=0.0, le=1.0, description="完整性评分")
    readability_score: float = Field(default=0.5, ge=0.0, le=1.0, description="可读性评分")
    issues: list[str] = Field(default_factory=list, description="质量问题")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class AiQualityEvalNode:
    name = "ai_quality_eval"

    def __init__(self, structured_llm_client: Any = None) -> None:
        self._structured_llm = structured_llm_client

    async def execute(self, context: WorkflowContext) -> NodeResult:
        input_data = context.input_data
        content = input_data.get("script_text", "") or input_data.get("body", "") or input_data.get("text", "")
        topic = input_data.get("topic", "") or input_data.get("demand_type", "")

        if not content:
            return NodeResult(
                node_name=self.name,
                success=True,
                output=QualityEvalResult(
                    overall_score=0.0,
                    relevance_score=0.0,
                    completeness_score=0.0,
                    readability_score=0.0,
                    issues=["内容为空"],
                    suggestions=["请提供内容后再评估"],
                ).model_dump(),
            )

        if self._structured_llm is None:
            return NodeResult(
                node_name=self.name,
                success=True,
                output=self._heuristic_eval(content, topic),
            )

        try:
            result, metadata = self._structured_llm.complete_structured(
                model_config=input_data["model_config"],
                api_key=input_data["api_key"],
                system_prompt=self._build_system_prompt(),
                user_prompt=f"请评估以下内容的质量：\n\n主题：{topic}\n内容：{content}",
                response_model=QualityEvalResult,
                max_retries=1,
            )

            return NodeResult(
                node_name=self.name,
                success=True,
                output=result.model_dump(),
                llm_tokens_used=metadata.get("tokens_used"),
                llm_cost_estimate=metadata.get("cost_estimate"),
            )
        except Exception as exc:
            logger.error("AI quality eval failed: %s", exc)
            return NodeResult(
                node_name=self.name,
                success=True,
                output=self._heuristic_eval(content, topic),
                error=str(exc),
            )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True

    @staticmethod
    def _heuristic_eval(content: str, topic: str) -> dict:
        issues: list[str] = []
        suggestions: list[str] = []

        if len(content) < 20:
            issues.append("内容过短")
            suggestions.append("建议补充更多细节")
        elif len(content) > 2000:
            issues.append("内容过长")
            suggestions.append("建议精简到 500 字以内")

        relevance = 0.5
        if topic and topic in content:
            relevance = 0.8

        completeness = 0.5
        if len(content) >= 50:
            completeness = 0.7

        readability = 0.6
        if any(p in content for p in ["？", "！", "。", "，"]):
            readability = 0.7

        overall = (relevance + completeness + readability) / 3.0

        return QualityEvalResult(
            overall_score=overall,
            relevance_score=relevance,
            completeness_score=completeness,
            readability_score=readability,
            issues=issues,
            suggestions=suggestions,
        ).model_dump()

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "你是内容质量评估专家。你需要评估营销内容的质量。\n\n"
            "评估维度：\n"
            "1. 相关性：内容是否与主题/需求相关\n"
            "2. 完整性：内容是否包含必要信息\n"
            "3. 可读性：内容是否通顺、易读\n\n"
            "评分标准：0.0-1.0，0.6 以下为不合格"
        )
