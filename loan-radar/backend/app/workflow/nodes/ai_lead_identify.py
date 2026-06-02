from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.workflow.context import NodeResult, WorkflowContext

logger = logging.getLogger(__name__)


class LeadIdentifyResult(BaseModel):
    is_potential_lead: bool = Field(description="是否为潜在线索")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度 0-1")
    lead_level: str = Field(description="线索等级 A/B/C/D")
    demand_type: str = Field(description="需求类型")
    urgency: str = Field(default="low", description="紧迫程度 high/medium/low")
    demand_summary: str = Field(default="", description="AI 总结的需求要点")
    key_evidence: list[str] = Field(default_factory=list, description="关键证据片段")
    estimated_amount: str | None = Field(default=None, description="提取的金额信息")
    risk_flags: list[str] = Field(default_factory=list, description="风险标记")
    reasoning: str = Field(default="", description="AI 推理过程")


class AiLeadIdentifyNode:
    name = "ai_lead_identify"

    def __init__(self, structured_llm_client: Any = None) -> None:
        self._structured_llm = structured_llm_client

    async def execute(self, context: WorkflowContext) -> NodeResult:
        text = context.input_data.get("text", "")
        rule_output = context.get_node_output("rule_prescreen")

        if not text or not text.strip():
            return NodeResult(
                node_name=self.name,
                success=True,
                output={
                    "is_potential_lead": False,
                    "confidence": 0.0,
                    "lead_level": "D",
                    "demand_type": "无效",
                    "urgency": "low",
                    "demand_summary": "",
                    "key_evidence": [],
                    "estimated_amount": None,
                    "risk_flags": [],
                    "reasoning": "内容为空，跳过 AI 识别",
                },
            )

        if self._structured_llm is None:
            return NodeResult(
                node_name=self.name,
                success=True,
                output=self._fallback_from_rules(text, rule_output),
            )

        try:
            result, metadata = self._structured_llm.complete_structured(
                model_config=context.input_data["model_config"],
                api_key=context.input_data["api_key"],
                system_prompt=self._build_system_prompt(),
                user_prompt=self._build_user_prompt(text, rule_output),
                response_model=LeadIdentifyResult,
                max_retries=2,
            )

            return NodeResult(
                node_name=self.name,
                success=True,
                output=result.model_dump(),
                llm_tokens_used=metadata.get("tokens_used"),
                llm_cost_estimate=metadata.get("cost_estimate"),
            )
        except Exception as exc:
            logger.error("AI lead identify failed: %s", exc)
            return NodeResult(
                node_name=self.name,
                success=True,
                output=self._fallback_from_rules(text, rule_output),
                error=str(exc),
            )

    def should_proceed(self, context: WorkflowContext) -> bool:
        rule_output = context.get_node_output("rule_prescreen")
        if rule_output.get("skipped"):
            return True
        rule_score = rule_output.get("rule_score", 0)
        return rule_score >= 15

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "你是助贷行业的线索识别专家。你需要分析社交媒体评论，判断是否为潜在贷款需求线索。\n"
            "分析维度：\n"
            "1. 需求明确度：是否明确表达了借款/贷款需求\n"
            "2. 紧迫程度：是否急需资金\n"
            "3. 资质条件：是否透露了征信、负债等资质信息\n"
            "4. 产品匹配：是否指向特定贷款产品\n"
            "5. 真实性：是否为真实个人需求（排除广告、同行、代理）\n\n"
            "线索等级标准：\n"
            "- A级：明确借款需求 + 紧迫 + 有资质信息，高转化概率\n"
            "- B级：有借款需求但不紧迫，或需求较明确但缺少资质信息\n"
            "- C级：弱意向，咨询性质，需要进一步沟通确认\n"
            "- D级：无需求、广告、同行、或已明确拒绝"
        )

    @staticmethod
    def _build_user_prompt(text: str, rule_output: dict) -> str:
        rule_info = ""
        if rule_output:
            rule_info = (
                f"\n\n规则引擎预筛结果：\n"
                f"- 规则评分：{rule_output.get('rule_score', 0)}\n"
                f"- 规则等级：{rule_output.get('lead_level', 'D')}\n"
                f"- 命中关键词：{', '.join(rule_output.get('matched', []))}\n"
                f"- 需求类型：{rule_output.get('demand_type', '未知')}\n"
            )
        return f"请分析以下评论是否为潜在贷款需求线索：\n\n评论内容：{text}{rule_info}"

    @staticmethod
    def _fallback_from_rules(text: str, rule_output: dict) -> dict:
        if rule_output:
            return {
                "is_potential_lead": rule_output.get("pass", False),
                "confidence": min(rule_output.get("rule_score", 0) / 100.0, 1.0),
                "lead_level": rule_output.get("lead_level", "D"),
                "demand_type": rule_output.get("demand_type", "未知"),
                "urgency": "high" if rule_output.get("rule_score", 0) >= 70 else "medium" if rule_output.get("rule_score", 0) >= 40 else "low",
                "demand_summary": rule_output.get("reason", ""),
                "key_evidence": rule_output.get("matched", []),
                "estimated_amount": None,
                "risk_flags": [],
                "reasoning": "AI 不可用，使用规则引擎结果作为降级方案",
            }
        return {
            "is_potential_lead": False,
            "confidence": 0.0,
            "lead_level": "D",
            "demand_type": "未知",
            "urgency": "low",
            "demand_summary": "",
            "key_evidence": [],
            "estimated_amount": None,
            "risk_flags": [],
            "reasoning": "AI 和规则引擎均不可用",
        }
