from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.workflow.context import NodeResult, WorkflowContext

logger = logging.getLogger(__name__)


class ComplianceViolation(BaseModel):
    category: str = Field(description="违规类别")
    description: str = Field(description="违规描述")
    severity: str = Field(default="medium", description="严重程度")
    original_text: str = Field(default="", description="原始违规文本")


class ComplianceResult(BaseModel):
    is_compliant: bool = Field(description="是否合规")
    risk_level: str = Field(default="low", description="风险等级 low/medium/high/critical")
    violations: list[ComplianceViolation] = Field(default_factory=list, description="违规列表")
    suggestions: list[str] = Field(default_factory=list, description="修改建议")
    auto_fix_available: bool = Field(default=False, description="是否可自动修正")
    fixed_script: str | None = Field(default=None, description="自动修正版本")


class ComplianceCheckNode:
    name = "compliance_check"

    COMPLIANCE_KEYWORDS = {
        "critical": [
            "包下款", "百分百下款", "黑户包装", "刷流水",
            "套现", "洗钱", "代还", "代刷",
        ],
        "high": [
            "最低利率", "零利息", "免息", "无门槛",
            "不看征信", "无视黑白户", "秒批", "必下",
        ],
        "medium": [
            "保证", "承诺", "一定", "肯定能",
            "内部渠道", "特殊通道", "加急办理",
        ],
    }

    def __init__(self, structured_llm_client: Any = None) -> None:
        self._structured_llm = structured_llm_client

    async def execute(self, context: WorkflowContext) -> NodeResult:
        input_data = context.input_data
        content = input_data.get("script_text", "") or input_data.get("text", "")

        if not content:
            return NodeResult(
                node_name=self.name,
                success=True,
                output=ComplianceResult(
                    is_compliant=True,
                    risk_level="low",
                ).model_dump(),
            )

        keyword_result = self._keyword_check(content)

        if self._structured_llm is not None and keyword_result.get("risk_level", "low") in ("medium", "high", "critical"):
            try:
                result, metadata = self._structured_llm.complete_structured(
                    model_config=input_data["model_config"],
                    api_key=input_data["api_key"],
                    system_prompt=self._build_system_prompt(),
                    user_prompt=f"请审核以下内容的合规性：\n\n{content}",
                    response_model=ComplianceResult,
                    max_retries=1,
                )

                if not result.violations and keyword_result.get("violations"):
                    result.violations = [ComplianceViolation(**v) for v in keyword_result["violations"]]
                    result.is_compliant = False
                    result.risk_level = self._higher_risk(result.risk_level, keyword_result.get("risk_level", "low"))

                return NodeResult(
                    node_name=self.name,
                    success=True,
                    output=result.model_dump(),
                    llm_tokens_used=metadata.get("tokens_used"),
                    llm_cost_estimate=metadata.get("cost_estimate"),
                )
            except Exception as exc:
                logger.error("AI compliance check failed: %s", exc)

        return NodeResult(
            node_name=self.name,
            success=True,
            output=keyword_result,
        )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True

    def _keyword_check(self, content: str) -> dict:
        violations: list[dict] = []
        max_severity = "low"

        for severity, keywords in self.COMPLIANCE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    violations.append({
                        "category": "合规关键词",
                        "description": f"包含敏感词「{keyword}」",
                        "severity": severity,
                        "original_text": keyword,
                    })
                    max_severity = self._higher_risk(max_severity, severity)

        risk_level = max_severity
        suggestions = []
        if violations:
            suggestions.append("建议移除或替换敏感表述")
            for v in violations:
                suggestions.append(f"- 移除「{v['original_text']}」")

        return ComplianceResult(
            is_compliant=len(violations) == 0,
            risk_level=risk_level,
            violations=[ComplianceViolation(**v) for v in violations],
            suggestions=suggestions,
            auto_fix_available=False,
        ).model_dump()

    @staticmethod
    def _higher_risk(a: str, b: str) -> str:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "你是助贷行业合规审核专家。你需要审核营销话术是否合规。\n\n"
            "审核维度：\n"
            "1. 是否包含虚假承诺（包下款、百分百通过等）\n"
            "2. 是否包含违规引导（黑户包装、刷流水等）\n"
            "3. 是否夸大宣传（零利息、无门槛等）\n"
            "4. 是否符合《广告法》和金融营销规范\n"
            "5. 是否适合在社交媒体公开发布\n\n"
            "风险等级：\n"
            "- critical：严重违规，涉及违法或欺诈\n"
            "- high：高风险，可能被平台处罚\n"
            "- medium：中等风险，建议修改\n"
            "- low：低风险，基本合规"
        )
