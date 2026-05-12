"""Phase 1: 采集器 API 路由测试"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestCollectorsAPI:
    """测试 /api/collectors 相关接口"""

    def test_get_collectors_endpoint(self, client):
        """GET /api/collectors 应返回所有采集器能力列表"""
        response = client.get("/api/collectors")
        assert response.status_code == 200
        data = response.json()
        
        assert "collectors" in data
        assert "summary" in data
        
        collectors = data["collectors"]
        assert "mock" in collectors
        assert "playwright" in collectors
        assert "xhs" in collectors
        
        # 检查采集器结构
        mock = collectors["mock"]
        assert "name" in mock
        assert "description" in mock
        assert "status" in mock
        assert "supports" in mock
        assert "config" in mock

    def test_get_collectors_summary(self, client):
        """GET /api/collectors 应包含 ready/implementing/planned 分类"""
        response = client.get("/api/collectors")
        data = response.json()
        summary = data["summary"]
        
        assert "ready" in summary
        assert "implementing" in summary
        assert "planned" in summary
        
        # mock、playwright、xhs 应该是 ready（Phase 5 完成）
        assert "mock" in summary["ready"]
        assert "playwright" in summary["ready"]
        assert "xhs" in summary["ready"]  # Phase 5 完成

        """POST /api/collectors/validate-config 应拒绝未知的 collector_type"""
        config = {
            "collector_type": "unknown_type",
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_config_invalid_external_api_no_endpoint(self, client):
        """POST /api/collectors/validate-config 应验证 external_api 需要 endpoint"""
        config = {
            "collector_type": "external_api",
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_config_valid_external_api(self, client):
        """POST /api/collectors/validate-config 应能验证有效的 external_api 配置"""
        config = {
            "collector_type": "external_api",
            "external_api": {
                "endpoint": "http://example.com/api/collect",
                "api_key_env": "MY_API_KEY",
            },
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True

    def test_validate_config_generic_web_needs_entry_url(self, client):
        """POST /api/collectors/validate-config 应验证 generic_web 需要 entry_url"""
        config = {
            "collector_type": "generic_web",
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False

    def test_validate_config_generic_web_needs_selectors(self, client):
        """POST /api/collectors/validate-config 应验证 generic_web 需要 selectors"""
        config = {
            "collector_type": "generic_web",
            "entry_url": "http://example.com",
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False

    def test_validate_config_valid_generic_web(self, client):
        """POST /api/collectors/validate-config 应能验证有效的 generic_web 配置"""
        config = {
            "collector_type": "generic_web",
            "entry_url": "http://example.com",
            "selectors": {
                "title": "h1",
                "content": "article",
            },
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True

    def test_validate_config_xhs_needs_cookies(self, client):
        """POST /api/collectors/validate-config 应验证 xhs 需要 cookies"""
        config = {
            "collector_type": "xhs",
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False

    def test_validate_config_valid_xhs(self, client):
        """POST /api/collectors/validate-config 应能验证有效的 xhs 配置"""
        config = {
            "collector_type": "xhs",
            "cookies": "test_cookie_value",
            "max_posts": 20,
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True

    def test_validate_config_warning_for_implementing(self, client):
        """POST /api/collectors/validate-config 应为实现中的采集器给出警告"""
        config = {
            "collector_type": "douyin",  # 改为 douyin（仍在规划中）
            "cookies": "test_cookie",
        }
        response = client.post("/api/collectors/validate-config", json=config)
        assert response.status_code == 200
        data = response.json()

        # douyin 虽然配置有效，但状态是 planned，应该有警告
        """GET /api/collectors/health 应返回采集器模块健康状态"""
        response = client.get("/api/collectors/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "ready_collectors" in data
        assert "total_collectors" in data
        assert data["ready_collectors"] > 0
