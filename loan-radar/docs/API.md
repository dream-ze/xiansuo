# API 文档

## 一、文档作用

记录智获客后端当前已实现的全部 HTTP 接口，包括路径、方法、查询参数、请求体、响应结构和错误约定。本文档以 `backend/app/api/routes/` 实际代码为准，不作前瞻性设计。

后续接口变更必须同步更新本文件。

## 二、约定

### 2.1 基础地址

- 本地开发：`http://localhost:8001`
- 健康检查：`GET /health` → `{"status": "ok"}`

### 2.2 统一响应包装

除 CSV 导出外，所有接口统一使用 `app/utils/response.py` 中的包装结构。

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

列表类接口（采集任务、帖子、评论、线索）的 `data` 字段固定为：

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
| 400 | 参数/状态校验失败 | `ValueError`、非法 `status`、不可重跑等 |
| 404 | 资源不存在 | id 查不到对应记录 |
| 422 | FastAPI 自动校验 | Query/Body 类型或 ge/le 越界 |

### 2.5 通用枚举

- `source_type`：`keyword` / `competitor_account` / `manual_post` / `hot_post_rule`
- `platform`：`xhs` / `douyin` / `zhihu`

  > 当前 MVP 仅支持以上 3 个平台。传入其他平台（如 kuaishou / bilibili / weibo / tieba / other）将返回 400 错误。后续版本将逐步开放更多平台。
- `crawl_task.status`：`pending` / `running` / `success` / `failed`
- `lead.lead_level`：`A` / `B` / `C` / `D`
- `lead.status`：`new` / `contacted` / `interested` / `invalid` / `converted`
- `lead.is_duplicate`：`true` / `false`——标记线索是否为疑似重复
- `lead.duplicate_reason`：重复原因枚举值——`"同用户相似评论(相似度XX%)"` 或 `"相同内容重复"`
- `comment.demand_type`：由评分服务输出（如 `借款需求`、`资质焦虑`、`产品咨询`、`弱意向` 等）
- `comment.risk_level`：由评分服务输出（如 `low` / `mid` / `high`，以代码为准）
- `collector_type`：`media_crawler`（真实采集）/ `mock`（演示采集，需设置 `ENABLE_MOCK_COLLECTOR=true`）
- `crawl_task.failure_type`：`media_crawler_unreachable` / `platform_not_supported` / `auth_required` / `captcha_or_risk_control` / `timeout` / `empty_result` / `parser_error` / `unknown`

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
    "max_posts": 20
  },
  "enabled": true,
  "last_crawled_at": null
}
```

响应：`success_response(MonitorSourceOut)`

`MonitorSourceOut` 字段：`id, source_type, platform, name, value, config, enabled, last_crawled_at, created_at, updated_at`。

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
    "platform_not_supported": {
      "value": "platform_not_supported",
      "label": "平台不支持",
      "description": "当前采集器不支持该平台",
      "suggestion": "请选择支持的平台（小红书、抖音、知乎），或等待后续版本开放更多平台"
    },
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

行为：使用 MediaCrawlerCollector 执行采集，自动创建关联监控源。

响应：`success_response(CrawlTaskOut)`；任务不存在返回 404；已在运行返回 400。

---

## 五、帖子 Posts

### 5.1 帖子列表

`GET /api/posts`

查询参数：

- `platform`、`source_type`、`source_id`、`is_hot`(bool)
- `keyword`：在 `title / content / post_id / author_name` 上做 ILIKE 模糊匹配
- `page` / `page_size`：同上

响应：`success_response({items: [PostOut], total, page, page_size})`。

`PostOut` 字段：`id, platform, source_id, source_type, post_id, title, content, post_url, author_name, author_profile_url, like_count, comment_count, collect_count, publish_time, is_hot, lead_count, raw_data, created_at, updated_at`。

- `lead_count`：该帖子关联的线索数量（由 `_enrich_post_out` 计算填充）。

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

`CommentOut` 字段：`id, platform, post_id, comment_id, user_name, user_profile_url, content, like_count, publish_time, is_suspected_demand, demand_type, risk_level, has_lead, raw_data, created_at, updated_at`。

- `has_lead`：该评论是否已生成线索（由 `_enrich_comment_out` 计算填充）。

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
- `keyword`：在 `content / user_name / reason` 等字段做模糊匹配（详见 `export_service.build_leads_query`）
- `page` / `page_size`：同上

响应：`success_response({items: [LeadOut], total, page, page_size})`，按 `id DESC`。

`LeadOut` 字段：`id, platform, source_id, source_type, source_post_id, source_comment_id, source_post_title, source_post_url, user_name, user_profile_url, content, content_hash, lead_level, lead_score, demand_type, risk_level, evidence, reason, follow_up_script, status, is_duplicate, duplicate_group_id, duplicate_reason, notes, created_at, updated_at`。

- `source_post_title`：来源帖子标题（冗余字段，由 `_enrich_lead_out` 填充）
- `source_post_url`：来源帖子 URL（冗余字段，由 `_enrich_lead_out` 填充）
- `user_profile_url`：评论者主页 URL，用于同用户相似评论去重
- `content_hash`：评论内容 MD5 哈希，用于相同内容去重
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

查询参数：与 7.1 完全一致（含 `source_post_id`、`source_comment_id`、`is_duplicate`，除分页外），不分页，全量导出。

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
{ "status": "contacted" }
```

`status` 必须属于 `new / contacted / interested / invalid / converted`，否则返回 400。

响应：`success_response(LeadOut)`；线索不存在返回 404。

> 注意：路径形式是 `/{lead_id}/status`，而非 `/{lead_id}`。`/export` 路由必须在动态路径之前注册，已在代码中处理。

---

## 八、今日获客报告 Daily Reports

路由前缀：`/api/daily-reports`

### 8.1 生成今日报告

`POST /api/daily-reports/generate`

查询参数：

- `platform`（可选）：传入时仅统计该平台；不传则统计全平台（在 daily_reports 中用约定值或 `all` 区分，以服务实现为准）

响应：`success_response(DailyReportOut)`。

`DailyReportOut` 字段：`id, report_date, platform, source_count, post_count, comment_count, lead_count, a_lead_count, b_lead_count, c_lead_count, d_lead_count, top_demands, top_keywords, hot_posts, content_suggestions, follow_up_suggestions, risk_warnings, created_at, updated_at`。

### 8.2 获取今日报告

`GET /api/daily-reports/today`

查询参数：`platform`（可选）。

响应：

- 已生成 → `success_response(DailyReportOut)`
- 未生成 → 404 `"today's report not found, please generate first"`

### 8.3 历史报告列表

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

## 十二、尚未实现（不在当前 API 中）

以下能力暂未实现或不稳定，需要前端避免依赖：

- `/api/collectors/test`
- 采集任务的定时调度 / 异步执行接口
- 后台批量 / 定时生成 daily_report
- `mock` / `playwright` / `external_api` / `generic_web` 采集器（代码文件存在但 CollectorFactory 不路由）
