# 项目进度审计报告

> 审计日期：2026-05-15（二次校验更新）
> 审计范围：dream-ze/xiansuo 仓库 loan-radar 项目
> 审计目标：对照文档与代码，列出真实实现状态、文档偏差和未打通能力

---

## 一、已真正实现且可运行的能力

### 1.1 后端 API（全部可运行）

| 模块 | 路由前缀 | 状态 | 备注 |
|------|----------|------|------|
| 健康检查 | `GET /health` | ✅ | |
| 监控源 CRUD | `/api/monitor-sources` | ✅ | 创建/列表/详情/更新/切换/删除/触发采集 |
| 监控源 MediaCrawler 健康检查 | `GET /api/monitor-sources/media-crawler/health` | ✅ | 返回支持平台列表 |
| 采集任务（旧） | `/api/crawl-tasks` | ✅ | 列表/详情/重跑 |
| 采集任务（新） | `/api/collection/tasks` | ✅ | 创建/列表/详情/运行，走 MediaCrawler |
| 帖子池 | `/api/posts` | ✅ | 列表 + 单帖详情 `GET /api/posts/{id}` |
| 评论池 | `/api/comments` | ✅ | 列表 |
| 线索池 | `/api/leads` | ✅ | 列表/导出/状态更新，支持 source_post_id/source_comment_id 过滤 |
| 日报 | `/api/daily-reports` | ✅ | 生成/今日/历史 |
| 同行账号 | `/api/pending-competitors` | ✅ | 列表/通过/忽略 |
| 采集器能力 | `/api/collectors` | ✅ | 列表/配置校验/健康检查 |
| 内容池 | `/api/content-pools` | ✅ | 占位空路由 |

### 1.2 采集器实现

| 采集器 | 代码文件 | 状态 | 备注 |
|--------|----------|------|------|
| MediaCrawlerCollector | `collectors/media_crawler/collector.py` | ✅ 可运行 | 依赖外部 MediaCrawler API 服务 |
| MockCollector | `collectors/mock_collector.py` | ⚠️ 代码存在 | Factory 不再路由，仅文件残留 |
| PlaywrightCollector | `collectors/playwright_collector.py` | ⚠️ 代码存在 | Factory 不再路由 |
| ExternalApiCollector | `collectors/external_api_collector.py` | ⚠️ 代码存在 | Factory 不再路由 |
| GenericWebCollector | `collectors/generic_web_collector.py` | ⚠️ 代码存在 | Factory 不再路由 |

**关键发现**：`CollectorFactory.create()` 当前仅支持 `media_crawler` 一种 collector_type。`mock`、`playwright`、`external_api`、`generic_web` 四种采集器代码文件仍存在，但 Factory 不再路由到它们。这意味着：

- 监控源触发采集时，如果 `config.collector_type` 不是 `media_crawler`，会抛出 `ValueError("Unsupported collector_type")`
- Mock 主链路无法通过监控源接口触发
- smoke_test.py 全链路不可运行

### 1.3 平台支持（✅ 已统一）

| 层级 | 定义位置 | 支持的平台 | 影响 |
|------|----------|-----------|------|
| 监控源创建校验 | `monitor_source_service.py` SUPPORTED_PLATFORMS | xhs, douyin, zhihu（3个） | 创建监控源时校验，不支持的平台返回 400 |
| 采集任务创建校验 | `collection_task_service.py` SUPPORTED_COLLECTION_PLATFORMS | xhs, douyin, zhihu（3个） | 创建采集任务时校验，不支持的平台返回 400 |
| MediaCrawler 采集 | `media_crawler/mappers.py` SUPPORTED_PLATFORMS | xhs, douyin, zhihu（3个） | 触发采集时校验 |

**已修复**：创建监控源和采集任务时，不支持的平台（kuaishou/bilibili/weibo/tieba/other）直接返回 400，不再出现"创建成功但采集失败"的问题。

### 1.4 采集管道

| 能力 | 状态 | 备注 |
|------|------|------|
| 帖子去重（platform + post_id） | ✅ | `_post_already_exists()` |
| 评论去重（platform + comment_id） | ✅ | `_comment_already_exists()` |
| 线索评分 | ✅ | `LeadScoringService` |
| 同行账号发现 | ✅ | `CompetitorDiscoveryService.discover_from_keyword_crawl()` |
| 采集后更新 last_crawled_at | ✅ | |
| 错误信息脱敏 | ✅ | `_sanitize_error_message()` |
| MediaCrawler 采集分支 | ✅ | `_run_monitor_source_with_media_crawler()` |
| Collection Task 采集分支 | ✅ | `collection_task_service.run_collection_task()` |

### 1.5 前端页面

| 页面 | 路由 | 状态 | API 对接 |
|------|------|------|----------|
| 仪表板 | `/` | ✅ | 统计卡片 + 快捷入口 |
| 监听源 | `/monitor-sources` | ✅ | 完整 CRUD + 采集 + media_crawler 配置 |
| 采集任务 | `/crawl-tasks` | ✅ | 创建采集 + 任务列表 + 详情 + 重跑 |
| 帖子池 | `/posts` | ✅ | 列表 + 线索数 + 跳转线索 |
| 评论池 | `/comments` | ✅ | 列表 + 关联线索 + 跳转线索 |
| 线索池 | `/leads` | ✅ | 列表 + 来源帖子 + 证据链 + 状态更新 + 导出 |
| 日报 | `/daily-reports` | ✅ | 生成 + 展示 |
| 同行账号 | **无路由** | ⚠️ | 组件存在但未挂载路由，用户无法访问 |

---

## 二、文档写了但代码未完整实现的能力

| 文档描述 | 来源 | 实际状态 |
|----------|------|----------|
| MockCollector 可通过监控源接口触发 | PRD、DEMO_FLOW、smoke_test | ❌ Factory 仅支持 media_crawler，mock 无法路由 |
| PlaywrightCollector 用于 manual_post | PRD、API.md | ❌ Factory 不支持 playwright 类型 |
| ExternalApiCollector "已实现" | 旧 API.md §10.3 | ❌ Factory 不路由，代码存在但不可用 |
| GenericWebCollector "已实现" | 旧 API.md §10.3 | ❌ Factory 不路由，代码存在但不可用 |
| XhsCollector（初版）"已实现" | 旧 API.md §10.3 | ❌ 代码已删除，被 MediaCrawler 替代 |
| 前端监控源页支持 playwright 配置提示 | PRD §本阶段做 #7 | ⚠️ 前端下拉仍有 playwright 选项但后端不支持 |
| smoke_test 覆盖 keyword + mock 主链路 | README §步骤23 | ❌ smoke_test Step 1-9 依赖 mock 采集，Factory 不支持 |
| smoke_test 覆盖 manual_post + playwright | README §步骤23 | ❌ smoke_test Step 10-13 依赖 playwright，Factory 不支持 |
| 支持 kuaishou/bilibili/weibo/tieba 平台采集 | API.md 枚举 | ✅ 已修复：API.md 已更新为仅 xhs/douyin/zhihu，不支持平台返回 400 |

---

## 三、代码实现了但文档状态未同步的能力

| 代码实现 | 文档状态 | 影响 |
|----------|----------|------|
| `GET /api/monitor-sources/media-crawler/health` | API.md ✅ 已补全 | 已修复 |
| `GET /api/posts/{post_id}` 单帖详情 | API.md ✅ 已补全 | 已修复 |
| `GET /api/collection/tasks` 全套接口 | API.md ✅ 已补全 | 已修复 |
| `source_post_id` / `source_comment_id` 过滤参数（leads） | API.md ✅ 已补全 | 已修复 |
| `source_post_title` / `source_post_url` 冗余字段（LeadOut） | API.md ✅ 已补全 | 已修复 |
| `lead_count` 字段（PostOut） | API.md ✅ 已补全 | 已修复 |
| `has_lead` 字段（CommentOut） | API.md ✅ 已补全 | 已修复 |
| `collected_posts` / `collected_comments` / `source_value` / `limit_count` 字段（CrawlTaskOut） | API.md ✅ 已补全 | 已修复 |
| MediaCrawler 替代了全部旧采集器 | PRD 仍描述 Mock/Playwright 主链路 | ❌ PRD 严重过时 |
| 前端导航已精简为 7 项 | DEMO_FLOW 仍描述旧流程 | ❌ 演示流程过时 |
| 采集管道已实现去重 | TASK_BACKLOG ✅ 已勾选 | 已修复 |
| 采集后更新 last_crawled_at | TASK_BACKLOG ✅ 已勾选 | 已修复 |
| 错误信息脱敏 | TASK_BACKLOG ✅ 已勾选 | 已修复 |
| `crawl_tasks` 模型新增字段 | DB_DESIGN.md ❌ 未更新 | 数据库设计文档过时 |
| 平台枚举两层定义不一致 | API.md/DB_DESIGN.md ❌ 未反映 | 文档未区分"可创建"和"可采集" |

---

## 四、前端页面已有但接口未打通的能力

| 前端页面/组件 | 问题 | 严重程度 |
|---------------|------|----------|
| PendingCompetitorsPage.tsx | 组件存在但未挂载路由（`routes/index.tsx` 无 `/pending-competitors`），用户无法访问同行账号审核页面 | P1 |
| MonitorSourcesPage 中 playwright 选项 | 前端下拉有 playwright，但后端 Factory 不支持，选了会报错 | P1 |
| MonitorSourcesPage 中 external_api / generic_web 选项 | 前端下拉有这些选项，但后端 Factory 不支持 | P2 |
| MonitorSourcesPage 中 mock 选项 | keyword/competitor_account 默认选 mock，但 Factory 不支持 | P0 |
| MonitorSourcesPage 平台下拉 | ~~可选 kuaishou/bilibili/weibo/tieba~~ | ✅ 已修复：前端仅展示小红书/抖音/知乎 |
| CrawlTasksPage 创建采集表单 | 调用 `/api/collection/tasks` + `/run`，依赖 MediaCrawler 服务在线 | P2（需文档说明） |
| HomePage.tsx | 组件存在但未使用，路由指向 DashboardPage | P2（死代码） |

---

## 五、smoke_test.py 覆盖检查

| 场景 | smoke_test 步骤 | 覆盖状态 | 备注 |
|------|-----------------|----------|------|
| keyword + mock 主链路 | Step 1-9 | ❌ 无法运行 | Step 1 创建 `collector_type: "mock"` 的监控源成功，但 Step 2 触发采集时 Factory 报错 `Unsupported collector_type: mock` |
| manual_post + playwright 成功分支 | Step 10-12 | ❌ 无法运行 | Step 10 创建 `collector_type: "playwright"` 的监控源成功，但 Step 11 触发采集时 Factory 报错 |
| manual_post + playwright 失败分支 | Step 13 | ❌ 无法运行 | 同上，Step 11 就已失败，无法走到 Step 13 |
| leads 导出 | Step 7 | ⚠️ 依赖前置步骤 | 如果前置步骤通过则可覆盖，但当前前置步骤必失败 |
| daily report 生成 | Step 8-9 | ⚠️ 依赖前置步骤 | 同上 |
| pending competitors 审核加入监控源 | 无 | ❌ 未覆盖 | smoke_test 无此步骤 |

**结论**：当前 smoke_test.py **完全无法通过**。Step 1 创建监控源会成功（后端不校验 collector_type 是否被 Factory 支持），但 Step 2 触发采集时必然失败。

---

## 六、P0/P1/P2 修复清单

### P0 — 阻塞性问题（Demo/测试无法运行）

| # | 问题 | 修复方案 |
|---|------|----------|
| P0-1 | CollectorFactory 仅支持 media_crawler，mock/playwright 无法路由，smoke_test 全链路不可运行 | 方案 A：恢复 mock 到 Factory 路由（最小改动，保证演示可跑）；方案 B：重写 smoke_test 基于 media_crawler（需 MediaCrawler 服务在线） |
| P0-2 | 前端 MonitorSourcesPage 默认 collector_type 为 mock（keyword/competitor_account），用户创建后触发采集必失败 | 将默认值改为 `media_crawler`，或恢复 Factory 对 mock 的支持 |
| P0-3 | PRD 和 DEMO_FLOW 描述的 Mock 主链路已不可用 | 更新 PRD/DEMO_FLOW 反映当前 MediaCrawler 单一采集器架构 |
| P0-4 | 前端监控源页 playwright 选项会导致创建后采集失败 | 移除 playwright 选项或恢复 Factory 支持 |

### P1 — 重要不一致（功能缺失或文档严重过时）

| # | 问题 | 修复方案 |
|---|------|----------|
| P1-1 | PendingCompetitorsPage 未挂载路由，同行审核功能不可达 | 在 `routes/index.tsx` 添加 `/pending-competitors` 路由和导航入口 |
| P1-2 | ~~平台枚举两层不一致~~ | ✅ 已修复：统一为 xhs/douyin/zhihu，不支持的平台返回 400 |
| P1-3 | DB_DESIGN.md 缺失 crawl_tasks 新增字段（source_value/limit_count/collected_posts/collected_comments） | 更新 DB_DESIGN.md |
| P1-4 | smoke_test 未覆盖 pending competitors 审核 | 新增 Step 14 测试同行审核 |
| P1-5 | README 中 XHS CDP 相关说明已过时（xhs_collector 等已删除） | 更新或移除相关段落 |
| P1-6 | README 仍描述"Mock / Playwright / External API / Generic Web / XHS"五种采集器 | 更新为 MediaCrawler 单一采集器架构 |

### P2 — 次要问题（死代码、低优先级同步）

| # | 问题 | 修复方案 |
|---|------|------|
| P2-1 | MockCollector/PlaywrightCollector/ExternalApiCollector/GenericWebCollector 代码文件存在但不可用 | 评估是否删除或归档到 `collectors/_deprecated/`，避免误导 |
| P2-2 | HomePage.tsx 死代码 | 删除或合并到 DashboardPage |
| P2-3 | 前端 external_api/generic_web 选项不可用 | 移除或标记为"即将支持" |
| P2-4 | docs/ 下 PHASE3/4/5_ACCEPTANCE、REAL_COLLECTION_PLAN 等历史文档过时 | 归档到 docs/archive/ |
| P2-5 | CODEX_REAL_COLLECTION_STEPS.md / REAL_COLLECTION_PLAN.md 描述旧架构 | 评估是否归档 |
| P2-6 | CODEX_TASK_RULES.md 可能包含过时规则 | 审核并更新 |
