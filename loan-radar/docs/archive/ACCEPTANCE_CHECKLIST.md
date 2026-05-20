# 交付验收清单

> 版本：MVP 试用版 | 最后更新：2026-05

使用本清单逐项验证系统功能，每项标记 PASS 或 FAIL。全部 PASS 视为验收通过。

---

## 1. 后端健康检查

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 后端启动 | 访问 `http://localhost:8001/health` | 返回 `{"status": "ok"}` | ☐ PASS / FAIL |

```bash
curl http://localhost:8001/health
```

---

## 2. 前端启动检查

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 前端加载 | 浏览器访问 `http://localhost:5173` | 首页加载成功，显示获客驾驶舱 | ☐ PASS / FAIL |
| 首页指标 | 查看驾驶舱 7 项核心指标 | 监控源、任务、帖子、评论、线索、A级线索、待审核同行均有数值 | ☐ PASS / FAIL |

---

## 3. 数据库迁移检查

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 迁移完成 | 执行 `alembic upgrade head` | 无报错，输出 "Running upgrade" 或 "Already up to date" | ☐ PASS / FAIL |
| 表结构 | 查询数据库表列表 | 包含 crawl_tasks、posts、comments、leads、monitor_sources、pending_competitor_accounts、daily_reports 表 | ☐ PASS / FAIL |

```bash
cd backend
alembic upgrade head
```

---

## 4. MediaCrawler 健康检查

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 健康接口 | 访问 `/api/monitor-sources/media-crawler/health` | 返回 `status: "ok"` | ☐ PASS / FAIL |
| 首页告警 | MediaCrawler 未启动时查看首页 | 显示黄色告警条"MediaCrawler 不在线" | ☐ PASS / FAIL |

```bash
curl http://localhost:8001/api/monitor-sources/media-crawler/health
```

> 如使用演示模式，此项可跳过，在"Demo 模式兜底"中验证。

---

## 5. 创建监控源

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 创建关键词监控源 | 填写名称、平台、关键词，点击创建 | 创建成功，列表显示新监控源 | ☐ PASS / FAIL |
| 创建同行账号监控源 | 填写账号 URL，点击创建 | 创建成功 | ☐ PASS / FAIL |
| 启用/禁用 | 点击监控源启用/禁用开关 | 状态切换正常 | ☐ PASS / FAIL |

---

## 6. 触发采集

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 手动采集 | 点击"立即采集" | 任务创建成功，状态变为"运行中"或"排队中" | ☐ PASS / FAIL |
| 任务完成 | 等待采集完成 | 任务状态变为"成功"，帖子数/评论数/线索数 > 0 | ☐ PASS / FAIL |
| 任务详情 | 点击"详情"按钮 | 弹窗显示基础信息、采集配置、结果统计 | ☐ PASS / FAIL |
| 失败重试 | 如有失败任务，点击"重试" | 任务重新执行 | ☐ PASS / FAIL |
| 运行中状态 | 查看运行中任务详情 | 弹窗显示 spinner 和进度信息 | ☐ PASS / FAIL |
| 成功快捷入口 | 查看成功任务详情 | 弹窗显示"查看帖子/评论/线索/生成日报"快捷按钮 | ☐ PASS / FAIL |

---

## 7. 查看帖子池

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 帖子列表 | 进入帖子池页面 | 显示采集到的帖子列表 | ☐ PASS / FAIL |
| 帖子详情 | 查看帖子内容、作者、互动数据 | 信息完整展示 | ☐ PASS / FAIL |

---

## 8. 查看评论池

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 评论列表 | 进入评论池页面 | 显示采集到的评论列表 | ☐ PASS / FAIL |
| 需求标记 | 查看评论的 `is_suspected_demand` 标记 | 需求类评论有标记 | ☐ PASS / FAIL |

---

## 9. 查看线索池

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 线索列表 | 进入线索池页面 | 显示识别出的线索列表 | ☐ PASS / FAIL |
| 线索等级 | 查看线索 A/B/C/D 等级 | 等级标注正确 | ☐ PASS / FAIL |
| 线索详情 | 查看线索评分、证据、跟进话术 | 信息完整展示 | ☐ PASS / FAIL |
| 去重筛选 | 切换"只看非重复/查看重复"筛选 | 筛选结果正确 | ☐ PASS / FAIL |

---

## 10. 修改线索状态

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 状态流转 | 将线索从"新线索"改为"已跟进" | 状态更新成功 | ☐ PASS / FAIL |
| 添加备注 | 在线索上添加备注文字 | 备注保存成功，刷新后仍在 | ☐ PASS / FAIL |

---

## 11. 导出 CSV

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| CSV 下载 | 点击"导出 CSV"按钮 | 浏览器下载 CSV 文件 | ☐ PASS / FAIL |
| CSV 内容 | 打开 CSV 文件 | 包含线索数据列和重复标记列 | ☐ PASS / FAIL |

---

## 12. 生成今日报告

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 生成报告 | 点击"生成今日报告" | 报告生成成功 | ☐ PASS / FAIL |
| 报告内容 | 查看报告六大板块 | 扫描概况、A级线索、典型证据、同行发现、明日建议、合规提醒均有内容 | ☐ PASS / FAIL |
| 空数据 | 无数据时生成报告 | 不报错，显示友好提示（如"今日暂无A级线索"） | ☐ PASS / FAIL |
| 复制摘要 | 点击"复制摘要" | 剪贴板包含纯文本版报告 | ☐ PASS / FAIL |
| 导出 Markdown | 点击"导出报告" | 下载 `.md` 文件，内容客户可读 | ☐ PASS / FAIL |
| 平台筛选 | 切换平台筛选 | 报告数据按平台过滤 | ☐ PASS / FAIL |

---

## 13. 查看同行发现

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 同行列表 | 进入同行发现页面 | 显示待审核同行账号 | ☐ PASS / FAIL |
| 审核通过 | 点击"通过" | 同行账号变为已通过，自动创建监控源 | ☐ PASS / FAIL |
| 忽略 | 点击"忽略" | 同行账号变为已忽略 | ☐ PASS / FAIL |

---

## 14. Demo 模式兜底

> 当 MediaCrawler 不可用时，使用演示模式验证完整链路。

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| 启用演示模式 | 设置 `ENABLE_MOCK_COLLECTOR=true` 启动后端 | 后端正常启动 | ☐ PASS / FAIL |
| 生成演示数据 | 运行 `python scripts/seed_demo_data.py` | 脚本执行成功，无报错 | ☐ PASS / FAIL |
| 数据完整性 | 查看帖子池、评论池、线索池 | 各页面有演示数据 | ☐ PASS / FAIL |
| 数据标记 | 查看演示数据的 `raw_data.demo` 字段 | 值为 `true` | ☐ PASS / FAIL |
| 首页驾驶舱 | 查看首页指标 | 核心指标有数值，MediaCrawler 离线告警显示 | ☐ PASS / FAIL |

---

## 15. Smoke Test PASS

| 检查项 | 操作 | 期望结果 | 状态 |
|--------|------|----------|------|
| Demo 模式 Smoke | `SMOKE_MODE=demo python scripts/media_crawler_smoke_test.py` | 所有步骤 PASS | ☐ PASS / FAIL |
| Real 模式 Smoke | `SMOKE_MODE=real python scripts/media_crawler_smoke_test.py` | 所有步骤 PASS | ☐ PASS / FAIL |

```powershell
# Demo 模式
$env:SMOKE_MODE = "demo"
python backend/scripts/media_crawler_smoke_test.py

# Real 模式（需 MediaCrawler 在线）
$env:SMOKE_MODE = "real"
python backend/scripts/media_crawler_smoke_test.py
```

验收结果输出到 `reports/smoke_test_result.json`。

---

## 验收结论

| 项目 | 结果 |
|------|------|
| 验收日期 | |
| 验收人 | |
| 通过项数 | / 15 |
| 失败项数 | |
| 总体结论 | ☐ 通过 / ☐ 不通过 |
| 备注 | |
