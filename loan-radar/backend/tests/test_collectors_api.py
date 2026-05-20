import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.login_session import LoginSession
from app.models.user import User


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    db = SessionLocal()
    db.execute(delete(LoginSession))
    db.execute(delete(User))
    db.commit()
    user = User(username="testuser", password_hash=hash_password("testpass123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    db.close()
    return {"Authorization": f"Bearer {token}"}


class TestCollectorsAPI:
    def test_get_collectors_endpoint(self, client, auth_headers):
        response = client.get("/api/collectors", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert "collectors" in data
        assert "summary" in data

        collectors = data["collectors"]
        assert "media_crawler" in collectors
        assert "xhs" not in collectors

        mc = collectors["media_crawler"]
        assert "name" in mc
        assert "description" in mc
        assert "status" in mc
        assert "supports" in mc
        assert "config" in mc

    def test_get_collectors_summary(self, client, auth_headers):
        response = client.get("/api/collectors", headers=auth_headers)
        data = response.json()
        summary = data["summary"]

        assert "ready" in summary
        assert "implementing" in summary
        assert "planned" in summary

        assert "media_crawler" in summary["ready"]
        assert "xhs" not in summary["ready"]

    def test_validate_config_rejects_unknown_type(self, client, auth_headers):
        config = {
            "collector_type": "unknown_type",
        }
        response = client.post("/api/collectors/validate-config", json=config, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_config_rejects_xhs_type(self, client, auth_headers):
        config = {
            "collector_type": "xhs",
        }
        response = client.post("/api/collectors/validate-config", json=config, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False

    def test_validate_config_valid_media_crawler(self, client, auth_headers):
        config = {
            "collector_type": "media_crawler",
            "login_type": "qrcode",
            "max_posts": 20,
        }
        response = client.post("/api/collectors/validate-config", json=config, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True

    def test_validate_config_valid_media_crawler_with_cookies(self, client, auth_headers):
        config = {
            "collector_type": "media_crawler",
            "login_type": "cookie",
            "cookies": "test_cookie_value",
            "max_posts": 20,
        }
        response = client.post("/api/collectors/validate-config", json=config, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True

    def test_validate_config_masks_sensitive_fields(self, client, auth_headers):
        config = {
            "collector_type": "media_crawler",
            "cookies": "sessionid=super_secret_cookie",
            "external_api": {
                "endpoint": "https://example.com/collect",
                "api_key": "sk-super-secret",
            },
            "user_token": "my-very-secret-token",
        }
        response = client.post("/api/collectors/validate-config", json=config, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert data["config"]["cookies"] == "se***ie"
        assert data["config"]["external_api"]["api_key"] == "sk***et"
        assert data["config"]["user_token"] == "my***en"

    def test_collectors_health(self, client, auth_headers):
        response = client.get("/api/collectors/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "ready_collectors" in data
        assert "total_collectors" in data
        assert data["ready_collectors"] > 0
