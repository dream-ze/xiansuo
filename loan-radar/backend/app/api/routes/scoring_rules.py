from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_current_user

from app.api.routes.monitor_sources import get_db
from app.services.lead_scoring_service import LeadScoringService
from app.services.rule_scoring_service import ScoringRuleSet, load_scoring_rules
from app.utils.response import error_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scoring-rules", tags=["scoring-rules"], dependencies=[Depends(require_current_user)])

_RULES_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "scoring_rules.json"

_scoring_service = LeadScoringService()


class ScoringRulesUpdate(BaseModel):
    rules: dict[str, Any]


class ScoringTestRequest(BaseModel):
    text: str


@router.get("")
def get_scoring_rules():
    rules = load_scoring_rules()
    return success_response(_rules_to_dict(rules))


@router.put("")
def update_scoring_rules(payload: ScoringRulesUpdate):
    try:
        validated = ScoringRuleSet.from_dict(payload.rules)
    except Exception as e:
        return error_response(f"invalid rules format: {e}")

    try:
        _RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(payload.rules, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("failed to save scoring rules")
        return error_response(f"failed to save rules: {e}")

    _scoring_service.reload_rules()
    logger.info("scoring rules updated to v%s", validated.version)
    return success_response(_rules_to_dict(validated))


@router.post("/test")
def test_scoring(payload: ScoringTestRequest):
    result = _scoring_service.score(payload.text)
    return success_response({
        "lead_level": result.lead_level,
        "lead_score": result.lead_score,
        "demand_type": result.demand_type,
        "risk_level": result.risk_level,
        "evidence": result.evidence,
        "reason": result.reason,
        "follow_up_script": result.follow_up_script,
        "is_suspected_demand": result.is_suspected_demand,
    })


@router.post("/batch-test")
def batch_test_scoring(payload: list[ScoringTestRequest], db: Session = Depends(get_db)):
    results = []
    for item in payload[:50]:
        result = _scoring_service.score(item.text)
        results.append({
            "text": item.text[:100],
            "lead_level": result.lead_level,
            "lead_score": result.lead_score,
            "demand_type": result.demand_type,
            "risk_level": result.risk_level,
            "reason": result.reason,
            "is_suspected_demand": result.is_suspected_demand,
        })
    return success_response(results)


@router.post("/reload")
def reload_scoring_rules():
    _scoring_service.reload_rules()
    rules = load_scoring_rules()
    return success_response({"version": rules.version, "message": "rules reloaded"})


def _rules_to_dict(rules: ScoringRuleSet) -> dict[str, Any]:
    return {
        "version": rules.version,
        "dimensions": [
            {
                "name": dim.name,
                "weight": dim.weight,
                "patterns": dim.patterns,
                "score_per_hit": dim.score_per_hit,
                "max_score": dim.max_score,
                "description": dim.description,
            }
            for dim in rules.dimensions
        ],
        "negative_patterns": rules.negative_patterns,
        "negation_patterns": rules.negation_patterns,
        "lead_level_thresholds": rules.lead_level_thresholds,
        "demand_type_rules": rules.demand_type_rules,
        "risk_keywords": rules.risk_keywords,
        "amount_pattern": rules.amount_pattern,
    }
