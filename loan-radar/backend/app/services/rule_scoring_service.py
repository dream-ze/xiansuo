from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RULES_FILE = Path(__file__).resolve().parent.parent / "config" / "scoring_rules.json"


@dataclass
class ScoreDimension:
    name: str
    weight: float
    patterns: list[str]
    score_per_hit: int
    max_score: int
    description: str = ""


@dataclass
class ScoringRuleSet:
    version: str = "1.0"
    dimensions: list[ScoreDimension] = field(default_factory=list)
    negative_patterns: list[str] = field(default_factory=list)
    negation_patterns: list[str] = field(default_factory=list)
    lead_level_thresholds: dict[str, int] = field(default_factory=dict)
    demand_type_rules: list[dict[str, Any]] = field(default_factory=list)
    risk_keywords: list[str] = field(default_factory=list)
    amount_pattern: str = r"(\d+(?:\.\d+)?)\s*(万|w|W|元|块)"

    @classmethod
    def from_dict(cls, data: dict) -> ScoringRuleSet:
        dimensions = []
        for dim_data in data.get("dimensions", []):
            dimensions.append(ScoreDimension(
                name=dim_data["name"],
                weight=dim_data.get("weight", 1.0),
                patterns=dim_data.get("patterns", []),
                score_per_hit=dim_data.get("score_per_hit", 10),
                max_score=dim_data.get("max_score", 30),
                description=dim_data.get("description", ""),
            ))
        return cls(
            version=data.get("version", "1.0"),
            dimensions=dimensions,
            negative_patterns=data.get("negative_patterns", []),
            negation_patterns=data.get("negation_patterns", []),
            lead_level_thresholds=data.get("lead_level_thresholds", {}),
            demand_type_rules=data.get("demand_type_rules", []),
            risk_keywords=data.get("risk_keywords", []),
            amount_pattern=data.get("amount_pattern", r"(\d+(?:\.\d+)?)\s*(万|w|W|元|块)"),
        )


def load_scoring_rules() -> ScoringRuleSet:
    if _RULES_FILE.exists():
        try:
            with open(_RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("loaded scoring rules from %s", _RULES_FILE)
            return ScoringRuleSet.from_dict(data)
        except Exception:
            logger.exception("failed to load scoring rules, using defaults")
    return _default_rules()


def _default_rules() -> ScoringRuleSet:
    return ScoringRuleSet(
        version="1.0",
        dimensions=[
            ScoreDimension(
                name="demand_clarity",
                weight=1.0,
                patterns=["贷款", "借款", "贷", "下款", "申请", "办理", "办", "周转", "信用贷", "房抵贷"],
                score_per_hit=10,
                max_score=30,
                description="需求明确度",
            ),
            ScoreDimension(
                name="urgency",
                weight=1.0,
                patterns=["急用", "马上", "今天", "现在", "尽快", "怎么办", "还不上", "周转"],
                score_per_hit=10,
                max_score=20,
                description="紧迫程度",
            ),
            ScoreDimension(
                name="qualification",
                weight=1.0,
                patterns=["征信花", "征信", "负债高", "负债", "网贷太多", "查询多", "公积金断", "房贷", "信用卡"],
                score_per_hit=10,
                max_score=15,
                description="资质条件",
            ),
            ScoreDimension(
                name="product_match",
                weight=1.0,
                patterns=["信用贷", "房抵贷", "公积金", "企业", "房贷", "网贷"],
                score_per_hit=10,
                max_score=10,
                description="产品匹配",
            ),
            ScoreDimension(
                name="weak_intent",
                weight=0.5,
                patterns=["了解", "咨询", "一般", "多久", "能办", "能贷", "能申请"],
                score_per_hit=5,
                max_score=10,
                description="弱意向信号",
            ),
        ],
        negative_patterns=["广告", "代理", "同行", "加盟", "引流"],
        negation_patterns=["不要", "不用", "不需要", "不想", "别给我", "拒绝", "已经还清", "已还清"],
        lead_level_thresholds={"A": 80, "B": 55, "C": 30, "D": 0},
        demand_type_rules=[
            {"keywords": ["征信花", "征信", "负债高", "负债", "网贷太多", "查询多", "公积金断"], "type": "资质焦虑"},
            {"keywords": ["急用", "周转", "借款", "贷款", "下款"], "type": "借款需求"},
            {"keywords": ["信用贷", "房抵贷", "公积金", "企业", "房贷", "网贷"], "type": "产品咨询"},
        ],
        risk_keywords=["黑户包装", "刷流水", "百分百下款", "包下款"],
        amount_pattern=r"(\d+(?:\.\d+)?)\s*(万|w|W|元|块)",
    )


def score_with_rules(text: str, rules: ScoringRuleSet) -> dict[str, Any]:
    normalized = text.strip().replace(" ", "")
    if not normalized:
        return _empty_result()

    is_negated = any(neg in normalized for neg in rules.negation_patterns)

    dimension_scores: dict[str, int] = {}
    matched_by_dimension: dict[str, list[str]] = {}
    all_matched: list[str] = []

    for dim in rules.dimensions:
        hits = [p for p in dim.patterns if p in normalized]
        matched_by_dimension[dim.name] = hits
        all_matched.extend(hits)

        raw_score = len(hits) * dim.score_per_hit
        weighted = int(raw_score * dim.weight)
        dimension_scores[dim.name] = min(weighted, dim.max_score)

    if is_negated:
        for dim_name in dimension_scores:
            if dim_name in ("demand_clarity", "urgency", "product_match"):
                dimension_scores[dim_name] = dimension_scores[dim_name] // 2

    amount_matches = re.findall(rules.amount_pattern, normalized)
    amount_score = 15 if amount_matches else 0
    dimension_scores["amount"] = amount_score

    authenticity_score = _score_authenticity(normalized)
    dimension_scores["authenticity"] = authenticity_score

    risk_hits = [kw for kw in rules.risk_keywords if kw in normalized]
    risk_penalty = max(-20, -10 * len(risk_hits))
    dimension_scores["risk_penalty"] = risk_penalty

    negative_hits = [kw for kw in rules.negative_patterns if kw in normalized]
    if negative_hits:
        dimension_scores["risk_penalty"] = min(dimension_scores.get("risk_penalty", 0), -10)

    total_score = max(0, min(100, sum(dimension_scores.values())))

    lead_level = _compute_lead_level(total_score, dimension_scores, risk_penalty, rules)
    demand_type = _compute_demand_type(all_matched, total_score, risk_hits, negative_hits, rules)
    risk_level = _compute_risk_level(risk_penalty, negative_hits, total_score)
    is_suspected_demand = lead_level in {"A", "B", "C"}

    amounts = [f"{amt}{unit}" for amt, unit in amount_matches]
    reason = _build_reason(lead_level, demand_type, all_matched, amounts, is_negated)
    follow_up = _build_follow_up(lead_level, demand_type, amounts)

    return {
        "lead_level": lead_level,
        "lead_score": total_score,
        "demand_type": demand_type,
        "risk_level": risk_level,
        "evidence": {
            "matched_words": list(dict.fromkeys(all_matched)),
            "amounts": amounts,
            "negation_detected": is_negated,
            "negation_words": [n for n in rules.negation_patterns if n in normalized],
            "risk_keywords_matched": risk_hits,
            "negative_keywords_matched": negative_hits,
            "score_breakdown": dimension_scores,
        },
        "reason": reason,
        "follow_up_script": follow_up,
        "is_suspected_demand": is_suspected_demand,
    }


def _score_authenticity(text: str) -> int:
    if len(text) >= 8 and ("?" in text or "？" in text or "吗" in text or "怎么办" in text):
        return 10
    if len(text) >= 6:
        return 5
    return 0


def _compute_lead_level(total_score: int, dimension_scores: dict, risk_penalty: int, rules: ScoringRuleSet) -> str:
    thresholds = rules.lead_level_thresholds
    if not thresholds:
        thresholds = {"A": 80, "B": 55, "C": 30, "D": 0}

    if risk_penalty <= -20 or (dimension_scores.get("risk_penalty", 0) <= -10 and total_score < 40):
        return "D"
    if total_score >= thresholds.get("A", 80):
        demand = dimension_scores.get("demand_clarity", 0)
        if demand >= 20:
            return "A"
        return "B"
    if total_score >= thresholds.get("B", 55):
        return "B"
    if total_score >= thresholds.get("C", 30):
        return "C"
    return "D"


def _compute_demand_type(
    matched: list[str],
    total_score: int,
    risk_hits: list[str],
    negative_hits: list[str],
    rules: ScoringRuleSet,
) -> str:
    if risk_hits or negative_hits:
        return "无效/风险"
    for rule in rules.demand_type_rules:
        if any(kw in matched for kw in rule.get("keywords", [])):
            return rule.get("type", "未知")
    if total_score >= 30:
        return "弱意向"
    return "无效/风险"


def _compute_risk_level(risk_penalty: int, negative_hits: list[str], total_score: int) -> str:
    if risk_penalty <= -20 or len(negative_hits) >= 2:
        return "high"
    if risk_penalty < 0 or negative_hits or total_score < 40:
        return "medium"
    return "low"


def _build_reason(lead_level: str, demand_type: str, matched: list[str], amounts: list[str], is_negated: bool) -> str:
    details = "、".join(matched[:6]) if matched else "无明显需求词"
    amount_text = f"，包含金额信息：{','.join(amounts)}" if amounts else ""
    negation_text = "（检测到否定词，评分已降低）" if is_negated else ""
    return f"识别为 {lead_level} 级线索，需求类型为{demand_type}，命中关键词：{details}{amount_text}{negation_text}。"


def _build_follow_up(lead_level: str, demand_type: str, amounts: list[str]) -> str:
    amount_text = f"{amounts[0]}左右" if amounts else "这笔资金"
    if lead_level == "A":
        return f"看你提到{amount_text}需求，我先帮你看下征信、负债和收入情况，再判断适合信用贷还是抵押类方案。"
    if lead_level == "B":
        return "可以先补充一下资金用途、期望金额和当前征信负债情况，我再帮你判断可选方案。"
    if lead_level == "C":
        return f"你关注的是{demand_type}，可以先看一份办理条件清单，再判断是否适合申请。"
    return "这条内容暂不建议直接跟进，可观察是否存在广告、同行或高风险特征。"


def _empty_result() -> dict[str, Any]:
    return {
        "lead_level": "D",
        "lead_score": 0,
        "demand_type": "无效/风险",
        "risk_level": "high",
        "evidence": {"matched_words": [], "amounts": [], "negation_detected": False, "score_breakdown": {}},
        "reason": "内容为空，无法评分。",
        "follow_up_script": "",
        "is_suspected_demand": False,
    }
