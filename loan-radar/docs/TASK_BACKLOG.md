# 助贷线索雷达开发任务清单

## P0 已完成主链路

- [x] 项目骨架和基础文档
- [x] 数据库模型和 Alembic 迁移
- [x] Pydantic Schemas
- [x] 监控源 CRUD
- [x] MockCollector（代码存在，Factory 已不路由）
- [x] 线索识别规则引擎
- [x] 触发采集完整链路
- [x] 线索查询和 CSV 导出
- [x] 今日报告生成
- [x] 同行账号发现池后端和前端页面
- [x] 前端基础页面：监控源、采集任务、帖子池、评论池、线索池、今日报告
- [x] MediaCrawler 多平台采集器（替代 Mock/Playwright/ExternalApi/GenericWeb）
- [x] 采集任务创建与运行接口（/api/collection/tasks）
- [x] 帖子/评论去重（platform + post_id / comment_id）
- [x] 采集后更新 monitor_sources.last_crawled_at
- [x] 错误信息脱敏
- [x] 线索追踪到帖子双向导航
- [x] 前端导航精简与全局优化
- [x] API.md 补全缺失接口和字段文档
- [x] DB_DESIGN.md 补充 crawl_tasks 新增字段和平台枚举说明

## P1 已完成：MVP 产品化增强

- [x] 前端 MonitorSourcesPage 默认 collector_type 改为 media_crawler
- [x] 前端移除不可用的 playwright/external_api/generic_web/mock 选项
- [x] 前端平台选项仅展示 xhs/douyin/zhihu
- [x] 创建监控源时增加 MediaCrawler API 依赖提示
- [x] 后端创建监控源时校验平台与 collector_type 兼容性（media_crawler 仅允许 xhs/douyin/zhihu）
- [x] PendingCompetitorsPage 挂载路由，导航栏增加"同行发现"
- [x] 线索状态流转增强：new → contacted → interested → invalid/converted
- [x] 线索增加备注字段（notes）
- [x] 线索表格增加备注输入列
- [x] CSV 导出增加备注列
- [x] 今日报告增强：A级线索详情、典型证据、建议跟进话术、发现的同行账号、明日建议
- [x] 前端日报页面展示新增板块
- [x] MediaCrawler Smoke Test（media_crawler_smoke_test.py）
- [x] 数据库迁移：leads.notes + daily_reports 新增字段
- [x] PRD/DEMO_FLOW/TASK_BACKLOG/README 更新

## P2 下一步：稳定性与清理

- [ ] 评估旧采集器代码（MockCollector/PlaywrightCollector/ExternalApiCollector/GenericWebCollector）是否删除或归档
- [ ] 删除 HomePage.tsx 死代码
- [ ] 归档历史文档（PHASE3/4/5_ACCEPTANCE、REAL_COLLECTION_PLAN 等）
- [ ] 增加真实采集测试页面或本地 HTML fixture
- [ ] smoke_test 新增 pending competitors 审核步骤
- [ ] CODEX_TASK_RULES.md 审核并更新过时规则
- [ ] 线索详情弹窗展示完整证据链（命中关键词、金额、判断理由）
- [ ] 线索批量操作（批量标记状态、批量导出）
- [ ] 日报 PDF 导出

## P3 后续：扩展能力

- [ ] 恢复 MockCollector 到 Factory 路由（保证无 MediaCrawler 服务时演示可跑）
- [ ] 扩展 MediaCrawler 支持更多平台（快手、B站、微博、贴吧）
- [ ] 定义外部采集 API 标准协议
- [ ] 实现 ExternalApiCollector（恢复 Factory 路由）
- [ ] 支持 `endpoint`、`api_key_env`、`timeout`、`retry`
- [ ] 前端支持 external_api 配置
- [ ] 测试 API Key 不泄漏
- [ ] 定时采集调度
- [ ] 异步采集队列
- [ ] 线索自动分配和跟进提醒
- [ ] 多租户和基础权限

## 暂缓

- [ ] CRM
- [ ] 员工管理
- [ ] 复杂权限
- [ ] 自动发布
- [ ] 登录态采集
- [ ] 验证码处理
- [ ] 代理池 / Cookie 池
- [ ] 真实平台关键词批量搜索
- [ ] 复杂智能体编排
