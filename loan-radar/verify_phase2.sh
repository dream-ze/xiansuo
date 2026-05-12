#!/bin/bash
# Phase 2 验收测试脚本
# 运行所有 Phase 2 相关的验证

echo "=========================================="
echo "Phase 2: 数据去重 + last_crawled_at 验收"
echo "=========================================="
echo ""

cd backend

echo "1️⃣ 检查编译..."
python -m compileall app
if [ $? -eq 0 ]; then
    echo "✅ 编译成功"
else
    echo "❌ 编译失败"
    exit 1
fi
echo ""

echo "2️⃣ 运行错误脱敏测试..."
python -m pytest tests/test_phase2_dedup.py::TestErrorSanitization -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ 错误脱敏测试失败"
    exit 1
fi
echo ""

echo "3️⃣ 运行 Phase 1 回归测试..."
python -m pytest tests/test_collectors_phase1.py tests/test_collectors_api.py tests/test_collector_factory.py -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Phase 1 回归测试失败"
    exit 1
fi
echo ""

echo "4️⃣ 运行 Phase 2 烟雾测试..."
python smoke_test_phase2.py
if [ $? -ne 0 ]; then
    echo "❌ Phase 2 烟雾测试失败"
    exit 1
fi
echo ""

echo "5️⃣ 验证迁移文件..."
if [ -f "alembic/versions/ae33606f820e_phase2_add_dedup_indexes.py" ]; then
    echo "✅ 迁移文件存在"
    echo "   文件: alembic/versions/ae33606f820e_phase2_add_dedup_indexes.py"
    echo "   功能: 添加 posts(platform, post_id) 和 comments(platform, comment_id) 唯一索引"
else
    echo "❌ 迁移文件不存在"
    exit 1
fi
echo ""

echo "=========================================="
echo "✅ Phase 2 验收完成！"
echo "=========================================="
echo ""
echo "📋 Phase 2 总结："
echo "  ✓ 错误信息脱敏（Cookie/Token/Key）"
echo "  ✓ Post 按 platform+post_id 去重"
echo "  ✓ Comment 按 platform+comment_id 去重"
echo "  ✓ 只对新评论生成 leads"
echo "  ✓ 采集成功后更新 last_crawled_at"
echo "  ✓ MonitorSource 模型已支持 last_crawled_at"
echo "  ✓ Post/Comment 模型添加复合唯一约束"
echo "  ✓ 数据库迁移脚本已准备"
echo ""
echo "🚀 下一步: 执行数据库迁移"
echo "  cd backend && alembic upgrade head"
