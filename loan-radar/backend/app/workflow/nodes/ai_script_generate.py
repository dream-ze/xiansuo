from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.workflow.context import NodeResult, WorkflowContext

logger = logging.getLogger(__name__)


class ScriptCandidate(BaseModel):
    script_text: str = Field(description="话术文本")
    tone: str = Field(default="专业", description="语气风格")
    key_selling_points: list[str] = Field(default_factory=list, description="核心卖点")
    compliance_notes: list[str] = Field(default_factory=list, description="合规注意事项")


class ScriptGenerateResult(BaseModel):
    candidates: list[ScriptCandidate] = Field(default_factory=list, description="话术候选版本")
    recommended_index: int = Field(default=0, description="推荐版本索引")
    rag_sources: list[str] = Field(default_factory=list, description="引用的素材来源")
    generation_metadata: dict = Field(default_factory=dict, description="生成元数据")


class AiScriptGenerateNode:
    name = "ai_script_generate"

    def __init__(self, structured_llm_client: Any = None) -> None:
        self._structured_llm = structured_llm_client

    async def execute(self, context: WorkflowContext) -> NodeResult:
        input_data = context.input_data
        text = input_data.get("text", "")
        demand_type = input_data.get("demand_type", "")
        lead_level = input_data.get("lead_level", "C")
        rag_output = context.get_node_output("rag_retrieve")

        if self._structured_llm is None:
            return NodeResult(
                node_name=self.name,
                success=True,
                output=self._fallback_script(text, demand_type, lead_level),
            )

        try:
            result, metadata = self._structured_llm.complete_structured(
                model_config=input_data["model_config"],
                api_key=input_data["api_key"],
                system_prompt=self._build_system_prompt(rag_output),
                user_prompt=self._build_user_prompt(text, demand_type, lead_level, rag_output),
                response_model=ScriptGenerateResult,
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
            logger.error("AI script generation failed: %s", exc)
            return NodeResult(
                node_name=self.name,
                success=True,
                output=self._fallback_script(text, demand_type, lead_level),
                error=str(exc),
            )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True

    @staticmethod
    def _build_system_prompt(rag_output: dict) -> str:
        prompt = (
            "你是助贷行业的客户沟通专家。你需要根据潜在线索信息生成个性化的跟进话术。\n\n"
            "话术要求：\n"
            "1. 自然、专业，不生硬推销\n"
            "2. 针对客户具体需求提供解决方案\n"
            "3. 符合行业合规要求，不承诺包下款、不夸大\n"
            "4. 生成 2-3 个不同风格版本（专业/亲和/简洁）\n"
            "5. 标注合规注意事项\n"
        )

        rag_refs = rag_output.get("references", [])
        rag_rules = rag_output.get("rules", [])
        rag_scripts = rag_output.get("top_scripts", [])

        if rag_refs:
            ref_texts = [r.get("content", "")[:200] for r in rag_refs[:3]]
            prompt += f"\n\n参考素材：\n" + "\n---\n".join(ref_texts)

        if rag_rules:
            rule_texts = [r.get("content", "")[:200] for r in rag_rules[:3]]
            prompt += f"\n\n平台规则参考：\n" + "\n---\n".join(rule_texts)

        if rag_scripts:
            script_texts = [r.get("content", "")[:200] for r in rag_scripts[:3]]
            prompt += f"\n\n历史优质话术参考：\n" + "\n---\n".join(script_texts)

        return prompt

    @staticmethod
    def _build_user_prompt(text: str, demand_type: str, lead_level: str, rag_output: dict) -> str:
        return (
            f"请为以下线索生成跟进话术：\n\n"
            f"客户评论：{text}\n"
            f"需求类型：{demand_type}\n"
            f"线索等级：{lead_level}\n"
        )

    @staticmethod
    def _fallback_script(text: str, demand_type: str, lead_level: str) -> dict:
        if lead_level == "A":
            script = f"看到您有{demand_type}的需求，我先帮您看下征信和负债情况，再判断适合信用贷还是抵押类方案。"
        elif lead_level == "B":
            script = f"您关注的{demand_type}方面，可以先补充一下资金用途和期望金额，我再帮您判断可选方案。"
        elif lead_level == "C":
            script = f"关于{demand_type}，可以先看一份办理条件清单，再判断是否适合申请。"
        else:
            script = "暂不建议直接跟进。"

        return ScriptGenerateResult(
            candidates=[ScriptCandidate(
                script_text=script,
                tone="专业",
                key_selling_points=[],
                compliance_notes=[],
            )],
            recommended_index=0,
            rag_sources=[],
            generation_metadata={"fallback": True},
        ).model_dump()
