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

## 十五、其他说明

- `mock` / `playwright` / `external_api` / `generic_web` 采集器（代码文件存在但 CollectorFactory 不路由）
- 所有采集任务通过 `CrawlTaskQueue` 队列管理，同一时间仅执行一个采集任务
- 定时采集调度器使用 APScheduler，每分钟检查一次需要触发的监控源
