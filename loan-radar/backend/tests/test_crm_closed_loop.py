from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.main import app
from app.models.comment import Comment
from app.models.crm import (
    CrmContract,
    CrmCustomer,
    CrmFollowUpRecord,
    CrmOpportunity,
    CrmReceivable,
    CrmReceivablePlan,
    CrmTask,
)
from app.models.lead import Lead
from app.models.post import Post


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_cleanup():
    session = SessionLocal()
    for model in [
        CrmReceivable,
        CrmReceivablePlan,
        CrmContract,
        CrmTask,
        CrmFollowUpRecord,
        CrmOpportunity,
        CrmCustomer,
        Lead,
        Comment,
        Post,
    ]:
        session.execute(delete(model))
    session.commit()
    yield session
    for model in [
        CrmReceivable,
        CrmReceivablePlan,
        CrmContract,
        CrmTask,
        CrmFollowUpRecord,
        CrmOpportunity,
        CrmCustomer,
        Lead,
        Comment,
        Post,
    ]:
        session.execute(delete(model))
    session.commit()
    session.close()


def _create_lead(session: SessionLocal) -> Lead:
    post = Post(
        platform="xhs",
        source_id=1,
        source_type="keyword",
        post_id="crm-post-1",
        title="征信花了还能贷款吗",
        content="贷款需求讨论",
        post_url="https://example.test/post/1",
    )
    session.add(post)
    session.flush()
    lead = Lead(
        platform="xhs",
        source_id=1,
        source_type="keyword",
        source_post_id=post.id,
        source_comment_id=101,
        user_name="张三",
        user_profile_url="https://example.test/u/zhangsan",
        content="负债高，需要周转 20 万，想找贷款渠道",
        lead_level="A",
        lead_score=86,
        demand_type="贷款周转",
        risk_level="mid",
        evidence={"amounts": ["20万"], "matched_words": ["负债高", "周转"]},
        reason="需求金额明确，有较强贷款意向",
        follow_up_script="先确认用途、收入和征信情况。",
        status="new",
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def test_convert_lead_to_crm_creates_customer_opportunity_and_task(client, db_cleanup):
    lead = _create_lead(db_cleanup)

    response = client.post(
        f"/api/leads/{lead.id}/convert-to-crm",
        json={"owner_name": "销售A", "next_follow_up_at": "2026-05-20T09:30:00+08:00"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["customer"]["name"] == "张三"
    assert payload["customer"]["owner_name"] == "销售A"
    assert payload["customer"]["source_lead_id"] == lead.id
    assert payload["opportunity"]["stage"] == "new_customer"
    assert payload["opportunity"]["estimated_amount"] == 200000
    assert payload["task"]["task_type"] == "follow_up"
    assert payload["task"]["status"] == "pending"


def test_convert_lead_to_crm_rejects_duplicate_conversion(client, db_cleanup):
    lead = _create_lead(db_cleanup)

    first_response = client.post(f"/api/leads/{lead.id}/convert-to-crm", json={})
    second_response = client.post(f"/api/leads/{lead.id}/convert-to-crm", json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert "already converted" in second_response.json()["message"]


def test_list_leads_can_filter_unconverted_for_crm_import(client, db_cleanup):
    open_lead = _create_lead(db_cleanup)
    converted_lead = Lead(
        platform="xhs",
        source_id=2,
        source_type="keyword",
        source_comment_id=202,
        user_name="Converted lead",
        content="Need loan",
        lead_level="B",
        lead_score=62,
        status="converted",
        crm_customer_id=999,
        converted_to_crm_at=datetime.now(timezone.utc),
    )
    db_cleanup.add(converted_lead)
    db_cleanup.commit()

    response = client.get("/api/leads?converted_to_crm=false")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["id"] for item in items] == [open_lead.id]


def test_create_and_update_crm_customer_for_manual_entry(client, db_cleanup):
    create_response = client.post(
        "/api/crm/customers",
        json={
            "name": "Manual customer",
            "phone": "13800000000",
            "owner_name": "Sales A",
            "demand_amount": 300000,
            "loan_purpose": "Business cashflow",
            "customer_level": "A",
            "notes": "Imported by manual entry",
        },
    )

    assert create_response.status_code == 200
    customer = create_response.json()["data"]
    assert customer["name"] == "Manual customer"
    assert customer["status"] == "new"
    assert customer["source_lead_id"] is None

    update_response = client.patch(
        f"/api/crm/customers/{customer['id']}",
        json={"status": "following", "notes": "Call tomorrow morning"},
    )

    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["status"] == "following"
    assert updated["notes"] == "Call tomorrow morning"


def test_crm_tasks_endpoint_marks_overdue_tasks(client, db_cleanup):
    customer = CrmCustomer(name="李四", owner_name="销售B", status="following")
    db_cleanup.add(customer)
    db_cleanup.flush()
    task = CrmTask(
        customer_id=customer.id,
        title="回访客户",
        task_type="follow_up",
        owner_name="销售B",
        due_at=datetime.now(timezone.utc) - timedelta(days=1),
        status="pending",
        priority="high",
    )
    db_cleanup.add(task)
    db_cleanup.commit()

    response = client.get("/api/crm/tasks?owner_name=销售B")

    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["is_overdue"] is True
    assert item["customer_name"] == "李四"


def test_crm_dashboard_tracks_conversion_and_task_metrics(client, db_cleanup):
    lead = _create_lead(db_cleanup)
    client.post(f"/api/leads/{lead.id}/convert-to-crm", json={"owner_name": "销售A"})

    response = client.get("/api/crm/dashboard")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_leads"] == 1
    assert data["converted_leads"] == 1
    assert data["conversion_rate"] == 100.0
    assert data["pending_task_count"] == 1
    assert data["stage_counts"]["new_customer"] == 1
