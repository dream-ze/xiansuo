# 智获客开发任务清单

## P0 已完成主链路（线索雷达）

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
- [x] 帖子/评论去重（platform + post_id / comment_id 唯一约束）
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

## P2 已完成：CRM 与采集增强

- [x] 轻 CRM 跟进台后端（crm_customers / crm_follow_records 模型、API）
- [x] CRM 仪表板（统计概览、跟进提醒：已逾期/今日/明日/本周）
- [x] 线索转客户（两种入口：CRM 页面 / 线索页面）
- [x] 手动录入客户
- [x] 客户状态管理（7 种状态：pending/contacted/interested/wechat_added/applied/converted/invalid）
- [x] 跟进记录管理（5 种跟进类型：phone/wechat/message/visit/other）
- [x] 跟进时间提醒（前端按 overdue/today/tomorrow/this_week/none 过滤）
- [x] CRM 前端页面（CrmFollowUpPage.tsx）
- [x] 采集时间范围过滤（config.time_range: 7d/15d/30d/90d）
- [x] 设置 time_range 时自动提升 max_posts 至 80
- [x] 入库前按 publish_time 过滤帖子和评论
- [x] 前端 CollectionPage 新增时间范围选择器和列表列
- [x] 定时采集调度（Cron 表达式配置，APScheduler）
- [x] 评分规则管理（可视化编辑、单条/批量测试、热重载）
- [x] 仪表板（全局统计概览、今日/昨日对比、CRM 跟进提醒、MediaCrawler 健康状态）
- [x] 采集任务队列管理（CrawlTaskQueue，同一时间仅执行一个任务）
- [x] 失败类型分类（8 种 FailureType，前端展示中文标签和处理建议）
- [x] 线索转 CRM 接口（POST /api/leads/{lead_id}/convert-to-crm）
- [x] 线索新增 crm_customer_id / converted_to_crm_at 字段
- [x] 线索列表新增 converted_to_crm / created_after 查询参数
- [x] 日报新增 a_lead_details / typical_evidence / discovered_competitors / tomorrow_suggestions / crm_stats 字段
- [x] 日报 Markdown 导出（GET /api/daily-reports/today/export）
- [x] 数据库迁移：crm_customers / crm_follow_records / leads CRM 字段 / daily_reports 新增字段

## P3 已完成：小红书运营模块

- [x] 用户认证系统（注册/登录/JWT 双 Token/密码 PBKDF2 加密）
- [x] 平台账号管理（PC/创作者端双类型，Cookie 导入/QR 码登录/手机验证码登录）
- [x] Cookie 安全存储（Fernet 加密，版本管理，PC 自动同步创作者端）
- [x] 登录会话管理（QR 码/手机验证码中间态）
- [x] 笔记管理（批量保存/详情/素材/评论/标签关联/导出）
- [x] AI 内容创作（改写/生成/标题/标签/润色/封面图/图片生成/图片描述）
- [x] 草稿管理（创建/编辑/发送至发布中心）
- [x] 发布中心（创建/更新/执行发布/素材上传/状态跟踪）
- [x] 图片工坊（上传/合成封面图/缩放裁剪）
- [x] 视频工坊（上传/ffmpeg 截取封面帧/AI 视频描述）
- [x] 关键词组管理（分组/多平台支持/去重）
- [x] 标签系统（CRUD/颜色自定义/笔记-标签多对多）
- [x] 模型配置（AI 模型管理/API Key 加密/默认模型切换）
- [x] 通知系统（站内通知/未读计数/级别分类/标记已读）
- [x] 任务中心（统一任务管理/子任务/调度器状态）
- [x] XHS 数据洞察（运营总览/热门内容/热门话题/评论分析/竞品对标）
- [x] XHS 自动运营（自动发布任务/关键词驱动/手动/定时/周期调度）
- [x] XHS 监控（监控目标 CRUD/刷新/快照）
- [x] 文件管理（上传/下载/图片合成/缩放裁剪/用户隔离）
- [x] API 日志（关键 API 调用日志/请求响应/耗时）
- [x] 数据库迁移：XHS 运营模块全部表（17 个新迁移版本）
- [x] 前端 XHS 运营页面（12 个页面：运营总览/账号矩阵/笔记发现/数据抓取/关键词组/数据洞察/图片工坊/视频工坊/内容库/草稿工坊/发布中心/自动运营）
- [x] 前端通用页面（登录/任务中心/模型配置/系统设置）
- [x] 前端账号管理组件（QR 登录/手机登录/Cookie 导入）
- [x] XHS API 封装（PC/创作者端 API + 登录 API）
- [x] XHS 适配器（creator_api/creator_login/pc_api/pc_login）
- [x] 文档更新（README/PRD/API/DB_DESIGN/DEMO_FLOW/TASK_BACKLOG）

## P4 已完成：智能工作流模块

- [x] RAG 知识库后端（LlamaIndex + ChromaDB 向量存储，知识条目 CRUD，语义检索，智能问答）
- [x] 知识库 API（索引笔记/帖子、语义检索、知识问答、统计信息）
- [x] 合规规则管理后端（compliance_rules 模型、CRUD、默认规则初始化）
- [x] 合规规则 API（规则列表/创建/更新/删除/初始化默认规则）
- [x] LangGraph 工作流引擎（WorkflowEngine + LangGraph 图编排）
- [x] 线索评分工作流（rule_prescreen → ai_lead_identify → lead_persist）
- [x] 话术生成工作流（rag_retrieve → ai_script_generate → compliance_check → risk_gate）
- [x] 内容发布审核工作流（ai_quality_eval → compliance_check → risk_gate）
- [x] 风险门控节点（自动暂停高风险工作流，创建审批记录）
- [x] 审批队列后端（approval_queue 模型、审批/拒绝、内容修改）
- [x] 审批队列 API（待审批列表/审批/拒绝/统计）
- [x] ReAct 智能体（LangGraph ReAct 图、5 种工具、多轮对话）
- [x] 智能体 API（对话/历史/清除）
- [x] 工作流运行记录（WorkflowRun + WorkflowLog 双表、状态追踪、节点日志）
- [x] 工作流 API（运行/查询/恢复/取消/节点日志）
- [x] 数据库迁移：compliance_rules / knowledge_entries / workflow_runs / workflow_logs / approval_queue / agent_conversations（6 个新表）
- [x] 文档更新（API.md / DB_DESIGN.md / README.md / PRD.md / TASK_BACKLOG.md）

## P5 下一步：稳定性与清理

- [ ] 评估旧采集器代码（MockCollector/PlaywrightCollector/ExternalApiCollector/GenericWebCollector）是否删除或归档
- [x] 删除 HomePage.tsx 死代码（已不存在，路由已改为 DashboardPage）
- [x] 归档历史文档（PHASE3/4/5_ACCEPTANCE、REAL_COLLECTION_PLAN 等已移至 docs/archive/）
- [ ] 增加真实采集测试页面或本地 HTML fixture
- [ ] smoke_test 新增 pending competitors 审核步骤
- [ ] CODEX_TASK_RULES.md 审核并更新过时规则
- [ ] 线索详情弹窗展示完整证据链（命中关键词、金额、判断理由）
- [ ] 线索批量操作（批量标记状态、批量导出）
- [ ] 日报 PDF 导出
- [ ] CRM 客户详情页完善（来源帖子、来源线索关联展示）
- [ ] CRM 跟进提醒通知增强（站内通知、邮件提醒）
- [ ] 前端导航优化：帖子池/评论池/评分规则从线索池子路由提升为独立菜单项
- [ ] XHS 数据洞察增强（粉丝趋势、笔记互动趋势、真实数据填充）
- [ ] XHS 自动运营执行逻辑完善（关键词搜索 → AI 生成 → 自动发布完整链路）
- [ ] XHS 监控快照对比功能（变化检测和通知）
- [ ] 发布任务定时调度器（APScheduler 驱动定时发布）

## P6 后续：扩展能力

- [ ] 恢复 MockCollector 到 Factory 路由（保证无 MediaCrawler 服务时演示可跑）
- [ ] 扩展 MediaCrawler 支持更多平台（快手、B站、微博、贴吧）
- [ ] 定义外部采集 API 标准协议
- [ ] 实现 ExternalApiCollector（恢复 Factory 路由）
- [ ] 支持 `endpoint`、`api_key_env`、`timeout`、`retry`
- [ ] 前端支持 external_api 配置
- [ ] 测试 API Key 不泄漏
- [ ] 异步采集队列
- [ ] 线索自动分配和跟进提醒增强
- [ ] 多租户和基础权限
- [ ] 多平台内容发布（抖音、快手等）
- [ ] 内容日历和排期管理
- [ ] AI 内容质量评分和优化建议

## 暂缓

- [ ] 员工管理
- [ ] 复杂权限
- [ ] 验证码处理
- [ ] 代理池 / Cookie 池
- [ ] 真实平台关键词批量搜索
- [ ] 复杂智能体编排
