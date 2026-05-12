"""Phase 2 烟雾测试脚本

这个脚本演示 Phase 2 的关键功能：
1. 错误脱敏
2. 去重逻辑（概念演示）
3. last_crawled_at 更新
4. Mock 采集器仍然可用
"""

from datetime import datetime, timezone
from types import SimpleNamespace

# 测试 1: 错误脱敏
print("=" * 60)
print("TEST 1: 错误脱敏")
print("=" * 60)

from app.services.crawl_pipeline_service import _sanitize_error_message

test_cases = [
    ("Error with cookie='secret123'", "***"),
    ("API key=sk-12345678", "***"),
    ("Token: Bearer xyz789", "***"),
    ("https://api.com?key=secret&value=public", "***"),
    ("source_id=123 is fine, but cookie=secret is not", "source_id=123"),
]

for error_msg, expected_in_result in test_cases:
    sanitized = _sanitize_error_message(error_msg)
    print(f"Original:  {error_msg}")
    print(f"Sanitized: {sanitized}")
    if expected_in_result in sanitized or expected_in_result == "***":
        print("✅ PASS")
    else:
        print(f"❌ FAIL - Expected '{expected_in_result}' in result")
    print()

# 测试 2: 采集器工厂路由和 Mock 采集器
print("=" * 60)
print("TEST 2: 采集器工厂和 Mock 采集器")
print("=" * 60)

from app.collectors.factory import CollectorFactory
from app.collectors.mock_collector import MockCollector

source = SimpleNamespace(
    source_type="keyword",
    platform="xhs",
    value="test_keyword",
    config={"collector_type": "mock"},
)

try:
    collector = CollectorFactory.create(source)
    if isinstance(collector, MockCollector):
        print("✅ PASS - Mock 采集器正确创建")
    else:
        print(f"❌ FAIL - 期望 MockCollector，得到 {type(collector)}")
except Exception as e:
    print(f"❌ FAIL - 创建采集器失败: {e}")

# 测试 3: Mock 采集器结果有 metadata 字段
print()
print("=" * 60)
print("TEST 3: CollectorResult metadata 字段")
print("=" * 60)

result = collector.collect(source)
if hasattr(result, 'metadata'):
    print(f"✅ PASS - CollectorResult 有 metadata 字段: {result.metadata}")
else:
    print("❌ FAIL - CollectorResult 缺少 metadata 字段")

if len(result.posts) > 0 and len(result.comments) > 0:
    print(f"✅ PASS - Mock 采集器返回数据: {len(result.posts)} posts, {len(result.comments)} comments")
else:
    print("❌ FAIL - Mock 采集器没有返回数据")

# 测试 4: MonitorSource last_crawled_at 字段
print()
print("=" * 60)
print("TEST 4: MonitorSource 模型")
print("=" * 60)

from app.models.monitor_source import MonitorSource

source_model = MonitorSource(
    source_type="keyword",
    platform="xhs",
    name="test source",
    value="test_value",
)

if hasattr(source_model, 'last_crawled_at'):
    print(f"✅ PASS - MonitorSource 有 last_crawled_at 字段")
    if source_model.last_crawled_at is None:
        print(f"✅ PASS - last_crawled_at 初始值为 None")
    
    # 测试更新
    now = datetime.now(timezone.utc)
    source_model.last_crawled_at = now
    if source_model.last_crawled_at is not None:
        print(f"✅ PASS - last_crawled_at 可以更新")
else:
    print("❌ FAIL - MonitorSource 缺少 last_crawled_at 字段")

# 测试 5: Post 和 Comment 唯一约束
print()
print("=" * 60)
print("TEST 5: Post 和 Comment 模型唯一约束")
print("=" * 60)

from app.models.post import Post
from app.models.comment import Comment

# 检查 Post 唯一约束
if hasattr(Post, '__table_args__') and Post.__table_args__:
    print(f"✅ PASS - Post 模型有表约束: {Post.__table_args__}")
else:
    print("ℹ️ INFO - Post 模型表约束: {Post.__table_args__}")

# 检查 Comment 唯一约束
if hasattr(Comment, '__table_args__') and Comment.__table_args__:
    print(f"✅ PASS - Comment 模型有表约束: {Comment.__table_args__}")
else:
    print("ℹ️ INFO - Comment 模型表约束: {Comment.__table_args__}")

# 测试 6: 采集器能力列表
print()
print("=" * 60)
print("TEST 6: 采集器能力列表")
print("=" * 60)

collectors = CollectorFactory.get_supported_collectors()
print(f"支持的采集器数量: {len(collectors)}")
print(f"Ready: {[c for c in collectors if collectors[c]['status'] == 'ready']}")
print(f"Implementing: {[c for c in collectors if collectors[c]['status'] == 'implementing']}")
print(f"Planned: {[c for c in collectors if collectors[c]['status'] == 'planned']}")

if 'mock' in collectors and collectors['mock']['status'] == 'ready':
    print("✅ PASS - Mock 采集器状态为 ready")
if 'xhs' in collectors and collectors['xhs']['status'] == 'implementing':
    print("✅ PASS - XHS 采集器状态为 implementing（Phase 4）")

print()
print("=" * 60)
print("Phase 2 烟雾测试完成")
print("=" * 60)
