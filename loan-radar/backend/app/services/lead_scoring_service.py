from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.services.rule_scoring_service import load_scoring_rules, score_with_rules

logger = logging.getLogger(__name__)


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
    def __init__(self) -> None:
        self._rules = load_scoring_rules()
        logger.debug("LeadScoringService initialized with rules v%s", self._rules.version)

    def score(self, text: str) -> LeadScoringResult:
        result = score_with_rules(text, self._rules)
        return LeadScoringResult(
            lead_level=result["lead_level"],
            lead_score=result["lead_score"],
            demand_type=result["demand_type"],
            risk_level=result["risk_level"],
            evidence=result["evidence"],
            reason=result["reason"],
            follow_up_script=result["follow_up_script"],
            is_suspected_demand=result["is_suspected_demand"],
        )

    def reload_rules(self) -> None:
        self._rules = load_scoring_rules()
        logger.info("LeadScoringService rules reloaded (v%s)", self._rules.version)
