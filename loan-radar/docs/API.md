# API 文档

## 一、文档作用

记录智获客后端当前已实现的全部 HTTP 接口，包括路径、方法、查询参数、请求体、响应结构和错误约定。本文档以 `backend/app/api/routes/` 实际代码为准，不作前瞻性设计。

后续接口变更必须同步更新本文件。

## API 路由总览

| 模块 | 路由前缀 | 代码文件 | 说明 |
|------|----------|----------|------|
| 监控源 | `/api/monitor-sources` | `monitor_sources.py` | 监控源 CRUD、触发采集、定时调度、演示数据 |
| 采集任务（旧） | `/api/crawl-tasks` | `crawl_tasks.py` | 采集任务列表、详情、重跑、失败类型 |
| 采集任务（新） | `/api/collection/tasks` | `collection_tasks.py` | 创建/运行/队列管理 |
| 帖子 | `/api/posts` | `posts.py` | 帖子池列表、详情 |
| 评论 | `/api/comments` | `comments.py` | 评论池列表 |
| 线索 | `/api/leads` | `leads.py` | 线索列表、CSV 导出、状态更新、转 CRM |
| 今日报告 | `/api/daily-reports` | `daily_reports.py` | 生成/获取/导出/历史报告 |
| 内容池 | `/api/content-pools` | `content_pools.py` | 占位路由（无实现） |
| 采集器 | `/api/collectors` | `collectors.py` | 能力列表、配置校验、健康检查 |
| 同行发现 | `/api/pending-competitors` | `pending_competitors.py` | 列表、审核通过、忽略 |
| CRM | `/api/crm` | `crm.py` | 仪表板、客户 CRUD、跟进记录 |
| 仪表板 | `/api/dashboard` | `dashboard.py` | 全局统计、MediaCrawler 健康状态 |
| 评分规则 | `/api/scoring-rules` | `scoring_rules.py` | 获取/更新/测试/批量测试/重载 |
| 用户认证 | `/api/auth` | `auth.py` | 注册/登录/刷新 Token/登出/当前用户 |
| 平台账号 | `/api/accounts` | `accounts.py` | 账号列表/Cookie 导入/状态检查/删除/Cookie 状态 |
| 登录会话 | `/api/xhs/login-sessions` | `login_sessions.py` | QR 码登录/手机验证码登录/会话确认 |
| 笔记 | `/api/notes` | `notes.py` | 笔记列表/详情/批量保存/标签关联/导出 |
| AI 创作 | `/api/ai` | `ai.py` | 改写/生成/标题/标签/润色/封面图/图片/描述 |
| 草稿 | `/api/drafts` | `drafts.py` | 草稿 CRUD/发送至发布中心 |
| 发布 | `/api/publish` | `publish.py` | 发布任务 CRUD/执行发布/素材管理 |
| 文件管理 | `/api/files` | `files.py` | 图片上传/下载/合成/缩放裁剪 |
| 关键词组 | `/api/keyword-groups` | `keyword_groups.py` | 关键词组 CRUD |
| 标签 | `/api/tags` | `tags.py` | 标签 CRUD/笔记标签关联 |
| 模型配置 | `/api/model-configs` | `model_configs.py` | AI 模型配置 CRUD/默认模型切换 |
| 通知 | `/api/notifications` | `notifications.py` | 通知列表/未读计数/标记已读 |
| 任务中心 | `/api/tasks` | `tasks.py` | 任务列表/详情/调度器状态 |
| XHS 数据洞察 | `/api/xhs/analytics` | `xhs_analytics.py` | 运营总览/热门内容/话题/评论/竞品对标 |
| XHS 自动运营 | `/api/xhs/auto-ops` | `xhs_auto_ops.py` | 自动任务 CRUD/执行 |
| XHS 监控 | `/api/xhs/monitoring` | `xhs_monitoring.py` | 监控目标 CRUD/刷新 |
| 智能体 | `/api/agent` | `agent.py` | ReAct 智能体对话/工具列表/会话管理 |
| 知识库 | `/api/knowledge` | `knowledge.py` | 知识条目/索引/检索/查询/统计 |
| 合规规则 | `/api/compliance-rules` | `compliance_rules.py` | 合规规则 CRUD/初始化默认规则 |
| 工作流 | `/api/workflows` | `workflows.py` | 线索评分/话术生成/内容发布审核/运行记录 |
| 审批队列 | `/api/approvals` | `approvals.py` | 审批列表/待审计数/审批操作 |
| 视频工坊 | `/api/video-studio` | `video_studio.py` | 视频上传/截取封面/AI 描述 |

## 二、约定

### 2.1 基础地址

- 本地开发：`http://localhost:8001`
- 健康检查：`GET /health` → `{"status": "ok"}`

### 2.2 统一响应包装

除 CSV / Markdown 导出外，所有接口统一使用 `app/utils/response.py` 中的包装结构。

成功响应：

```json
{
  "success": true,
  "data": <object | array | {}>,
  "message": "ok"
}
```

错误响应：

```json
{
  "success": false,
  "data": null,
  "message": "<错误说明>"
}
```

### 2.3 分页响应

列表类接口（采集任务、帖子、评论、线索、CRM 客户、跟进记录）的 `data` 字段固定为：

```json
{
  "items": [...],
  "total": 123,
  "page": 1,
  "page_size": 20
}
```

### 2.4 错误码

| HTTP | 含义 | 触发场景 |
|------|------|----------|
| 200 | 成功 | 正常返回（含业务校验失败前的成功路径） |
| 202 | 已接受 | 采集任务已入队，异步执行中 |
| 400 | 参数/状态校验失败 | `ValueError`、非法 `status`、不可重跑等 |
| 404 | 资源不存在 | id 查不到对应记录 |
| 422 | FastAPI 自动校验 | Query/Body 类型或 ge/le 越界 |

### 2.5 通用枚举

- `source_type`：`keyword` / `competitor_account` / `manual_post` / `hot_post_rule`
- `platform`：`xhs` / `douyin` / `zhihu`

  > 当前 MVP 仅支持以上 3 个平台。传入其他平台（如 kuaishou / bilibili / weibo / tieba / other）将返回 400 错误。后续版本将逐步开放更多平台。
- `crawl_task.status`：`pending` / `running` / `success` / `failed`
- `crawl_task.progress`：`queued` / `collecting` / `saving_posts` / `scoring_leads`
- `lead.lead_level`：`A` / `B` / `C` / `D`
- `lead.status`：`new` / `contacted` / `interested` / `invalid` / `converted`
- `lead.is_duplicate`：`true` / `false`——标记线索是否为疑似重复
- `lead.duplicate_reason`：重复原因枚举值——`"同用户相似评论(相似度XX%)"` 或 `"相同内容重复"`
- `comment.demand_type`：由评分服务输出（如 `借款需求`、`资质焦虑`、`产品咨询`、`弱意向` 等）
- `comment.risk_level`：由评分服务输出（如 `low` / `mid` / `high`，以代码为准）
- `collector_type`：`media_crawler`（真实采集）/ `mock`（演示采集，需设置 `ENABLE_MOCK_COLLECTOR=true`）
- `crawl_task.failure_type`：`media_crawler_unreachable` / `platform_not_supported` / `auth_required` / `captcha_or_risk_control` / `timeout` / `empty_result` / `parser_error` / `unknown`
- `crm_customer.status`：`pending` / `contacted` / `interested` / `wechat_added` / `applied` / `converted` / `invalid`
- `crm_customer.source_type`：`lead_conversion` / `manual` / `import`
- `crm_follow_record.follow_type`：`phone` / `wechat` / `message` / `visit` / `other`
- `crm_customer.source_channel`：`小红书` / `抖音` / `知乎` / `微信` / `电话` / `朋友介绍` / `线下` / `员工自拓` / `其他`
- `config.time_range`：`7d` / `15d` / `30d` / `90d`（为空或不设则不限制时间范围）

---

## 三、监控源 Monitor Sources

路由前缀：`/api/monitor-sources`

### 3.1 创建监控源

`POST /api/monitor-sources`

请求体：

```json
{
  "source_type": "keyword",
  "platform": "xhs",
  "name": "信用贷关键词",
  "value": "信用贷",
  "config": {
    "collector_type": "media_crawler",
    "login_type": "qrcode",
    "enable_comments": true,
    "max_posts": 20,
    "max_comments_per_post": 50,
    "time_range": "7d"
  },
  "enabled": true,
  "last_crawled_at": null
}
```

`config` 完整字段说明：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `collector_type` | string | `"media_crawler"` | 采集器类型，当前仅支持 `media_crawler` |
| `mode` | string | `"test"` | 模式：`test`（测试）/ `real`（真实） |
| `max_posts` | int | `10` | 单次采集最多笔记数（1-1000） |
| `max_comments_per_post` | int | `50` | 每条笔记最多评论数（1-100） |
| `timeout_seconds` | int | `30` | 请求超时时间（5-300 秒） |
| `retry_times` | int | `3` | 重试次数（1-10） |
| `rate_limit_seconds` | int | `1` | 请求间隔（0-60 秒） |
| `cookies` | string | null | 登录 Cookie |
| `user_agent` | string | null | 自定义 UA |
| `login_type` | string | null | 登录方式：`cookie` / `qrcode` / `phone` |
| `enable_comments` | bool | null | 是否采集评论（默认 True） |
| `time_range` | string | null | 采集时间范围：`7d` / `15d` / `30d` / `90d` |

`config.time_range` 说明：
- 可选值：`7d` / `15d` / `30d` / `90d`，为空或不传则不限制时间范围
- 设置 `time_range` 后，采集时 `max_posts` 自动提升至 80（`TIME_RANGE_BOOSTED_MAX_POSTS`），确保采集量覆盖
- 入库前按 `publish_time` 过滤帖子和评论，仅保留发布时间在范围内的内容
- `publish_time` 为空的帖子/评论将被过滤掉

响应：`success_response(MonitorSourceOut)`

`MonitorSourceOut` 字段：`id, source_type, platform, name, value, config, enabled, schedule_enabled, schedule_cron, last_crawled_at, created_at, updated_at`。

错误：参数非法返回 400。

### 3.2 监控源列表

`GET /api/monitor-sources`

查询参数（全部可选）：

- `source_type`、`platform`、`enabled`(bool)、`keyword`（按 name/value 模糊匹配）

响应：`success_response([MonitorSourceOut])`（注意：本接口不分页，直接返回数组）。

### 3.3 监控源详情

`GET /api/monitor-sources/{monitor_source_id}`

响应：`success_response(MonitorSourceOut)`；不存在返回 404。

### 3.4 更新监控源

`PATCH /api/monitor-sources/{monitor_source_id}`

请求体：`MonitorSourceUpdate`，所有字段均可选，仅传需要变更的字段。

响应：`success_response(MonitorSourceOut)`；不存在返回 404；参数非法返回 400。

### 3.5 启用 / 禁用切换

`PATCH /api/monitor-sources/{monitor_source_id}/toggle`

查询参数：

- `enabled`（bool，可选）：传入则强制设为该值；不传则在当前值上取反。

响应：`success_response(MonitorSourceOut)`。

### 3.6 触发采集

`POST /api/monitor-sources/{monitor_source_id}/crawl`

行为：基于该监控源同步运行一次采集流水线，返回新建的 `CrawlTask`。

- 当 `config.collector_type == "media_crawler"` 时，使用 MediaCrawlerCollector 采集。
- 当 `config.collector_type == "mock"` 时，使用 MockCollector 生成演示数据（需 `ENABLE_MOCK_COLLECTOR=true`）。
- MediaCrawler 支持关键词搜索、指定帖子、创作者主页采集，需 MediaCrawler API 服务在线。
- 采集失败不会导致后端服务崩溃；任务返回 `status="failed"`，并在 `error_message` 中写明原因。
- 当 `config.time_range` 有值时，采集量自动提升，入库前按发布时间过滤。

响应：`success_response(CrawlTaskOut)`；监控源不存在返回 404。

### 3.7 删除监控源

`DELETE /api/monitor-sources/{monitor_source_id}`

响应：`success_response({"id": <删除的 id>})`；不存在返回 404。

### 3.8 MediaCrawler 健康检查

`GET /api/monitor-sources/media-crawler/health`

行为：检查 MediaCrawler API 服务是否可用，返回支持的平台列表。

响应：

```json
{
  "success": true,
  "data": {
    "status": "healthy" | "unreachable",
    "api_base_url": "http://127.0.0.1:8080",
    "supported_platforms": [
      {"value": "douyin", "label": "抖音"},
      {"value": "xhs", "label": "小红书"},
      {"value": "zhihu", "label": "知乎"}
    ]
  }
}
```

### 3.9 一键初始化演示数据

`POST /api/monitor-sources/demo/seed`

行为：直接写入数据库生成完整演示数据（监控源、帖子、评论、线索、同行账号、日报）。仅在开发环境（`APP_ENV != production`）可用，生产环境返回 403。支持重复运行（先清理旧 demo 数据）。

响应（200）：

```json
{
  "success": true,
  "data": {
    "message": "演示数据初始化完成",
    "stats": {
      "sources": 3,
      "posts": 10,
      "comments": 50,
      "leads": 29,
      "lead_levels": {"A": 16, "B": 6, "C": 4, "D": 3},
      "competitors": 5,
      "crawl_tasks": 3,
      "report_date": "2026-05-17"
    },
    "tip": "所有演示数据均标记 raw_data.demo=true，可与真实数据区分"
  }
}
```

响应（403，生产环境）：

```json
{
  "success": false,
  "message": "生产环境禁止使用演示数据初始化接口"
}
```

### 3.10 一键生成演示数据（采集方式）

`POST /api/monitor-sources/demo/generate`

行为：创建演示监控源并立即触发采集任务，生成完整的演示链路数据。仅在 `ENABLE_MOCK_COLLECTOR=true` 时可用，否则返回 403。

响应（200）：

```json
{
  "success": true,
  "data": {
    "message": "演示数据生成中，请稍后查看帖子池、评论池、线索池和日报",
    "demo_sources": [
      {"id": 1, "name": "演示 - 征信花了", "source_type": "keyword", "platform": "xhs"},
      {"id": 2, "name": "演示 - 急用5万周转", "source_type": "keyword", "platform": "douyin"},
      {"id": 3, "name": "演示 - 负债高能不能做", "source_type": "keyword", "platform": "zhihu"},
      {"id": 4, "name": "演示 - 爆款规则", "source_type": "hot_post_rule", "platform": "xhs"}
    ],
    "crawl_tasks": [
      {"task_id": 1, "source_id": 1, "queue_position": 0},
      {"task_id": 2, "source_id": 2, "queue_position": 1}
    ],
    "tip": "所有演示数据均标记 raw_data.demo=true，可与真实数据区分"
  }
}
```

响应（403，未启用演示模式）：

```json
{
  "success": false,
  "message": "演示模式未启用，请设置 ENABLE_MOCK_COLLECTOR=true"
}
```

### 3.11 定时采集调度状态

`GET /api/monitor-sources/scheduler/status`

行为：返回定时采集调度器的运行状态。

响应：

```json
{
  "success": true,
  "data": {
    "running": true,
    "jobs": [
      {"id": "scheduled_source_check", "name": "Check scheduled monitor sources", "next_run_time": "..."},
      {"id": "source_schedule_1", "name": "Schedule source 1", "next_run_time": "..."}
    ]
  }
}
```

---

## 四、采集任务 Crawl Tasks

### 4.1 采集任务列表（旧接口）

路由前缀：`/api/crawl-tasks`

`GET /api/crawl-tasks`

查询参数：

- `status`、`source_type`、`platform`、`source_id`（可选过滤）
- `page`（默认 1，ge=1）、`page_size`（默认 20，ge=1, le=100）

响应：`success_response({items: [CrawlTaskOut], total, page, page_size})`。

`CrawlTaskOut` 字段：`id, source_id, source_type, source_value, platform, status, progress, limit_count, retry_count, max_retries, last_error_type, failure_type, started_at, finished_at, error_message, post_count, comment_count, collected_posts, collected_comments, lead_count, discovered_competitor_count, duplicate_post_count, duplicate_comment_count, created_at, updated_at`。

- `failure_type`：失败类型分类，可选值：`media_crawler_unreachable` / `platform_not_supported` / `auth_required` / `captcha_or_risk_control` / `timeout` / `empty_result` / `parser_error` / `unknown`。仅在 `status == "failed"` 时有值。
- `error_message`：脱敏后的错误信息，不暴露内部堆栈、密钥、Cookie、数据库连接串。

### 4.2 采集任务详情

`GET /api/crawl-tasks/{crawl_task_id}`

响应：`success_response(CrawlTaskOut)`；不存在返回 404。

### 4.3 失败类型元数据

`GET /api/crawl-tasks/failure-types/meta`

行为：返回所有失败类型的中文标签、描述和处理建议，供前端展示。

响应：

```json
{
  "success": true,
  "data": {
    "media_crawler_unreachable": {
      "value": "media_crawler_unreachable",
      "label": "采集服务不可用",
      "description": "MediaCrawler API 服务未启动或无法连接",
      "suggestion": "请启动 MediaCrawler 服务，或切换为演示模式（设置 ENABLE_MOCK_COLLECTOR=true）"
    },
    "platform_not_supported": { ... },
    "auth_required": { ... },
    "captcha_or_risk_control": { ... },
    "timeout": { ... },
    "empty_result": { ... },
    "parser_error": { ... },
    "unknown": { ... }
  }
}
```

### 4.4 重跑失败任务

`POST /api/crawl-tasks/{crawl_task_id}/rerun`

约束：仅当任务 `status == "failed"` 时可重跑。

响应：`success_response(CrawlTaskOut)`（新创建的重跑任务）。

错误：

- 任务不存在 → 404
- 任务非 failed → 400 `"only failed crawl tasks can be rerun"`
- 关联监控源不存在 → 404 `"monitor source not found"`

### 4.5 采集任务创建与运行（新接口）

路由前缀：`/api/collection/tasks`

`POST /api/collection/tasks` — 创建采集任务

请求体：

```json
{
  "platform": "xhs",
  "source_type": "keyword",
  "source_value": "征信花了",
  "limit_count": 20
}
```

`source_type` 可选值：`keyword` / `account` / `post_url`（前端映射为 `keyword` / `competitor_account` / `manual_post`）。

响应：`success_response(CrawlTaskOut)`。

`GET /api/collection/tasks` — 列表

查询参数：`status`、`source_type`、`page`、`page_size`

响应：`success_response({items: [CrawlTaskOut], total, page, page_size})`。

`GET /api/collection/tasks/{task_id}` — 详情

响应：`success_response(CrawlTaskOut)`；不存在返回 404。

`POST /api/collection/tasks/{task_id}/run` — 运行

行为：将任务加入采集队列，异步执行。

响应（202）：`success_response({...CrawlTaskOut, queue_position: 0})`；任务不存在返回 404；已在运行返回 400。

`GET /api/collection/tasks/queue/status` — 队列状态

响应：

```json
{
  "success": true,
  "data": {
    "active_task_id": 5,
    "queue_size": 2,
    "queue_items": [6, 7]
  }
}
```

---

## 五、帖子 Posts

### 5.1 帖子列表

`GET /api/posts`

查询参数：

- `platform`、`source_type`、`source_id`、`is_hot`(bool)
- `keyword`：在 `title / content / post_id / author_name` 上做 ILIKE 模糊匹配
- `page` / `page_size`：同上

响应：`success_response({items: [PostOut], total, page, page_size})`。

`PostOut` 字段：`id, platform, source_id, source_type, post_id, content_hash, title, content, post_url, author_name, author_profile_url, like_count, comment_count, collect_count, publish_time, is_hot, raw_data, created_at, updated_at`。

- `content_hash`：内容 MD5 哈希，用于去重
- `lead_count`：该帖子关联的线索数量（由 `_enrich_post_out` 计算填充）

排序：按 `id DESC`。

### 5.2 帖子详情

`GET /api/posts/{post_id}`

响应：`success_response(PostOut)`；不存在返回 `success_response({"success": false, ...})`。

---

## 六、评论 Comments

### 6.1 评论列表

`GET /api/comments`

查询参数：

- `platform`、`demand_type`、`risk_level`、`is_suspected_demand`(bool)、`post_id`(string，对应 `comments.post_id` 平台原始帖子 id)
- `keyword`：在 `content / user_name / comment_id` 上做 ILIKE 模糊匹配
- `page` / `page_size`：同上

响应：`success_response({items: [CommentOut], total, page, page_size})`。

`CommentOut` 字段：`id, platform, post_id, comment_id, content_hash, user_name, user_profile_url, content, like_count, publish_time, is_suspected_demand, demand_type, risk_level, raw_data, created_at, updated_at`。

- `content_hash`：评论内容 MD5 哈希，用于去重
- `has_lead`：该评论是否已生成线索（由 `_enrich_comment_out` 计算填充）

---

## 七、线索 Leads

路由前缀：`/api/leads`

### 7.1 线索列表

`GET /api/leads`

查询参数：

- `lead_level`、`demand_type`、`risk_level`、`platform`、`status`、`source_type`
- `source_post_id`（可选）：按来源帖子 ID 过滤
- `source_comment_id`（可选）：按来源评论 ID 过滤
- `is_duplicate`（可选，bool）：按重复标记过滤——`true` 仅返回重复线索，`false` 仅返回非重复线索，不传则返回全部
- `converted_to_crm`（可选，bool）：按是否已转 CRM 过滤——`true` 仅返回已转客户线索，`false` 仅返回未转客户线索
- `created_after`（可选，string）：ISO 日期字符串，仅返回此时间之后创建的线索
- `keyword`：在 `content / user_name / reason` 等字段做模糊匹配（详见 `export_service.build_leads_query`）
- `page` / `page_size`：同上

响应：`success_response({items: [LeadOut], total, page, page_size})`，按 `id DESC`。

`LeadOut` 字段：`id, platform, source_id, source_type, source_post_id, source_comment_id, source_post_title, source_post_url, user_name, user_profile_url, content, content_hash, lead_level, lead_score, demand_type, risk_level, evidence, reason, follow_up_script, status, notes, crm_customer_id, crm_opportunity_id, converted_to_crm_at, is_duplicate, duplicate_group_id, duplicate_reason, created_at, updated_at`。

- `source_post_title`：来源帖子标题（冗余字段，由 `_enrich_lead_out` 填充）
- `source_post_url`：来源帖子 URL（冗余字段，由 `_enrich_lead_out` 填充）
- `user_profile_url`：评论者主页 URL，用于同用户相似评论去重
- `content_hash`：评论内容 MD5 哈希，用于相同内容去重
- `crm_customer_id`：关联的 CRM 客户 ID，线索转客户后自动填充
- `crm_opportunity_id`：关联的 CRM 商机 ID（预留字段）
- `converted_to_crm_at`：线索转客户的时间
- `is_duplicate`：是否为疑似重复线索（`true` / `false`）
- `duplicate_group_id`：重复组 ID，同一组内的线索互为重复，值为 `dup-` 前缀的 12 位随机字符串
- `duplicate_reason`：重复原因，如 `"同用户相似评论(相似度80%)"` 或 `"相同内容重复"`

`evidence` 是 JSON，结构由评分服务输出：

```json
{
  "matched_words": {"demand": [...], "urgency": [...], "qualification": [...], "product": [...], "risk": [...]},
  "amounts": [{"value": 5, "unit": "万"}],
  "score_breakdown": {
    "demand_clarity": 25,
    "urgency": 10,
    "amount": 15,
    "qualification": 10,
    "product_match": 10,
    "authenticity": 5,
    "risk_penalty": 0
  }
}
```

### 7.2 线索 CSV 导出

`GET /api/leads/export`

查询参数：与 7.1 完全一致（含 `source_post_id`、`source_comment_id`、`is_duplicate`、`converted_to_crm`、`created_after`，除分页外），不分页，全量导出。

响应：

- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename=leads.csv`
- Body：UTF-8 CSV 字节流（不走统一响应包装）

CSV 列：`线索等级, 评分, 需求类型, 评论内容, 识别理由, 跟进话术, 风险提示, 来源平台, 状态, 备注, 是否重复, 重复原因, 重复组ID, 创建时间`

- `是否重复`：`"是"` 或 `"否"`
- `重复原因`：如 `"同用户相似评论(相似度80%)"` 或 `"相同内容重复"`，非重复线索为空
- `重复组ID`：`dup-` 前缀的组标识，非重复线索为空

### 7.3 更新线索状态

`PATCH /api/leads/{lead_id}/status`

请求体：

```json
{ "status": "contacted", "notes": "已电话联系" }
```

`status` 必须属于 `new / contacted / interested / invalid / converted`，否则返回 400。`notes` 可选，同时更新备注。

响应：`success_response(LeadOut)`；线索不存在返回 404。

### 7.4 线索转 CRM 客户

`POST /api/leads/{lead_id}/convert-to-crm`

请求体：

```json
{
  "owner_name": "张经理",
  "next_follow_up_at": "2026-05-20T10:00:00Z"
}
```

行为：将线索转为 CRM 客户，自动填充来源信息（平台、渠道、需求类型、线索等级等）。线索状态自动更新为 `contacted`，`crm_customer_id` 和 `converted_to_crm_at` 自动填充。

- 同一线索不可重复转入 CRM
- 已转入的线索再次调用返回 400

响应：`success_response({"customer": CrmCustomerOut})`；线索不存在返回 404；已转入返回 400。

---

## 八、今日获客报告 Daily Reports

路由前缀：`/api/daily-reports`

### 8.1 生成今日报告

`POST /api/daily-reports/generate`

查询参数：

- `platform`（可选）：传入时仅统计该平台；不传则统计全平台

响应：`success_response(DailyReportOut)`。

`DailyReportOut` 字段：`id, report_date, platform, source_count, post_count, comment_count, lead_count, a_lead_count, b_lead_count, c_lead_count, d_lead_count, top_demands, top_keywords, hot_posts, content_suggestions, follow_up_suggestions, risk_warnings, a_lead_details, typical_evidence, discovered_competitors, tomorrow_suggestions, crm_stats, created_at, updated_at`。

新增字段说明：
- `a_lead_details`：A级线索详情列表（JSON）
- `typical_evidence`：典型需求证据（JSON）
- `discovered_competitors`：发现的同行账号（JSON）
- `tomorrow_suggestions`：明日采集建议（JSON）
- `crm_stats`：CRM 统计数据（JSON）

### 8.2 获取今日报告

`GET /api/daily-reports/today`

查询参数：`platform`（可选）。

响应：

- 已生成 → `success_response(DailyReportOut)`
- 未生成 → 404 `"today's report not found, please generate first"`

### 8.3 导出今日报告

`GET /api/daily-reports/today/export`

查询参数：

- `format`（可选，默认 `markdown`）：导出格式，目前仅支持 `markdown` / `md`
- `platform`（可选）

响应（Markdown 格式）：

- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="loan-radar-report-2026-05-19.md"`
- Body：UTF-8 Markdown 字节流

报告未生成时返回 404。

### 8.4 历史报告列表

`GET /api/daily-reports`

查询参数：`platform`（可选）。

响应：`success_response([DailyReportOut])`（不分页）。

---

## 九、内容池 Content Pools

`/api/content-pools`（占位 router，当前无任何已实现的接口）。

帖子池、评论池请直接使用第五章 `/api/posts` 与第六章 `/api/comments`。

---

## 十、采集器能力 Collectors

路由前缀：`/api/collectors`

### 10.1 采集器能力列表

`GET /api/collectors`

响应：

```json
{
  "collectors": {
    "media_crawler": {
      "name": "MediaCrawler 多平台采集器",
      "description": "...",
      "status": "ready",
      "supports": ["keyword", "competitor_account", "manual_post", "hot_post_rule"],
      "config": { ... }
    }
  },
  "summary": {
    "ready": ["media_crawler"],
    "implementing": [],
    "planned": []
  }
}
```

### 10.2 配置校验

`POST /api/collectors/validate-config`

请求体：采集器配置字典。

响应：

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "config": { ... }
}
```

### 10.3 健康检查

`GET /api/collectors/health`

响应：

```json
{
  "status": "ok",
  "ready_collectors": 1,
  "total_collectors": 1
}
```

---

## 十一、同行账号发现池 Pending Competitors

路由前缀：`/api/pending-competitors`

### 11.1 列表

`GET /api/pending-competitors`

查询参数：

- `platform`（可选）
- `status`（可选：`pending` / `approved` / `ignored`）
- `min_score`（可选，0-100）

响应：`success_response([PendingCompetitorOut])`。

### 11.2 审核通过

`POST /api/pending-competitors/{id}/approve`

行为：仅 `pending` 状态可通过。通过后创建一个 `source_type=competitor_account` 的监控源。

响应：

```json
{
  "success": true,
  "data": {
    "pending_competitor": {},
    "monitor_source": {}
  },
  "message": "ok"
}
```

### 11.3 忽略

`POST /api/pending-competitors/{id}/ignore`

行为：仅 `pending` 状态可忽略。

响应：`success_response(PendingCompetitorOut)`。

---

## 十二、轻 CRM 跟进台

路由前缀：`/api/crm`

### 12.1 CRM 仪表板

`GET /api/crm/dashboard`

响应：

```json
{
  "success": true,
  "data": {
    "total_customers": 10,
    "lead_conversion_count": 6,
    "manual_count": 4,
    "today_new": 2,
    "today_manual": 1,
    "pending_follow": 3,
    "interested": 2,
    "converted": 1,
    "overdue_follow": 1,
    "today_follow_up_count": 2,
    "tomorrow_follow_up_count": 1,
    "this_week_follow_up_count": 4,
    "status_counts": {"pending": 3, "contacted": 2, "interested": 2, "wechat_added": 1, "applied": 1, "converted": 1, "invalid": 0},
    "level_counts": {"A": 4, "B": 3, "C": 2, "unknown": 1}
  }
}
```

### 12.2 客户列表

`GET /api/crm/customers`

查询参数（全部可选）：

- `source_type`：`lead_conversion` / `manual` / `import`
- `source_channel`：来源渠道（如 `小红书`、`抖音`、`知乎`、`微信` 等）
- `platform`：`xhs` / `douyin` / `zhihu`
- `lead_level`：`A` / `B` / `C` / `D`
- `status`：`pending` / `contacted` / `interested` / `wechat_added` / `applied` / `converted` / `invalid`
- `owner_name`：负责人
- `keyword`：在 `customer_name / nickname / phone` 上做模糊匹配
- `reminder`：跟进提醒过滤——`overdue`（已逾期）/ `today`（今日跟进）/ `tomorrow`（明日跟进）/ `this_week`（本周跟进）/ `none`（暂无提醒）
- `page` / `page_size`

响应：`success_response({items: [CrmCustomerOut], total, page, page_size})`。

`CrmCustomerOut` 字段：`id, source_type, lead_id, platform, source_channel, source_url, source_post_id, customer_name, nickname, phone, wechat, city, demand_type, demand_description, intended_amount, lead_level, status, owner_name, entered_by, notes, next_follow_up_at, last_follow_up_at, converted_at, created_at, updated_at`。

### 12.3 手动创建客户

`POST /api/crm/customers`

请求体：

```json
{
  "customer_name": "张先生",
  "nickname": "小张",
  "phone": "13800138000",
  "wechat": "zhang_wx",
  "source_channel": "小红书",
  "demand_type": "信用贷",
  "demand_description": "需要5万信用贷",
  "intended_amount": 50000,
  "city": "北京",
  "lead_level": "A",
  "owner_name": "李经理",
  "entered_by": "admin",
  "notes": "客户意向较强",
  "next_follow_up_at": "2026-05-20T10:00:00Z"
}
```

所有字段均可选。`source_type` 自动设为 `manual`，`status` 自动设为 `pending`。

响应：`success_response(CrmCustomerOut)`。

### 12.4 线索转客户

`POST /api/crm/customers/from-lead/{lead_id}`

行为：将指定线索转为 CRM 客户，自动填充来源信息。

- 同一线索不可重复转入
- 线索不存在返回 404
- 已转入返回 400 `"该线索已转入 CRM"`

响应：`success_response(CrmCustomerOut)`。

### 12.5 客户详情

`GET /api/crm/customers/{customer_id}`

响应：`success_response(CrmCustomerOut)`；不存在返回 404。

### 12.6 更新客户信息

`PATCH /api/crm/customers/{customer_id}`

请求体（所有字段均可选）：

```json
{
  "customer_name": "张先生",
  "status": "contacted",
  "owner_name": "王经理",
  "next_follow_up_at": "2026-05-22T14:00:00Z"
}
```

- `status` 必须属于 `pending / contacted / interested / wechat_added / applied / converted / invalid`，否则返回 400
- 当 `status` 更新为 `converted` 时，`converted_at` 自动填充为当前时间

响应：`success_response(CrmCustomerOut)`；不存在返回 404。

### 12.7 添加跟进记录

`POST /api/crm/customers/{customer_id}/follow-records`

请求体：

```json
{
  "follow_type": "phone",
  "content": "电话沟通，客户表示有意向，需要再考虑",
  "next_follow_up_at": "2026-05-22T14:00:00Z"
}
```

- `follow_type`：`phone` / `wechat` / `message` / `visit` / `other`
- `content`：必填
- `next_follow_up_at`：可选，设置后自动更新客户的 `next_follow_up_at`
- 添加跟进记录后，客户的 `last_follow_up_at` 自动更新

响应：`success_response(CrmFollowRecordOut)`；客户不存在返回 404。

`CrmFollowRecordOut` 字段：`id, customer_id, follow_type, content, next_follow_up_at, created_at`。

### 12.8 跟进记录列表

`GET /api/crm/customers/{customer_id}/follow-records`

查询参数：

- `page` / `page_size`

响应：`success_response({items: [CrmFollowRecordOut], total, page, page_size})`；客户不存在返回 404。

排序：按 `id DESC`。

---

## 十三、仪表板 Dashboard

路由前缀：`/api/dashboard`

### 13.1 全局统计

`GET /api/dashboard/stats`

响应：

```json
{
  "success": true,
  "data": {
    "source_count": 5,
    "today_task_count": 3,
    "today_post_count": 15,
    "today_comment_count": 80,
    "today_lead_count": 12,
    "today_a_lead_count": 4,
    "total_task_count": 20,
    "total_post_count": 100,
    "total_comment_count": 500,
    "total_lead_count": 60,
    "total_a_lead_count": 15,
    "yesterday_lead_count": 10,
    "yesterday_a_lead_count": 3,
    "yesterday_post_count": 12,
    "pending_competitor_count": 3,
    "crm_today_new": 2,
    "crm_pending_follow": 5,
    "crm_overdue_follow": 1,
    "crm_converted": 3,
    "recent_a_leads": [...],
    "recent_tasks": [...]
  }
}
```

- `source_count`：启用的监控源数量
- `today_*`：今日新增统计
- `total_*`：累计统计
- `yesterday_*`：昨日统计（用于对比）
- `pending_competitor_count`：待审核同行账号数量
- `crm_*`：CRM 相关统计
- `recent_a_leads`：最近 5 条 A 级线索（含 `id, platform, user_name, content, lead_score, demand_type, follow_up_script, created_at`）
- `recent_tasks`：最近 5 条采集任务（含 `id, source_type, source_value, platform, status, post_count, comment_count, lead_count, error_message, started_at, finished_at, created_at`）

### 13.2 MediaCrawler 健康状态

`GET /api/dashboard/media-crawler-health`

行为：检查 MediaCrawler 服务健康状态，自动判断运行模式（HTTP Bridge 或内嵌模式）。

响应：

```json
{
  "success": true,
  "data": {
    "status": "healthy" | "unreachable" | "misconfigured",
    "mode": "http_bridge" | "embedded",
    "api_base_url": "http://127.0.0.1:8080",
    "media_crawler_home": "/path/to/MediaCrawler",
    "shared_db": {
      "available": true,
      "path": "/path/to/MediaCrawler/data/media_crawler.db"
    },
    "supported_platforms": [
      {"value": "douyin", "label": "抖音"},
      {"value": "xhs", "label": "小红书"},
      {"value": "zhihu", "label": "知乎"}
    ]
  }
}
```

- `mode`：`http_bridge`（HTTP API 模式）或 `embedded`（内嵌模式，需设置 `MEDIA_CRAWLER_HOME`）
- `shared_db`：MediaCrawler 共享数据库状态（内嵌模式下可直接读取采集结果）

---

## 十四、评分规则 Scoring Rules

路由前缀：`/api/scoring-rules`

### 14.1 获取评分规则

`GET /api/scoring-rules`

响应：

```json
{
  "success": true,
  "data": {
    "version": "1.0",
    "dimensions": [
      {
        "name": "demand_clarity",
        "weight": 1.0,
        "patterns": ["借款", "贷款", "信用贷"],
        "score_per_hit": 5,
        "max_score": 25,
        "description": "需求明确度"
      }
    ],
    "negative_patterns": [...],
    "negation_patterns": [...],
    "lead_level_thresholds": {"A": 60, "B": 40, "C": 20, "D": 0},
    "demand_type_rules": [...],
    "risk_keywords": [...],
    "amount_pattern": "..."
  }
}
```

### 14.2 更新评分规则

`PUT /api/scoring-rules`

请求体：

```json
{
  "rules": {
    "version": "1.1",
    "dimensions": [...],
    ...
  }
}
```

行为：校验规则格式，写入 `backend/config/scoring_rules.json`，自动重载评分服务。

响应：`success_response(rules_dict)`；格式错误返回错误信息。

### 14.3 测试评分效果

`POST /api/scoring-rules/test`

请求体：

```json
{ "text": "征信花了急需5万周转" }
```

响应：

```json
{
  "success": true,
  "data": {
    "lead_level": "A",
    "lead_score": 75,
    "demand_type": "借款需求",
    "risk_level": "low",
    "evidence": {...},
    "reason": "命中借款需求+金额+紧急度关键词",
    "follow_up_script": "...",
    "is_suspected_demand": true
  }
}
```

### 14.4 批量测试评分

`POST /api/scoring-rules/batch-test`

请求体：最多 50 条文本的数组。

```json
[
  { "text": "征信花了急需5万周转" },
  { "text": "谢谢分享" }
]
```

响应：`success_response([{text, lead_level, lead_score, demand_type, risk_level, reason, is_suspected_demand}, ...])`。

### 14.5 重载评分规则

`POST /api/scoring-rules/reload`

行为：从配置文件重新加载评分规则。

响应：`success_response({"version": "1.0", "message": "rules reloaded"})`。

---

## 十五、用户认证 Auth

路由前缀：`/api/auth`

### 15.1 用户注册

`POST /api/auth/register`

请求体：

```json
{
  "username": "string (3-80)",
  "password": "string (6-128)"
}
```

行为：创建新用户，返回 JWT Token。用户名已存在返回 400。

响应：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {"id": 1, "username": "string"}
}
```

### 15.2 用户登录

`POST /api/auth/login`

请求体：同注册。

行为：验证用户名和密码，返回 JWT Token。密码使用 PBKDF2_SHA256 验证。用户名或密码错误返回 401。

响应：同注册。

### 15.3 刷新 Token

`POST /api/auth/refresh`

请求体：

```json
{ "refresh_token": "eyJ..." }
```

行为：验证 refresh_token，返回新的 access_token。Token 无效返回 401。

响应：

```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### 15.4 登出

`POST /api/auth/logout`

响应：`{"status": "ok"}`

### 15.5 获取当前用户

`GET /api/auth/me`

需要认证（Bearer Token）。

响应：`{"id": 1, "username": "string"}`

---

## 十六、平台账号 Accounts

路由前缀：`/api/accounts`

所有接口需要认证。

### 16.1 账号列表

`GET /api/accounts`

查询参数：

- `platform`（可选）：按平台过滤
- `page` / `page_size`

响应：`paginated([AccountOut])`。

`AccountOut` 字段：`id, user_id, platform, sub_type, external_user_id, nickname, avatar_url, status, status_message, profile_json, created_at, updated_at`。

### 16.2 Cookie 导入

`POST /api/accounts/import-cookie`

请求体：

```json
{
  "platform": "xhs",
  "sub_type": "pc",
  "cookie_string": "cookie文本",
  "sync_creator": false
}
```

行为：
- 解析 Cookie 文本，获取用户信息
- PC 类型自动调用 XHS 自身接口补充用户资料
- `sync_creator=true` 时自动同步创作者端账号（PC Cookie 换取创作者端 Cookie）
- Cookie 使用 Fernet 加密存储

响应：`AccountOut`（含 `action` 字段：`created` / `updated`）。

### 16.3 检查账号状态

`POST /api/accounts/{account_id}/check`

行为：使用存储的 Cookie 验证账号是否有效，更新状态（`active` / `expired`）。

响应：`AccountOut`。

### 16.4 更新账号

`PATCH /api/accounts/{account_id}`

响应：`{"id": account_id, "status": "updated"}`

### 16.5 删除账号

`DELETE /api/accounts/{account_id}`

行为：删除账号及其所有 Cookie 版本记录。

响应：`{"id": account_id, "status": "deleted"}`

### 16.6 Cookie 状态总览

`GET /api/accounts/cookie-status`

行为：按平台汇总当前用户的账号和 Cookie 可用状态。

响应：

```json
{
  "platforms": [
    {
      "platform": "xhs",
      "total_accounts": 2,
      "active_accounts": 1,
      "expired_accounts": 1,
      "cookies_available": true,
      "crawl_ready": true
    }
  ]
}
```

---

## 十七、登录会话 Login Sessions

路由前缀：`/api/xhs/login-sessions`

所有接口需要认证。

### 17.1 PC 端 QR 码登录

`POST /api/xhs/login-sessions/pc/qrcode`

请求体（可选）：

```json
{ "sync_creator": false }
```

行为：生成小红书 PC 端登录二维码，创建登录会话。

响应：

```json
{
  "session_id": 1,
  "status": "pending",
  "qr_url": "https://...",
  "qr_image_data_url": "data:image/png;base64,..."
}
```

### 17.2 创作者端 QR 码登录

`POST /api/xhs/login-sessions/creator/qrcode`

行为：生成小红书创作者端登录二维码。

响应：同 PC 端。

### 17.3 手机验证码发送

`POST /api/xhs/login-sessions/phone/send-code`

请求体：

```json
{
  "phone": "13800138000",
  "sync_creator": false
}
```

行为：向手机发送验证码，创建登录会话。

响应：

```json
{
  "session_id": 1,
  "status": "pending",
  "phone_mask": "138****8000"
}
```

### 17.4 手机验证码确认

`POST /api/xhs/login-sessions/phone/confirm`

请求体：

```json
{
  "session_id": 1,
  "phone": "13800138000",
  "code": "123456",
  "sync_creator": null
}
```

行为：确认手机验证码，完成登录。Cookie 转存至 `account_cookie_versions`，创建平台账号。

响应：`AccountOut`。

### 17.5 QR 码登录确认（轮询）

`POST /api/xhs/login-sessions/{session_id}/confirm`

行为：检查 QR 码是否已扫码确认。已确认则创建平台账号并保存 Cookie。

响应：

```json
{
  "status": "confirmed",
  "account": { ... }
}
```

---

## 十八、笔记 Notes

路由前缀：`/api/notes`

所有接口需要认证。

### 18.1 笔记列表

`GET /api/notes`

查询参数：

- `platform`（可选）
- `keyword`（可选，在 title/content 中模糊匹配）
- `tag_id`（可选，按标签过滤）
- `page` / `page_size`

响应：`paginated([NoteOut])`。

`NoteOut` 字段：`id, platform, note_id, title, content, author_name, created_at`。

### 18.2 笔记详情

`GET /api/notes/{note_db_id}`

响应：`NoteOut` + `assets`（素材列表）+ `comments`（评论列表）+ `tags`（标签列表）。

### 18.3 批量保存笔记

`POST /api/notes/batch-save`

请求体：

```json
{
  "account_id": 1,
  "note_ids": ["note_id_1", "note_id_2"],
  "fetch_comments": false
}
```

行为：使用指定账号的 Cookie 调用 XHS PC API 获取笔记详情，保存笔记、素材和评论。已存在的笔记跳过。

响应：`{"saved_count": 2, "skipped_count": 0}`

### 18.4 笔记关联标签

`POST /api/notes/{note_db_id}/tags`

请求体：

```json
{ "tag_ids": [1, 2, 3] }
```

行为：为笔记设置标签关联（替换已有标签）。

响应：`{"note_id": 1, "tag_ids": [1, 2, 3]}`

### 18.5 删除笔记

`DELETE /api/notes/{note_db_id}`

响应：`{"id": note_db_id, "status": "deleted"}`

### 18.6 导出笔记

`POST /api/notes/export`

请求体：

```json
{
  "note_ids": ["note_id_1", "note_id_2"],
  "format": "json"
}
```

`format` 可选值：`json` / `csv`。

---

## 十九、AI 创作 AI

路由前缀：`/api/ai`

所有接口需要认证。所有 AI 操作会创建 Task 记录用于追踪。

### 19.1 笔记改写

`POST /api/ai/rewrite`

请求体：

```json
{
  "draft_id": 1,
  "instruction": "改写为更口语化的风格"
}
```

行为：基于已有草稿，使用默认文本模型改写内容。更新草稿的 title 和 body。

响应：`success_response(DraftOut)`

### 19.2 笔记生成

`POST /api/ai/generate`

请求体：

```json
{
  "platform": "xhs",
  "topic": "信用贷攻略",
  "reference": "参考内容",
  "instruction": "生成小红书风格笔记"
}
```

行为：使用默认文本模型生成新笔记，创建 AI 草稿。

响应：`success_response(DraftOut)`

### 19.3 标题生成

`POST /api/ai/generate-title`

请求体：

```json
{
  "title": "原标题",
  "body": "正文内容",
  "count": 5
}
```

行为：生成多个标题候选（1-10 个）。

响应：`success_response({"titles": ["标题1", "标题2", ...]})`

### 19.4 标签生成

`POST /api/ai/generate-tags`

请求体：

```json
{
  "title": "标题",
  "body": "正文",
  "count": 8
}
```

行为：生成标签候选（1-20 个）。

响应：`success_response({"tags": ["标签1", "标签2", ...]})`

### 19.5 文本润色

`POST /api/ai/polish`

请求体：

```json
{
  "text": "待润色文本",
  "instruction": "使其更专业"
}
```

响应：`success_response({"polished_text": "..."})`

### 19.6 封面图生成

`POST /api/ai/generate-cover`

请求体：

```json
{
  "prompt": "金融主题封面",
  "draft_id": null,
  "size": "1024x1024",
  "style": "clean"
}
```

行为：使用默认图片模型生成封面图，保存为 `ai_generated_assets` 记录。

响应：`success_response(GeneratedAssetOut)`

### 19.7 图片生成

`POST /api/ai/generate-image`

请求体：

```json
{
  "prompt": "一张信用卡图片",
  "reference_images": [],
  "save_to_assets": true
}
```

响应：`success_response(GeneratedAssetOut)`

### 19.8 图片描述

`POST /api/ai/describe-image`

请求体：

```json
{
  "image_url": "https://...",
  "instruction": "描述这张图片"
}
```

响应：`success_response({"description": "..."})`

---

## 二十、草稿 Drafts

路由前缀：`/api/drafts`

所有接口需要认证。

### 20.1 草稿列表

`GET /api/drafts`

查询参数：

- `platform`（可选）
- `page` / `page_size`

响应：`success_response(paginated([DraftOut]))`。

`DraftOut` 字段：`id, platform, title, body, tags, source_note_id, intent, status, created_at`。

### 20.2 创建草稿

`POST /api/drafts`

请求体：

```json
{
  "platform": "xhs",
  "source_note_id": null,
  "title": "草稿标题",
  "body": "草稿正文",
  "intent": "publish"
}
```

行为：创建草稿。如指定 `source_note_id`，自动复制源笔记的标题、正文、标签和素材。

响应：`success_response(DraftOut)`

### 20.3 更新草稿

`PATCH /api/drafts/{draft_id}`

请求体：

```json
{
  "title": "新标题",
  "body": "新正文",
  "tags": [{"name": "标签1"}]
}
```

响应：`success_response(DraftOut)`

### 20.4 发送至发布中心

`POST /api/drafts/{draft_id}/send-to-publish`

请求体：

```json
{
  "platform_account_id": 1,
  "publish_mode": "immediate",
  "scheduled_at": null,
  "topics": ["话题1"],
  "location": "上海",
  "privacy_type": 0,
  "is_private": false
}
```

行为：将草稿转为发布任务（`publish_jobs`），草稿素材同步为发布素材。

响应：`success_response(PublishJobOut)`

### 20.5 删除草稿

`DELETE /api/drafts/{draft_id}`

响应：`success_response({"id": draft_id, "status": "deleted"})`

---

## 二十一、发布 Publish

路由前缀：`/api/publish`

所有接口需要认证。

### 21.1 发布任务列表

`GET /api/publish`

查询参数：

- `status`（可选）
- `page` / `page_size`

响应：`paginated([PublishJobOut])`。

`PublishJobOut` 字段：`id, platform_account_id, source_draft_id, platform, title, body, publish_mode, publish_options, status, scheduled_at, external_note_id, publish_error, published_at, created_at`。

- `publish_mode`：`immediate` / `scheduled`
- `status`：`pending` / `uploading` / `publishing` / `published` / `failed`

### 21.2 创建发布任务

`POST /api/publish`

请求体：

```json
{
  "platform_account_id": 1,
  "source_draft_id": 1,
  "title": "发布标题",
  "body": "发布正文",
  "publish_mode": "immediate",
  "topics": ["话题1"],
  "location": "上海",
  "is_private": false
}
```

响应：`success_response(PublishJobOut)`

### 21.3 更新发布任务

`PATCH /api/publish/{job_id}`

请求体（所有字段可选）：

```json
{
  "title": "新标题",
  "body": "新正文",
  "platform_account_id": 2,
  "publish_mode": "scheduled",
  "scheduled_at": "2026-05-21T10:00:00Z",
  "topics": ["新话题"],
  "location": "北京",
  "privacy_type": 1
}
```

响应：`success_response(PublishJobOut)`

### 21.4 执行发布

`POST /api/publish/{job_id}/execute`

行为：
1. 获取创作者端账号 Cookie
2. 上传素材（图片/视频）至创作者端
3. 调用创作者端发布接口
4. 更新发布状态和外部笔记 ID

响应：`success_response(PublishJobOut)`

### 21.5 发布任务详情

`GET /api/publish/{job_id}`

响应：`success_response(PublishJobOut)`

### 21.6 添加发布素材

`POST /api/publish/{job_id}/assets`

请求体：

```json
{
  "asset_type": "image",
  "file_path": "/path/to/image.png"
}
```

响应：`success_response(PublishAssetOut)`

`PublishAssetOut` 字段：`id, publish_job_id, asset_type, file_path, upload_status, creator_media_id, upload_error, creator_upload_info`。

- `upload_status`：`pending` / `uploaded` / `failed`

### 21.7 删除发布任务

`DELETE /api/publish/{job_id}`

响应：`success_response({"id": job_id, "status": "deleted"})`

---

## 二十二、文件管理 Files

路由前缀：`/api/files`

所有接口需要认证。文件按用户 ID 前缀隔离。

### 22.1 用户图片列表

`GET /api/files/images`

响应：`success_response({"items": [{"file_name": "...", "url": "/api/files/media/...", "size": 12345}]})`

### 22.2 删除图片

`DELETE /api/files/images/{file_name}`

行为：删除指定图片文件（仅限当前用户拥有的文件）。

响应：`success_response({"deleted": true})`

### 22.3 上传图片

`POST /api/files/upload-image`

请求体：`multipart/form-data`，字段 `file`。

行为：上传图片文件，文件名以 `xhs-upload-u{user_id}-` 前缀存储。

响应：`success_response({"file_name": "...", "download_url": "/api/files/media/..."})`

### 22.4 下载媒体文件

`GET /api/files/media/{file_name}`

行为：下载指定媒体文件（图片/视频）。校验文件归属（用户 ID 前缀）。

响应：`FileResponse`

### 22.5 合成封面图

`POST /api/files/compose-image`

请求体：

```json
{
  "title": "封面标题",
  "body": "副标题",
  "width": 1080,
  "height": 1440,
  "background_color": "#fafaf8",
  "accent_color": "#111111"
}
```

行为：使用 Pillow 合成封面图，保存为 PNG 文件。

响应：`success_response({"file_name": "...", "download_url": "...", "width": 1080, "height": 1440})`

### 22.6 图片缩放裁剪

`POST /api/files/resize-image`

请求体：

```json
{
  "source_file_name": "原始文件名",
  "width": 1080,
  "height": 1440,
  "mode": "cover",
  "format": "png",
  "quality": 90
}
```

- `mode`：`cover`（裁剪填满）/ `contain`（等比缩放留白）

响应：`success_response({"file_name": "...", "download_url": "...", "width": 1080, "height": 1440})`

---

## 二十三、关键词组 Keyword Groups

路由前缀：`/api/keyword-groups`

所有接口需要认证。

### 23.1 关键词组列表

`GET /api/keyword-groups`

查询参数：

- `platform`（可选）
- `page` / `page_size`

响应：`paginated([KeywordGroupOut])`。

`KeywordGroupOut` 字段：`id, platform, name, keywords, created_at, updated_at`。

### 23.2 创建关键词组

`POST /api/keyword-groups`

请求体：

```json
{
  "platform": "xhs",
  "name": "信用贷关键词",
  "keywords": ["信用贷", "征信花了"]
}
```

- `platform` 可选值：`xhs` / `douyin` / `kuaishou` / `weibo` / `xianyu` / `taobao`
- `keywords`：1-50 个关键词，自动去重

响应：`KeywordGroupOut`

### 23.3 更新关键词组

`PATCH /api/keyword-groups/{group_id}`

请求体：

```json
{
  "name": "新名称",
  "keywords": ["新关键词1", "新关键词2"]
}
```

响应：`KeywordGroupOut`

### 23.4 删除关键词组

`DELETE /api/keyword-groups/{group_id}`

响应：`success_response({"id": group_id, "status": "deleted"})`

---

## 二十四、标签 Tags

路由前缀：`/api/tags`

所有接口需要认证。同一用户下标签名称唯一。

### 24.1 标签列表

`GET /api/tags`

查询参数：`page` / `page_size`（默认 100）

响应：`paginated([TagOut])`。

`TagOut` 字段：`id, name, color`。

### 24.2 创建标签

`POST /api/tags`

请求体：

```json
{
  "name": "标签名称",
  "color": "#111111"
}
```

响应：`TagOut`

### 24.3 更新标签

`PATCH /api/tags/{tag_id}`

请求体：

```json
{
  "name": "新名称",
  "color": "#FF0000"
}
```

响应：`TagOut`

### 24.4 删除标签

`DELETE /api/tags/{tag_id}`

行为：删除标签及其所有笔记关联。

响应：`success_response({"id": tag_id, "status": "deleted"})`

---

## 二十五、模型配置 Model Configs

路由前缀：`/api/model-configs`

所有接口需要认证。API Key 使用 Fernet 加密存储。

### 25.1 模型配置列表

`GET /api/model-configs`

查询参数：

- `model_type`（可选）：`text` / `image`
- `page` / `page_size`

响应：`success_response(paginated([ModelConfigOut]))`。

`ModelConfigOut` 字段：`id, name, model_type, provider, model_name, base_url, has_api_key, is_default`。

- `has_api_key`：bool，是否已配置 API Key（不返回实际值）

### 25.2 创建模型配置

`POST /api/model-configs`

请求体：

```json
{
  "name": "GPT-5.4",
  "model_type": "text",
  "provider": "openai",
  "model_name": "gpt-5.4",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "is_default": true
}
```

行为：创建模型配置，API Key 加密存储。`is_default=true` 时自动清除同类型其他默认标记。

响应：`success_response(ModelConfigOut)`

### 25.3 更新模型配置

`PATCH /api/model-configs/{config_id}`

请求体（所有字段可选）：

```json
{
  "name": "新名称",
  "provider": "新提供商",
  "model_name": "新模型",
  "base_url": "新URL",
  "api_key": "新Key",
  "is_default": true
}
```

响应：`success_response(ModelConfigOut)`

### 25.4 删除模型配置

`DELETE /api/model-configs/{config_id}`

响应：`success_response({"id": config_id, "status": "deleted"})`

---

## 二十六、通知 Notifications

路由前缀：`/api/notifications`

所有接口需要认证。

### 26.1 通知列表

`GET /api/notifications`

查询参数：

- `unread`（可选，bool）：仅返回未读通知
- `level`（可选）：`info` / `warning` / `error` / `success`
- `source_type`（可选）：`crawl_task` / `lead` / `task` / `account` / `account_expired` / `publish_job`
- `page` / `page_size`

响应：`success_response(paginated([NotificationOut]))`。

`NotificationOut` 字段：`id, title, body, level, source_task_id, source_type, source_id, is_read, created_at`。

### 26.2 未读计数

`GET /api/notifications/unread-count`

响应：

```json
{
  "success": true,
  "data": {
    "count": 5,
    "breakdown": {"info": 2, "warning": 2, "error": 1}
  }
}
```

### 26.3 标记已读

`POST /api/notifications/{notification_id}/read`

响应：`success_response(NotificationOut)`

### 26.4 全部标记已读

`POST /api/notifications/read-all`

响应：`success_response({"marked": 5})`

---

## 二十七、任务中心 Tasks

路由前缀：`/api/tasks`

所有接口需要认证。

### 27.1 任务列表

`GET /api/tasks`

查询参数：

- `platform`（可选）
- `page` / `page_size`

响应：`success_response(paginated([TaskOut]))`。

`TaskOut` 字段：`id, platform, task_type, status, progress, payload, created_at, started_at, finished_at, duration_ms, error_type, retry_count, max_retries, parent_task_id`。

- `status`：`pending` / `running` / `completed` / `failed`
- `duration_ms`：任务耗时（毫秒），由 `started_at` 和 `finished_at` 计算
- `parent_task_id`：父任务 ID，支持子任务层级

### 27.2 任务详情

`GET /api/tasks/{task_id}`

响应：`success_response(TaskOut)` + `children`（子任务列表）。

### 27.3 调度器状态

`GET /api/tasks/scheduler/status`

响应：

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "running": true,
    "jobs": [...],
    "recent_tasks": [TaskOut, ...]
  }
}
```

---

## 二十八、XHS 数据洞察 Analytics

路由前缀：`/api/xhs/analytics`

所有接口需要认证。

### 28.1 运营总览

`GET /api/xhs/analytics/overview`

响应：

```json
{
  "platform": "xhs",
  "today_crawls": 0,
  "saved_notes": 10,
  "pending_publishes": 0,
  "healthy_accounts": 1,
  "at_risk_accounts": 0,
  "comment_count": 0,
  "total_engagement": 0,
  "hot_topics": [],
  "recent_activity": []
}
```

### 28.2 热门内容

`GET /api/xhs/analytics/top-content`

响应：`{"items": []}`

### 28.3 热门话题

`GET /api/xhs/analytics/hot-topics`

响应：`{"items": []}`

### 28.4 评论分析

`GET /api/xhs/analytics/comment-insights`

响应：

```json
{
  "total_comments": 0,
  "question_count": 0,
  "top_terms": [],
  "top_comments": []
}
```

### 28.5 竞品对标

`GET /api/xhs/analytics/benchmarks`

响应：`{"targets": [], "summary": {}}`

### 28.6 竞品对标创建草稿

`POST /api/xhs/analytics/benchmarks/{target_id}/create-drafts`

查询参数：`limit`（默认 5，1-20）

响应：`{"created_count": 0, "draft_ids": []}`

### 28.7 生成报告

`POST /api/xhs/analytics/reports`

响应：报告数据。

---

## 二十九、XHS 自动运营 Auto Ops

路由前缀：`/api/xhs/auto-ops`

所有接口需要认证。

### 29.1 自动任务列表

`GET /api/xhs/auto-ops/tasks`

查询参数：`page` / `page_size`

响应：`paginated([AutoTaskOut])`。

`AutoTaskOut` 字段：`id, user_id, name, keywords, pc_account_id, creator_account_id, ai_instruction, status, last_run_at, next_run_at, total_published, created_at, schedule_type, schedule_time, schedule_days, schedule_interval_hours`。

- `status`：`active` / `paused`
- `schedule_type`：`manual` / `scheduled` / `periodic`

### 29.2 创建自动任务

`POST /api/xhs/auto-ops/tasks`

请求体：

```json
{
  "name": "每日自动发布",
  "keywords": ["信用贷", "征信"],
  "pc_account_id": 1,
  "creator_account_id": 2,
  "ai_instruction": "生成小红书风格笔记",
  "schedule_type": "manual",
  "schedule_time": "",
  "schedule_days": "",
  "schedule_interval_hours": 0
}
```

响应：`AutoTaskOut`

### 29.3 更新自动任务

`PATCH /api/xhs/auto-ops/tasks/{task_id}`

请求体（所有字段可选）：

```json
{
  "name": "新名称",
  "keywords": ["新关键词"],
  "ai_instruction": "新指令",
  "status": "paused",
  "schedule_type": "periodic",
  "schedule_interval_hours": 24
}
```

响应：`AutoTaskOut`

### 29.4 删除自动任务

`DELETE /api/xhs/auto-ops/tasks/{task_id}`

响应：`success_response({"id": task_id, "status": "deleted"})`

### 29.5 执行自动任务

`POST /api/xhs/auto-ops/tasks/{task_id}/execute`

行为：手动触发自动运营任务执行。

响应：`success_response(AutoTaskOut)`

---

## 三十、XHS 监控 Monitoring

路由前缀：`/api/xhs/monitoring`

所有接口需要认证。底层复用 `monitor_sources` 表，仅展示 `platform=xhs` 的记录。

### 30.1 监控目标列表

`GET /api/xhs/monitoring/targets`

查询参数：`page` / `page_size`

响应：`paginated([MonitoringTargetOut])`。

`MonitoringTargetOut` 字段：`id, platform, target_type, name, value, status, config, last_refreshed_at, created_at, updated_at`。

- `status`：`active` / `paused`（映射自 `monitor_sources.enabled`）

### 30.2 创建监控目标

`POST /api/xhs/monitoring/targets`

请求体：

```json
{
  "target_type": "keyword",
  "name": "信用贷监控",
  "value": "信用贷",
  "status": "active",
  "config": {}
}
```

响应：`MonitoringTargetOut`

### 30.3 刷新监控目标

`POST /api/xhs/monitoring/targets/{target_id}/refresh`

行为：更新 `last_crawled_at`，返回快照数据。

响应：

```json
{
  "target": { ... },
  "task": {"id": 0, "status": "pending"},
  "snapshot": {"id": 0, "target_id": 1, "payload": {}, "created_at": "..."}
}
```

### 30.4 删除监控目标

`DELETE /api/xhs/monitoring/targets/{target_id}`

响应：`success_response({"id": target_id, "status": "deleted"})`

---

## 三十一、视频工坊 Video Studio

路由前缀：`/api/video-studio`

所有接口需要认证。文件按用户 ID 前缀隔离。

### 31.1 视频列表

`GET /api/video-studio/videos`

查询参数：`page` / `page_size`

响应：`success_response(paginated([VideoOut]))`。

### 31.2 上传视频

`POST /api/video-studio/upload`

请求体：`multipart/form-data`，字段 `file`。

行为：上传视频文件，文件名以 `xhs-video-u{user_id}-` 前缀存储。

响应：`success_response({"file_name": "...", "download_url": "...", "media_type": "video/mp4"})`

### 31.3 截取封面帧

`POST /api/video-studio/extract-cover`

请求体：

```json
{
  "video_file_name": "视频文件名",
  "timestamp_seconds": 0.0,
  "width": 1080,
  "height": 1440
}
```

行为：使用 ffmpeg 从视频中截取指定时间点的画面作为封面图。

响应：`success_response({"file_name": "...", "download_url": "...", "width": 1080, "height": 1440})`

### 31.4 AI 视频描述

`POST /api/video-studio/describe-video`

请求体：

```json
{
  "video_url": "https://...",
  "instruction": "描述视频内容"
}
```

行为：使用默认文本模型生成视频内容描述。

响应：`success_response({"description": "..."})`

---

## 三十二、其他说明

- `mock` / `playwright` / `external_api` / `generic_web` 采集器（代码文件存在但 CollectorFactory 不路由）
- 所有采集任务通过 `CrawlTaskQueue` 队列管理，同一时间仅执行一个采集任务
- 定时采集调度器使用 APScheduler，每分钟检查一次需要触发的监控源
- 小红书运营模块所有接口需要 JWT Bearer Token 认证
- Cookie 使用 Fernet 对称加密存储，密钥由 `SECRET_KEY` 派生
- AI 操作自动创建 Task 记录，支持任务追踪和错误处理
- 文件存储按用户 ID 前缀隔离，确保用户间文件不可互访
- API Key 使用 Fernet 加密存储，接口仅返回 `has_api_key` 布尔值

---

## 三十三、智能体 Agent

路由前缀：`/api/agent`

所有接口需要认证。基于 LangGraph 的 ReAct (Reasoning + Acting) 智能体，支持多轮对话和工具调用。

### 33.1 智能体对话

`POST /api/agent/chat`

请求体：

```json
{
  "query": "帮我生成一条针对'急需5万周转'的跟进话术",
  "thread_id": null,
  "max_iterations": 8
}
```

- `query`：用户问题（1-6000 字符）
- `thread_id`：对话线程 ID，传入则继续多轮对话，不传则新建对话
- `max_iterations`：最大思考-行动迭代次数（1-20，默认 8）

行为：
1. 获取用户默认文本模型配置
2. 构建 RAG 查询引擎和结构化 LLM 客户端
3. 如有 `thread_id`，从数据库加载历史对话上下文
4. 运行 ReAct Agent 图（思考 → 行动 → 观察 循环）
5. 保存对话记录到数据库和 WorkflowRun

响应：

```json
{
  "success": true,
  "data": {
    "thread_id": "abc123",
    "final_answer": "针对'急需5万周转'的客户，建议话术如下：...",
    "iterations": 3,
    "tool_history": [
      {"action": "knowledge_search", "action_input": {"query": "周转话术"}, "success": true, "observation": "..."},
      {"action": "script_generate", "action_input": {"text": "急需5万周转", "lead_level": "A"}, "success": true, "observation": "..."},
      {"action": "compliance_check", "action_input": {"content": "生成的话术内容"}, "success": true, "observation": "..."}
    ]
  }
}
```

### 33.2 工具列表

`GET /api/agent/tools`

行为：返回智能体可用的全部工具定义。

响应：

```json
{
  "success": true,
  "data": [
    {
      "name": "knowledge_search",
      "description": "检索知识库素材。可以搜索产品资料、平台规则、优质话术等。",
      "parameters": { ... }
    },
    {
      "name": "compliance_check",
      "description": "合规审核工具。检查营销内容是否包含违规表述。",
      "parameters": { ... }
    },
    {
      "name": "script_generate",
      "description": "话术生成工具。根据客户评论和需求类型生成个性化跟进话术。",
      "parameters": { ... }
    },
    {
      "name": "lead_score",
      "description": "线索评分工具。使用规则引擎对文本进行快速评分。",
      "parameters": { ... }
    },
    {
      "name": "quality_eval",
      "description": "内容质量评估工具。评估营销内容的整体质量。",
      "parameters": { ... }
    }
  ]
}
```

工具详细说明：

| 工具 | 功能 | 参数 |
|------|------|------|
| `knowledge_search` | 检索知识库素材（产品资料、平台规则、优质话术） | `query`(必填), `source_types`(可选: material/platform_rule/quality_script), `top_k`(默认5) |
| `compliance_check` | 合规审核，检查违规表述 | `content`(必填) |
| `script_generate` | 生成 2-3 个不同风格的跟进话术 | `text`(必填), `demand_type`(可选), `lead_level`(默认C: A/B/C/D) |
| `lead_score` | 规则引擎快速评分，返回 0-100 分和 A/B/C/D 等级 | `text`(必填) |
| `quality_eval` | 评估内容质量，返回 0-1 评分和改进建议 | `content`(必填), `topic`(可选) |

### 33.3 会话列表

`GET /api/agent/conversations`

查询参数：

- `limit`（可选，默认 20）：返回最近 N 个会话

响应：

```json
{
  "success": true,
  "data": [
    {
      "thread_id": "abc123",
      "last_message": "针对'急需5万周转'的客户...",
      "message_count": 5,
      "created_at": "2026-06-01T10:00:00"
    }
  ]
}
```

### 33.4 会话详情

`GET /api/agent/conversations/{thread_id}`

响应：

```json
{
  "success": true,
  "data": {
    "thread_id": "abc123",
    "message_count": 5,
    "messages": [
      {"role": "user", "content": "帮我生成话术", "tool_calls": [], "metadata": {}},
      {"role": "assistant", "content": "好的，我来为您生成...", "tool_calls": [...], "metadata": {"iterations": 3}},
      {"role": "tool", "content": "搜索结果...", "metadata": {"tool_name": "knowledge_search", "success": true}}
    ]
  }
}
```

### 33.5 删除会话

`DELETE /api/agent/conversations/{thread_id}`

行为：删除指定会话及其所有消息记录。

响应：`success_response({"thread_id": "abc123", "deleted_count": 5})`

---

## 三十四、知识库 Knowledge

路由前缀：`/api/knowledge`

所有接口需要认证。基于 LlamaIndex + ChromaDB 的 RAG 知识库，支持文档索引、语义检索和智能问答。

### 34.1 知识条目列表

`GET /api/knowledge/entries`

查询参数：

- `source_type`（可选）：素材类型过滤
- `page` / `page_size`

响应：`paginated([KnowledgeEntryOut])`。

`KnowledgeEntryOut` 字段：`id, source_type, source_id, content(截断200字), embedding_id, metadata, created_at`。

### 34.2 知识库统计

`GET /api/knowledge/stats`

响应：

```json
{
  "success": true,
  "data": {
    "total": 50,
    "by_type": {
      "material": 30,
      "platform_rule": 10,
      "quality_script": 10
    },
    "chroma": {
      "collection_name": "user_1_knowledge",
      "document_count": 50,
      "available": true
    }
  }
}
```

### 34.3 索引知识

`POST /api/knowledge/index`

请求体：

```json
{
  "source_type": "material",
  "note_ids": [1, 2, 3]
}
```

行为：将指定笔记内容索引到 ChromaDB 向量数据库。`source_type` 为 `material` 时，从笔记表读取内容进行索引。

响应：

```json
{
  "success": true,
  "data": {
    "indexed": 3,
    "skipped": 0,
    "failed": 0
  }
}
```

### 34.4 索引全部笔记

`POST /api/knowledge/index-all-notes`

行为：将当前用户所有笔记（最多 100 条）批量索引到 ChromaDB。

响应：

```json
{
  "success": true,
  "data": {
    "indexed": 20,
    "skipped": 5,
    "failed": 0
  }
}
```

### 34.5 语义检索

`POST /api/knowledge/search`

请求体：

```json
{
  "query": "信用贷话术",
  "top_k": 5,
  "source_types": ["material", "quality_script"]
}
```

行为：基于查询文本进行语义检索，返回最相关的知识条目。

响应：

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "content": "相关内容...",
        "score": 0.92,
        "source_type": "quality_script",
        "metadata": { ... }
      }
    ],
    "count": 5
  }
}
```

### 34.6 知识问答

`POST /api/knowledge/query`

请求体：

```json
{
  "query": "小红书发布有哪些合规注意事项？",
  "similarity_top_k": 5,
  "response_mode": "tree_summarize"
}
```

行为：基于 RAG 的智能问答，先检索相关文档，再由 LLM 生成回答。`response_mode` 可选值：`tree_summarize` / `refine` / `compact`。

响应：`success_response({"answer": "...", "source_nodes": [...]})`

### 34.7 删除知识条目

`DELETE /api/knowledge/entries/{entry_id}`

行为：删除知识条目，同时从 ChromaDB 中移除对应向量。

响应：`success_response({"id": entry_id, "status": "deleted"})`

---

## 三十五、合规规则 Compliance Rules

路由前缀：`/api/compliance-rules`

所有接口需要认证。管理营销内容的合规审核规则，用于工作流中的合规检查节点。

### 35.1 规则列表

`GET /api/compliance-rules`

查询参数：

- `category`（可选）：规则类别过滤
- `severity`（可选）：严重程度过滤
- `is_active`（可选，bool）：是否仅返回启用的规则
- `page` / `page_size`

响应：`paginated([ComplianceRuleOut])`。

`ComplianceRuleOut` 字段：`id, category, rule_text, rule_description, severity, is_active, created_at, updated_at`。

- `category`：规则类别，如 `platform_rule`（平台规则）、`industry_regulation`（行业规范）、`internal_policy`（内部策略）
- `severity`：严重程度，`low` / `medium` / `high` / `critical`

### 35.2 创建规则

`POST /api/compliance-rules`

请求体：

```json
{
  "category": "platform_rule",
  "rule_text": "不得包含微信号、二维码等站外引流信息",
  "rule_description": "小红书社区规范",
  "severity": "high"
}
```

响应：`success_response(ComplianceRuleOut)`

### 35.3 更新规则

`PATCH /api/compliance-rules/{rule_id}`

请求体（所有字段可选）：

```json
{
  "category": "industry_regulation",
  "rule_text": "更新后的规则文本",
  "severity": "critical",
  "is_active": false
}
```

响应：`success_response(ComplianceRuleOut)`

### 35.4 删除规则

`DELETE /api/compliance-rules/{rule_id}`

响应：`success_response({"id": rule_id, "status": "deleted"})`

### 35.5 初始化默认规则

`POST /api/compliance-rules/seed-defaults`

行为：为当前用户创建默认合规规则（仅在用户无任何规则时生效）。默认规则包含 9 条：

| 类别 | 规则 | 严重程度 |
|------|------|----------|
| platform_rule | 不得承诺包下款、百分百通过等绝对化表述 | critical |
| platform_rule | 不得包含微信号、二维码等站外引流信息 | high |
| platform_rule | 不得使用夸张标题党吸引点击 | medium |
| industry_regulation | 不得暗示内部渠道、特殊通道办理贷款 | high |
| industry_regulation | 不得宣传零利息、免息等不实利率信息 | critical |
| industry_regulation | 不得引导黑户包装、刷流水等违规操作 | critical |
| internal_policy | 话术中应包含风险提示 | medium |
| internal_policy | 不得直接报价利率，应引导线下咨询 | medium |
| internal_policy | 首次接触不应过度推销，以咨询为主 | low |

响应：

```json
{
  "success": true,
  "data": {
    "message": "已有规则，跳过初始化",
    "created_count": 9
  }
}
```

---

## 三十六、工作流 Workflows

路由前缀：`/api/workflows`

所有接口需要认证。基于 LangGraph 的工作流引擎，支持线索评分、话术生成、内容发布审核三种工作流。

### 36.1 线索评分工作流

`POST /api/workflows/lead-scoring`

请求体：

```json
{
  "text": "征信花了急需5万周转",
  "platform": "xhs",
  "source_id": 1,
  "source_type": "keyword",
  "source_post_id": 10,
  "source_comment_id": 50,
  "user_name": "用户A",
  "user_profile_url": "https://..."
}
```

所有字段除 `text` 外均可选。

行为：
1. **规则预筛**（rule_prescreen）：使用规则引擎快速评分，判断是否为潜在线索
2. **AI 线索识别**（ai_lead_identify）：使用 LLM 深度分析，输出置信度、线索等级、需求类型、紧急度、关键证据等
3. **线索持久化**（lead_persist）：将结果保存到 leads 表

响应：

```json
{
  "success": true,
  "data": {
    "workflow_id": "abc123",
    "state": "completed",
    "rule_score": 75,
    "rule_level": "A",
    "ai_result": {
      "is_potential_lead": true,
      "confidence": 0.92,
      "lead_level": "A",
      "demand_type": "借款需求",
      "urgency": "high",
      "demand_summary": "用户征信有问题，急需5万元周转",
      "key_evidence": ["征信花了", "急需5万", "周转"],
      "estimated_amount": "5万",
      "risk_flags": [],
      "reasoning": "..."
    },
    "lead_id": 42
  }
}
```

### 36.2 话术生成工作流

`POST /api/workflows/script-generation`

请求体：

```json
{
  "lead_id": 42,
  "demand_type": "借款需求",
  "lead_level": "A"
}
```

- `lead_id`：必填，关联的线索 ID
- `demand_type`：可选，默认使用线索的需求类型
- `lead_level`：可选，默认使用线索的等级

行为：
1. **RAG 检索**（rag_retrieve）：从知识库检索参考素材、平台规则、优质话术
2. **AI 话术生成**（ai_script_generate）：基于检索结果和线索信息，生成 2-3 个不同风格的话术候选
3. **合规检查**（compliance_check）：检查生成的话术是否合规
4. **风险门控**（risk_gate）：根据合规风险等级决定自动通过或进入人工审批

响应：

```json
{
  "success": true,
  "data": {
    "workflow_id": "def456",
    "state": "completed",
    "scripts": {
      "candidates": [
        {"style": "专业咨询", "text": "...", "compliance_notes": "..."},
        {"style": "亲和关怀", "text": "...", "compliance_notes": "..."}
      ],
      "recommended_index": 0,
      "rag_sources": ["知识条目1", "知识条目2"]
    },
    "compliance": {
      "is_compliant": true,
      "risk_level": "low",
      "violations": [],
      "suggestions": []
    },
    "risk_gate": {
      "auto_approve": true,
      "gate_decision": "auto_approved"
    }
  }
}
```

### 36.3 内容发布审核工作流

`POST /api/workflows/content-publish-check`

请求体：

```json
{
  "draft_id": 5,
  "publish_job_id": null,
  "title": "信用贷攻略",
  "body": "笔记正文内容..."
}
```

- `draft_id` / `publish_job_id`：可选，关联的草稿或发布任务 ID
- `title` / `body`：可选，直接传入内容（如有关联草稿/发布任务则自动填充）

行为：
1. **AI 质量评估**（ai_quality_eval）：评估内容的相关性、完整性、可读性
2. **合规检查**（compliance_check）：检查内容是否违反合规规则
3. **风险门控**（risk_gate）：根据质量和合规结果决定自动通过或进入人工审批

响应：

```json
{
  "success": true,
  "data": {
    "workflow_id": "ghi789",
    "state": "completed",
    "quality": {
      "overall_score": 0.85,
      "relevance_score": 0.9,
      "completeness_score": 0.8,
      "readability_score": 0.85,
      "issues": [],
      "suggestions": ["可以增加具体案例"]
    },
    "compliance": {
      "is_compliant": true,
      "risk_level": "low",
      "violations": [],
      "suggestions": []
    },
    "risk_gate": {
      "auto_approve": true,
      "gate_decision": "auto_approved"
    }
  }
}
```

### 36.4 工作流运行记录列表

`GET /api/workflows/runs`

查询参数：

- `workflow_type`（可选）：`lead_scoring` / `script_generation` / `content_publish` / `agent_react`
- `state`（可选）：`pending` / `running` / `paused` / `completed` / `failed` / `cancelled`
- `page` / `page_size`

响应：`paginated([WorkflowRunOut])`。

`WorkflowRunOut` 字段：`id, workflow_id, workflow_type, state, input_data, output_data, current_node, paused_at_node, error_node, error_message, retry_count, parent_workflow_id, created_at, updated_at, completed_at`。

### 36.5 工作流运行详情

`GET /api/workflows/runs/{workflow_id}`

响应：`success_response(WorkflowRunOut)`

### 36.6 工作流日志

`GET /api/workflows/runs/{workflow_id}/logs`

响应：

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "workflow_id": "abc123",
      "node_name": "rule_prescreen",
      "event_type": "completed",
      "input_snapshot": null,
      "output_snapshot": {"rule_score": 75, "rule_level": "A"},
      "error_message": null,
      "duration_ms": 120,
      "llm_tokens_used": null,
      "llm_cost_estimate": null,
      "created_at": "2026-06-01T10:00:00"
    }
  ]
}
```

### 36.7 恢复暂停的工作流

`POST /api/workflows/runs/{workflow_id}/resume`

请求体：

```json
{
  "approved": true,
  "review_comment": "审核通过",
  "modified_content": "修改后的话术内容"
}
```

行为：恢复因风险门控而暂停的工作流。`approved=true` 时继续执行，`approved=false` 时标记为拒绝。

响应：`success_response(WorkflowRunOut)`

---

## 三十七、审批队列 Approvals

路由前缀：`/api/approvals`

所有接口需要认证。管理工作流中因合规风险而暂停的待审批内容。

### 37.1 审批列表

`GET /api/approvals`

查询参数：

- `status_filter`（可选）：`pending` / `approved` / `rejected`
- `risk_level`（可选）：`low` / `medium` / `high` / `critical`
- `content_type`（可选）：`follow_up_script` / `draft`
- `page` / `page_size`

响应：`paginated([ApprovalQueueOut])`。

`ApprovalQueueOut` 字段：`id, user_id, workflow_id, workflow_type, content_type, content_id, content_snapshot, risk_level, compliance_result, status, reviewer_id, review_comment, reviewed_at, created_at`。

- `content_type`：内容类型，`follow_up_script`（跟进话术）或 `draft`（草稿）
- `status`：`pending` / `approved` / `rejected`
- `risk_level`：风险等级，由工作流合规检查节点输出

### 37.2 待审计数

`GET /api/approvals/pending-count`

响应：

```json
{
  "success": true,
  "data": {
    "pending_count": 3
  }
}
```

### 37.3 审批详情

`GET /api/approvals/{approval_id}`

响应：`success_response(ApprovalQueueOut)`

### 37.4 审批操作

`POST /api/approvals/{approval_id}/review`

请求体：

```json
{
  "approved": true,
  "review_comment": "话术合规，可以发送",
  "modified_content": "修改后的话术（可选）"
}
```

行为：
- `approved=true`：通过审批。如提供 `modified_content`，使用修改后的内容替换原内容
- `approved=false`：拒绝审批
- 仅 `pending` 状态的记录可审批

响应：`success_response(ApprovalQueueOut)`
