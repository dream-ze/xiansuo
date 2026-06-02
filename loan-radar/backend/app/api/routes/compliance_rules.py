from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.models import ComplianceRule, User
from app.schemas.common import paginated
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/compliance-rules", tags=["compliance-rules"])


class ComplianceRuleCreate(BaseModel):
    category: str = Field(max_length=64)
    rule_text: str = Field(min_length=1, max_length=2000)
    rule_description: str | None = None
    severity: str = Field(default="medium", max_length=16)


class ComplianceRuleUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=64)
    rule_text: str | None = Field(default=None, max_length=2000)
    rule_description: str | None = None
    severity: str | None = Field(default=None, max_length=16)
    is_active: bool | None = None


@router.get("")
def list_compliance_rules(
    category: str | None = None,
    severity: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    statement = select(ComplianceRule).where(ComplianceRule.user_id == current_user.id)
    if category:
        statement = statement.where(ComplianceRule.category == category)
    if severity:
        statement = statement.where(ComplianceRule.severity == severity)
    if is_active is not None:
        statement = statement.where(ComplianceRule.is_active == is_active)

    rules = db.scalars(
        statement.order_by(ComplianceRule.created_at.desc(), ComplianceRule.id.desc())
    ).all()

    return paginated([
        {
            "id": r.id,
            "category": r.category,
            "rule_text": r.rule_text,
            "rule_description": r.rule_description,
            "severity": r.severity,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rules
    ], page, page_size)


@router.post("")
def create_compliance_rule(
    payload: ComplianceRuleCreate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    rule = ComplianceRule(
        user_id=current_user.id,
        category=payload.category,
        rule_text=payload.rule_text,
        rule_description=payload.rule_description,
        severity=payload.severity,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return success_response({
        "id": rule.id,
        "category": rule.category,
        "rule_text": rule.rule_text,
        "severity": rule.severity,
    })


@router.patch("/{rule_id}")
def update_compliance_rule(
    rule_id: int,
    payload: ComplianceRuleUpdate,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    rule = db.scalar(
        select(ComplianceRule).where(
            ComplianceRule.id == rule_id,
            ComplianceRule.user_id == current_user.id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则未找到")

    if payload.category is not None:
        rule.category = payload.category
    if payload.rule_text is not None:
        rule.rule_text = payload.rule_text
    if payload.rule_description is not None:
        rule.rule_description = payload.rule_description
    if payload.severity is not None:
        rule.severity = payload.severity
    if payload.is_active is not None:
        rule.is_active = payload.is_active

    db.commit()
    db.refresh(rule)

    return success_response({
        "id": rule.id,
        "category": rule.category,
        "rule_text": rule.rule_text,
        "severity": rule.severity,
        "is_active": rule.is_active,
    })


@router.delete("/{rule_id}")
def delete_compliance_rule(
    rule_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    rule = db.scalar(
        select(ComplianceRule).where(
            ComplianceRule.id == rule_id,
            ComplianceRule.user_id == current_user.id,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则未找到")

    db.delete(rule)
    db.commit()
    return success_response({"id": rule_id, "status": "deleted"})


@router.post("/seed-defaults")
def seed_default_rules(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(ComplianceRule).where(ComplianceRule.user_id == current_user.id)
    )
    if existing is not None:
        return success_response({"message": "已有规则，跳过初始化"})

    defaults = [
        ("platform_rule", "不得承诺包下款、百分百通过等绝对化表述", "小红书社区规范", "critical"),
        ("platform_rule", "不得包含微信号、二维码等站外引流信息", "小红书社区规范", "high"),
        ("platform_rule", "不得使用夸张标题党吸引点击", "小红书社区规范", "medium"),
        ("industry_regulation", "不得暗示内部渠道、特殊通道办理贷款", "金融营销规范", "high"),
        ("industry_regulation", "不得宣传零利息、免息等不实利率信息", "金融营销规范", "critical"),
        ("industry_regulation", "不得引导黑户包装、刷流水等违规操作", "金融营销规范", "critical"),
        ("internal_policy", "话术中应包含风险提示", "内部合规策略", "medium"),
        ("internal_policy", "不得直接报价利率，应引导线下咨询", "内部合规策略", "medium"),
        ("internal_policy", "首次接触不应过度推销，以咨询为主", "内部合规策略", "low"),
    ]

    for category, rule_text, description, severity in defaults:
        db.add(ComplianceRule(
            user_id=current_user.id,
            category=category,
            rule_text=rule_text,
            rule_description=description,
            severity=severity,
        ))

    db.commit()
    return success_response({"created_count": len(defaults)})
