import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LeadScoringResult:
    lead_level: str
    lead_score: int
    demand_type: str
    risk_level: str
    evidence: dict[str, Any]
    reason: str
    follow_up_script: str
    is_suspected_demand: bool


class LeadScoringService:
    demand_words = [
        "贷款",
        "借款",
        "贷",
        "下款",
        "申请",
        "办理",
        "办",
        "周转",
        "信用贷",
        "房抵贷",
    ]
    urgent_words = ["急用", "马上", "今天", "现在", "尽快", "怎么办", "还不上", "周转"]
    qualification_words = ["征信花", "征信", "负债高", "负债", "网贷太多", "查询多", "公积金断", "房贷", "信用卡"]
    product_words = ["信用贷", "房抵贷", "公积金", "企业", "房贷", "网贷"]
    weak_intent_words = ["了解", "咨询", "一般", "多久", "能办", "能贷", "能申请"]
    risk_words = ["广告", "代理", "同行", "加盟", "引流", "黑户包装", "刷流水", "百分百下款"]

    amount_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(万|w|W|元|块)")

    def score(self, text: str) -> LeadScoringResult:
        normalized_text = self._normalize(text)
        matched_words = self._matched_words(normalized_text)
        amounts = self._matched_amounts(normalized_text)

        demand_score = self._score_demand_clarity(normalized_text, matched_words)
        urgency_score = self._score_urgency(matched_words)
        amount_score = 15 if amounts else 0
        qualification_score = self._score_qualification(matched_words)
        product_score = self._score_product_match(matched_words)
        authenticity_score = self._score_authenticity(normalized_text)
        risk_penalty = self._score_risk(matched_words)

        total_score = max(
            0,
            min(
                100,
                demand_score
                + urgency_score
                + amount_score
                + qualification_score
                + product_score
                + authenticity_score
                + risk_penalty,
            ),
        )

        demand_type = self._demand_type(matched_words, total_score)
        risk_level = self._risk_level(risk_penalty, total_score)
        lead_level = self._lead_level(
            total_score=total_score,
            demand_score=demand_score,
            urgency_score=urgency_score,
            amount_score=amount_score,
            qualification_score=qualification_score,
            risk_level=risk_level,
        )
        is_suspected_demand = lead_level in {"A", "B", "C"}

        return LeadScoringResult(
            lead_level=lead_level,
            lead_score=total_score,
            demand_type=demand_type,
            risk_level=risk_level,
            evidence={
                "matched_words": matched_words,
                "amounts": amounts,
                "score_breakdown": {
                    "demand_clarity": demand_score,
                    "urgency": urgency_score,
                    "amount": amount_score,
                    "qualification": qualification_score,
                    "product_match": product_score,
                    "authenticity": authenticity_score,
                    "risk_penalty": risk_penalty,
                },
            },
            reason=self._reason(lead_level, demand_type, matched_words, amounts),
            follow_up_script=self._follow_up_script(lead_level, demand_type, amounts),
            is_suspected_demand=is_suspected_demand,
        )

    def _normalize(self, text: str) -> str:
        return text.strip().replace(" ", "")

    def _matched_words(self, text: str) -> list[str]:
        words = (
            self.demand_words
            + self.urgent_words
            + self.qualification_words
            + self.product_words
            + self.weak_intent_words
            + self.risk_words
        )
        return list(dict.fromkeys(word for word in words if word in text))

    def _matched_amounts(self, text: str) -> list[str]:
        return [f"{amount}{unit}" for amount, unit in self.amount_pattern.findall(text)]

    def _score_demand_clarity(self, text: str, matched_words: list[str]) -> int:
        score = 0
        if any(word in matched_words for word in self.demand_words):
            score += 20
        if "吗" in text or "怎么办" in text or "能" in text:
            score += 10
        return min(score, 30)

    def _score_urgency(self, matched_words: list[str]) -> int:
        if any(word in matched_words for word in ["急用", "马上", "今天", "现在", "还不上"]):
            return 20
        if any(word in matched_words for word in self.urgent_words):
            return 10
        return 0

    def _score_qualification(self, matched_words: list[str]) -> int:
        if any(word in matched_words for word in self.qualification_words):
            return 15
        return 0

    def _score_product_match(self, matched_words: list[str]) -> int:
        if any(word in matched_words for word in self.product_words):
            return 10
        if any(word in matched_words for word in self.demand_words):
            return 5
        return 0

    def _score_authenticity(self, text: str) -> int:
        if len(text) >= 8 and ("?" in text or "？" in text or "吗" in text or "怎么办" in text):
            return 10
        if len(text) >= 6:
            return 5
        return 0

    def _score_risk(self, matched_words: list[str]) -> int:
        risk_hits = sum(1 for word in self.risk_words if word in matched_words)
        return max(-20, -10 * risk_hits)

    def _demand_type(self, matched_words: list[str], total_score: int) -> str:
        if any(word in matched_words for word in self.risk_words):
            return "无效/风险"
        if any(word in matched_words for word in ["征信花", "征信", "负债高", "负债", "网贷太多", "查询多", "公积金断"]):
            return "资质焦虑"
        if any(word in matched_words for word in ["急用", "周转", "借款", "贷款", "下款"]):
            return "借款需求"
        if any(word in matched_words for word in self.product_words):
            return "产品咨询"
        if total_score >= 30:
            return "弱意向"
        return "无效/风险"

    def _risk_level(self, risk_penalty: int, total_score: int) -> str:
        if risk_penalty <= -20:
            return "high"
        if risk_penalty < 0 or total_score < 40:
            return "medium"
        return "low"

    def _lead_level(
        self,
        total_score: int,
        demand_score: int,
        urgency_score: int,
        amount_score: int,
        qualification_score: int,
        risk_level: str,
    ) -> str:
        if risk_level == "high":
            return "D"
        if (
            total_score >= 80
            and demand_score >= 25
            and (urgency_score > 0 or amount_score > 0 or qualification_score > 0)
        ):
            return "A"
        if total_score >= 55:
            return "B"
        if total_score >= 30:
            return "C"
        return "D"

    def _reason(
        self,
        lead_level: str,
        demand_type: str,
        matched_words: list[str],
        amounts: list[str],
    ) -> str:
        details = "、".join(matched_words[:6]) if matched_words else "无明显需求词"
        amount_text = f"，包含金额信息：{','.join(amounts)}" if amounts else ""
        return f"识别为 {lead_level} 级线索，需求类型为{demand_type}，命中关键词：{details}{amount_text}。"

    def _follow_up_script(self, lead_level: str, demand_type: str, amounts: list[str]) -> str:
        amount_text = f"{amounts[0]}左右" if amounts else "这笔资金"
        if lead_level == "A":
            return f"看你提到{amount_text}需求，我先帮你看下征信、负债和收入情况，再判断适合信用贷还是抵押类方案。"
        if lead_level == "B":
            return "可以先补充一下资金用途、期望金额和当前征信负债情况，我再帮你判断可选方案。"
        if lead_level == "C":
            return f"你关注的是{demand_type}，可以先看一份办理条件清单，再判断是否适合申请。"
        return "这条内容暂不建议直接跟进，可观察是否存在广告、同行或高风险特征。"
