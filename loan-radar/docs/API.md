# API 文档

## 一、文档作用

记录智获客后端当前已实现的全部 HTTP 接口，包括路径、方法、查询参数、请求体、响应结构和错误约定。本文档以 `backend/app/api/routes/` 实际代码为准，不作前瞻性设计。

后续接口变更必须同步更新本文件。

## 二、约定

### 2.1 基础地址

- 本地开发：`http://localhost:8000`
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
- `platform`：`xhs` / `douyin` / `zhihu` / `other`
- `crawl_task.status`：`pending` / `running` / `success` / `failed`
- `lead.lead_level`：`A` / `B` / `C` / `D`
- `lead.status`：`new` / `contacted` / `invalid` / `converted`
- `comment.demand_type`：由评分服务输出（如 `借款需求`、`资质焦虑`、`产品咨询`、`弱意向` 等）
- `comment.risk_level`：由评分服务输出（如 `low` / `mid` / `high`，以代码为准）

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
  "config": null,
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

- 默认 `config.collector_type` 为空或 `mock` 时使用 MockCollector。
- 当 `source_type == "manual_post"` 且 `config.collector_type == "playwright"` 时，使用 PlaywrightCollector 尝试采集公开帖子链接。
- Playwright 真实采集只支持 `http/https` URL，不支持登录、验证码、代理池或关键词批量搜索。
- 真实采集失败不会导致后端服务崩溃；任务返回 `status="failed"`，并在 `error_message` 中写明原因。

响应：`success_response(CrawlTaskOut)`；监控源不存在返回 404。

### 3.7 删除监控源

`DELETE /api/monitor-sources/{monitor_source_id}`

响应：`success_response({"id": <删除的 id>})`；不存在返回 404。

---

## 四、采集任务 Crawl Tasks

路由前缀：`/api/crawl-tasks`

### 4.1 采集任务列表

`GET /api/crawl-tasks`

查询参数：

- `status`、`source_type`、`platform`、`source_id`（可选过滤）
- `page`（默认 1，ge=1）、`page_size`（默认 20，ge=1, le=100）

响应：`success_response({items: [CrawlTaskOut], total, page, page_size})`。

`CrawlTaskOut` 字段：`id, source_id, source_type, platform, status, started_at, finished_at, error_message, post_count, comment_count, lead_count, discovered_competitor_count, created_at, updated_at`。

### 4.2 采集任务详情

`GET /api/crawl-tasks/{crawl_task_id}`

响应：`success_response(CrawlTaskOut)`；不存在返回 404。

### 4.3 重跑失败任务

`POST /api/crawl-tasks/{crawl_task_id}/rerun`

约束：仅当任务 `status == "failed"` 时可重跑。

响应：`success_response(CrawlTaskOut)`（新创建的重跑任务）。

错误：

- 任务不存在 → 404
- 任务非 failed → 400 `"only failed crawl tasks can be rerun"`
- 关联监控源不存在 → 404 `"monitor source not found"`

---

## 五、帖子 Posts

### 5.1 帖子列表

`GET /api/posts`

查询参数：

- `platform`、`source_type`、`source_id`、`is_hot`(bool)
- `keyword`：在 `title / content / post_id / author_name` 上做 ILIKE 模糊匹配
- `page` / `page_size`：同上

响应：`success_response({items: [PostOut], total, page, page_size})`。

`PostOut` 字段：`id, platform, source_id, source_type, post_id, title, content, post_url, author_name, author_profile_url, like_count, comment_count, collect_count, publish_time, is_hot, raw_data, created_at, updated_at`。

排序：按 `id DESC`。

---

## 六、评论 Comments

### 6.1 评论列表

`GET /api/comments`

查询参数：

- `platform`、`demand_type`、`risk_level`、`is_suspected_demand`(bool)、`post_id`(string，对应 `comments.post_id` 平台原始帖子 id)
- `keyword`：在 `content / user_name / comment_id` 上做 ILIKE 模糊匹配
- `page` / `page_size`：同上

响应：`success_response({items: [CommentOut], total, page, page_size})`。

`CommentOut` 字段：`id, platform, post_id, comment_id, user_name, user_profile_url, content, like_count, publish_time, is_suspected_demand, demand_type, risk_level, raw_data, created_at, updated_at`。

---

## 七、线索 Leads

路由前缀：`/api/leads`

### 7.1 线索列表

`GET /api/leads`

查询参数：

- `lead_level`、`demand_type`、`risk_level`、`platform`、`status`、`source_type`
- `keyword`：在 `content / user_name / reason` 等字段做模糊匹配（详见 `export_service.build_leads_query`）
- `page` / `page_size`：同上

响应：`success_response({items: [LeadOut], total, page, page_size})`，按 `id DESC`。

`LeadOut` 字段：`id, platform, source_id, source_type, source_post_id, source_comment_id, user_name, content, lead_level, lead_score, demand_type, risk_level, evidence, reason, follow_up_script, status, created_at, updated_at`。

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

查询参数：与 7.1 完全一致（除分页外），不分页，全量导出。

响应：

- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename=leads.csv`
- Body：UTF-8 CSV 字节流（不走统一响应包装）

### 7.3 更新线索状态

`PATCH /api/leads/{lead_id}/status`

请求体：

```json
{ "status": "contacted" }
```

`status` 必须属于 `new / contacted / invalid / converted`，否则返回 400。

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

## 十、真实指定链接采集配置

当前已实现的真实采集入口仍复用监控源接口，不新增 `/api/collectors`。

### 10.1 创建 manual_post Playwright 监控源

`POST /api/monitor-sources`

请求体：

```json
{
  "source_type": "manual_post",
  "platform": "xhs",
  "name": "真实帖子链接",
  "value": "https://example.com/post/1",
  "config": {
    "collector_type": "playwright",
    "max_comments_per_post": 50,
    "timeout_ms": 15000,
    "wait_after_load_ms": 1200
  },
  "enabled": true
}
```

校验规则：

1. `collector_type=playwright` 仅支持 `source_type=manual_post`。
2. `value` 必须以 `http://` 或 `https://` 开头。
3. 非 `manual_post` 传入 `collector_type=playwright` 会返回 400。
4. 评论为空允许采集成功，`comment_count=0`。

### 10.2 Playwright raw_data

真实采集成功后，`posts.raw_data` 和 `comments.raw_data` 会包含：

```json
{
  "collector": "playwright",
  "source_url": "https://example.com/post/1",
  "parser": "GenericPostParser",
  "browser_channel": "chromium",
  "extracted_comment_count": 2
}
```

### 10.3 后续真实采集规划

以下能力仍是规划，当前尚未实现：

- `/api/collectors`
- `/api/collectors/validate-config`
- `/api/collectors/test`
- ExternalApiCollector
- GenericWebCollector
- 平台专用 xhs/douyin/zhihu collector
- 定时采集 / 异步采集队列

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

以下接口在规划中提及但 **目前不存在**，需要前端避免调用：

- 真实采集能力接口：`/api/collectors`、`/api/collectors/validate-config`、`/api/collectors/test`
- ExternalApiCollector / GenericWebCollector
- 采集任务的定时调度 / 异步执行接口
- 后台批量 / 定时生成 daily_report
