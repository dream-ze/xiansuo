# 真实采集接入技术方案

> 本文档只描述方案和实施步骤，不代表所有接口已经实现。当前代码仍以 Mock 闭环为主，真实采集将按本文档分阶段接入。

## 一、目标

将当前智获客 / 线索雷达项目从 Mock 采集演示系统升级为可接入真实采集的数据雷达系统。

目标链路：

监控源管理 -> 采集任务 -> 真实采集器 -> 帖子池 -> 评论池 -> 线索识别 -> 线索池 -> 今日获客报告 -> CSV 导出。

核心要求：

1. 保留 MockCollector，保证演示和测试稳定。
2. 新增真实采集接入层。
3. 优先通过 ExternalApiCollector 接入真实采集服务。
4. 增强 Playwright / Generic Web 作为低成本网页采集方式。
5. 为小红书、抖音、知乎等平台专用采集器预留扩展点。
6. 采集失败不影响主服务。
7. 采集配置、错误、统计信息可追踪。
8. 敏感信息不落库、不进日志。

---

## 二、现有项目基础

当前项目已有：

```text
backend/app/collectors/base.py
backend/app/collectors/factory.py
backend/app/collectors/mock_collector.py
backend/app/collectors/playwright_collector.py
backend/app/services/crawl_pipeline_service.py
backend/app/services/crawl_task_service.py
backend/app/api/routes/monitor_sources.py
```

当前链路：

1. `POST /api/monitor-sources` 创建监控源。
2. `POST /api/monitor-sources/{id}/crawl` 触发采集。
3. `CollectorFactory` 根据 `config.collector_type` 选择采集器。
4. 默认使用 MockCollector。
5. manual_post + collector_type=playwright 时使用 PlaywrightCollector。
6. 采集结果进入 posts/comments。
7. comments 经过 LeadScoringService 生成 leads。

当前限制：

1. 默认是 Mock 采集。
2. PlaywrightCollector 只适合简单 manual_post。
3. 没有 External API 采集器。
4. 没有统一采集配置模型。
5. 没有 collector 能力列表接口。
6. 没有测试采集接口。
7. 真实采集文档不完整。

---

## 三、总体架构

推荐架构：采集器插件化。

```text
MonitorSource
  -> CrawlPipelineService
    -> CollectorFactory
      -> MockCollector
      -> ExternalApiCollector
      -> PlaywrightCollector
      -> GenericWebCollector
      -> XhsCollector
      -> DouyinCollector
      -> ZhihuCollector
    -> Normalize / Validate
    -> Save Posts / Comments
    -> LeadScoringService
    -> Save Leads
    -> Mark CrawlTask Success / Failed
```

核心原则：

1. Collector 只负责采集和格式转换，不直接写数据库。
2. Pipeline 负责入库、评分、任务状态。
3. Factory 只负责选择采集器，不做业务处理。
4. 所有采集器都返回统一 `CollectorResult`。
5. 所有真实采集器都读取 `source.config`。
6. 所有错误必须明确、可追踪、脱敏。

---

## 四、目录规划

建议后续演进为：

```text
backend/app/collectors/
  __init__.py
  base.py
  config.py
  factory.py
  mock_collector.py
  playwright_collector.py
  generic_web_collector.py
  external_api_collector.py
  xhs_collector.py
  douyin_collector.py
  zhihu_collector.py
  utils/
    browser_context.py
    html_extractors.py
    normalize.py
    rate_limit.py
```

说明：

1. `config.py`：解析和校验 monitor_sources.config。
2. `external_api_collector.py`：第一版真实采集 MVP。
3. `generic_web_collector.py`：URL + CSS selector 通用网页采集。
4. `utils/normalize.py`：统一 ID、时间、数字、raw_data 处理。
5. `utils/rate_limit.py`：限速辅助。

---

## 五、配置标准

`monitor_sources.config` 推荐标准：

```json
{
  "collector_type": "mock | playwright | generic_web | external_api | xhs | douyin | zhihu",
  "mode": "mock | real",
  "max_posts": 20,
  "max_comments_per_post": 50,
  "timeout_seconds": 30,
  "retry_times": 2,
  "rate_limit_seconds": 3,
  "entry_url": "",
  "cookie_profile": "",
  "proxy_profile": "",
  "external_api": {
    "provider": "custom",
    "endpoint": "https://collector.example.com/api/search",
    "api_key_env": "COLLECTOR_API_KEY"
  },
  "selectors": {
    "post_title": "h1",
    "post_content": "article",
    "comment_item": ".comment",
    "comment_author": ".author",
    "comment_content": ".content"
  },
  "dedupe": {
    "enabled": true,
    "key_fields": ["platform", "post_id", "comment_id"]
  }
}
```

最小 MVP 必需字段：

1. `collector_type`
2. `mode`
3. `max_posts`
4. `max_comments_per_post`

External API 必需字段：

1. `external_api.endpoint`
2. `external_api.api_key_env` 可选，但生产建议必填

Generic Web 必需字段：

1. `entry_url`
2. `selectors.post_title` 或 `selectors.post_content`

---

## 六、ExternalApiCollector 方案

### 6.1 为什么优先实现 ExternalApiCollector

真实平台直接采集存在稳定性、风控、登录态、验证码、合规等问题。第一版优先做 ExternalApiCollector，可以更快实现“真实采集可接入”：

1. 用户可接入自己的采集服务。
2. 可接入第三方合规采集 API。
3. 后端只消费标准 JSON。
4. 项目内不承担平台风控细节。
5. 易于测试和替换。

### 6.2 请求协议

后端向外部采集服务发送：

```http
POST {endpoint}
Content-Type: application/json
Authorization: Bearer ${API_KEY}
```

请求体：

```json
{
  "platform": "xhs",
  "source_type": "keyword",
  "value": "征信花了",
  "max_posts": 20,
  "max_comments_per_post": 50,
  "config": {
    "collector_type": "external_api",
    "mode": "real"
  }
}
```

### 6.3 响应协议

外部服务返回：

```json
{
  "posts": [
    {
      "platform": "xhs",
      "post_id": "xhs_123",
      "title": "征信花了还能贷款吗",
      "content": "正文内容",
      "post_url": "https://example.com/post/123",
      "author_name": "作者A",
      "author_profile_url": "https://example.com/u/a",
      "like_count": 12,
      "comment_count": 2,
      "collect_count": 3,
      "publish_time": null,
      "is_hot": false,
      "raw_data": {}
    }
  ],
  "comments": [
    {
      "platform": "xhs",
      "post_id": "xhs_123",
      "comment_id": "comment_1",
      "user_name": "用户B",
      "user_profile_url": "https://example.com/u/b",
      "content": "征信花了还能贷吗",
      "like_count": 1,
      "publish_time": null,
      "raw_data": {}
    }
  ],
  "metadata": {
    "provider": "custom",
    "raw_post_count": 1,
    "raw_comment_count": 1
  }
}
```

### 6.4 错误处理

1. 请求超时：crawl_task.status=failed。
2. HTTP 4xx/5xx：crawl_task.status=failed。
3. 返回 JSON 非法：crawl_task.status=failed。
4. posts/comments 结构非法：crawl_task.status=failed。
5. 错误信息必须脱敏，不显示 API Key。

---

## 七、Playwright / Generic Web 方案

### 7.1 PlaywrightCollector 增强

当前 PlaywrightCollector 主要支持 manual_post URL。建议增强：

1. 读取 `timeout_seconds`。
2. 读取 `max_comments_per_post`。
3. 读取 `selectors`。
4. 支持可配置滚动次数。
5. 评论为空时可返回 warning，不一定失败。
6. 生成稳定 post_id/comment_id。

### 7.2 GenericWebCollector

GenericWebCollector 用于普通网页：

1. 根据 entry_url 打开页面。
2. 根据 selectors 抽取标题、正文、评论。
3. 组装 CollectedPost / CollectedComment。
4. 不处理复杂登录、验证码、动态风控。

适用场景：

1. 普通文章页面。
2. 自有内容站。
3. 测试页面。
4. 简单论坛页面。

不适用：

1. 强登录态平台。
2. 强动态渲染平台。
3. 验证码页面。
4. 高频大规模采集。

---

## 八、API 规划

### 8.1 采集器能力列表

`GET /api/collectors`

返回示例：

```json
{
  "success": true,
  "data": [
    {
      "collector_type": "mock",
      "label": "Mock 演示采集",
      "supported_platforms": ["xhs", "douyin", "zhihu", "other"],
      "supported_source_types": ["keyword", "competitor_account", "manual_post", "hot_post_rule"],
      "requires": []
    },
    {
      "collector_type": "external_api",
      "label": "外部 API 采集",
      "supported_platforms": ["xhs", "douyin", "zhihu", "other"],
      "supported_source_types": ["keyword", "competitor_account", "manual_post", "hot_post_rule"],
      "requires": ["external_api.endpoint"]
    }
  ],
  "message": "ok"
}
```

### 8.2 配置校验

`POST /api/collectors/validate-config`

用途：创建监控源前校验 config 是否完整。

### 8.3 测试采集

`POST /api/collectors/test`

用途：测试采集配置是否可用，但不写入 posts/comments/leads。

### 8.4 现有立即采集接口

继续使用：

`POST /api/monitor-sources/{monitor_source_id}/crawl`

---

## 九、前端方案

当前 `MonitorSourcesPage` 已支持：

1. source_type
2. platform
3. name
4. value
5. collector_type
6. max_posts
7. max_comments_per_post
8. enabled

建议升级为动态表单：

### 9.1 Mock 模式

显示：

1. max_posts
2. max_comments_per_post

### 9.2 Playwright 模式

显示：

1. entry_url / value
2. timeout_seconds
3. max_comments_per_post
4. selectors 可选

### 9.3 Generic Web 模式

显示：

1. entry_url
2. post_title selector
3. post_content selector
4. comment_item selector
5. comment_author selector
6. comment_content selector

### 9.4 External API 模式

显示：

1. provider
2. endpoint
3. api_key_env
4. max_posts
5. max_comments_per_post

### 9.5 监控源列表增强

显示：

1. 采集模式。
2. 最近采集状态。
3. 最近采集错误。
4. 最近采集时间。
5. 帖子数 / 评论数 / 线索数。
6. 测试采集按钮。
7. 立即采集按钮。

---

## 十、数据库与去重策略

### 10.1 最小改动策略

第一阶段不强制新增表。优先利用现有字段：

1. `monitor_sources.config` 保存采集配置。
2. `crawl_tasks.error_message` 保存错误。
3. `posts.raw_data` 保存采集原始信息。
4. `comments.raw_data` 保存采集原始信息。

### 10.2 后续增强字段

crawl_tasks 可考虑新增：

1. collector_type
2. mode
3. raw_stats JSON
4. request_config JSON

### 10.3 去重策略

1. posts 按 `platform + post_id` 去重。
2. comments 按 `platform + comment_id` 去重。
3. 无稳定 ID 时，用 sha1 生成：
   - post_id = sha1(platform + post_url + title + content)
   - comment_id = sha1(platform + post_id + user_name + content + publish_time)
4. 重复 comments 不重复生成 leads。

---

## 十一、安全与合规

1. 只接入用户有权访问的数据源。
2. 不提供验证码绕过。
3. 不提供账号盗用、批量注册、风控绕过。
4. 不鼓励高频抓取。
5. 真实采集器必须支持 timeout 和 rate_limit。
6. API Key、Cookie、Token 必须通过环境变量或安全配置读取。
7. 不把敏感信息写入数据库、日志、error_message。
8. raw_data 存储前必须脱敏。
9. 外部 API 错误信息需要截断，避免污染日志。

---

## 十二、实施步骤

### 阶段 0：文档升级

目标：先明确产品目标、技术方案和任务拆分，不改业务代码。

文件：

1. `docs/PRD.md`
2. `docs/TASK_BACKLOG.md`
3. `docs/REAL_COLLECTION_PLAN.md`
4. `docs/API.md`

验收：

1. 文档说明真实采集 MVP 范围。
2. 文档说明 ExternalApiCollector 优先路线。
3. 文档说明分阶段实施步骤。
4. 不影响现有代码运行。

### 阶段 1：Collector 基础设施升级

目标：让系统具备接入多个采集器的基础。

任务：

1. 扩展 CollectorResult metadata。
2. 新增 CollectorConfig。
3. 重构 CollectorFactory。
4. 新增 collector 能力列表。
5. 新增 config 校验。

验收：

1. MockCollector 正常。
2. PlaywrightCollector 正常。
3. 不支持的 collector_type 返回明确错误。
4. `/api/collectors` 返回能力列表。

### 阶段 2：External API 真实采集 MVP

目标：最快实现真实采集可接入。

任务：

1. 新增 ExternalApiCollector。
2. 定义外部 API 标准协议。
3. 支持环境变量 API Key。
4. 支持 timeout / retry。
5. 支持 fake external API 测试。

验收：

1. 可以通过外部 API 拉回真实 posts/comments。
2. 可以生成 leads。
3. 失败时 crawl_task 标记 failed。
4. 不泄漏 API Key。

### 阶段 3：Generic Web / Playwright 增强

目标：支持 URL + CSS selector 的低成本网页采集。

任务：

1. Playwright 支持 selectors。
2. 新增 GenericWebCollector。
3. 支持评论为空策略。
4. 支持稳定 ID 生成。

验收：

1. 测试 HTML 页面可采集帖子和评论。
2. selector 错误有明确错误。
3. 评论为空时按策略处理。

### 阶段 4：前端真实采集配置

目标：让用户能在页面配置真实采集。

任务：

1. collector_type 动态表单。
2. External API 配置表单。
3. Generic Web selector 表单。
4. 测试采集按钮。
5. 最近采集状态展示。

验收：

1. 用户能创建 external_api 监控源。
2. 用户能创建 generic_web 监控源。
3. 用户能触发采集并看到结果。

### 阶段 5：生产化增强

目标：让真实采集可持续运行。

任务：

1. 去重。
2. 增量采集。
3. 定时采集。
4. 失败重试。
5. raw_stats。

验收：

1. 重复采集不重复产生大量线索。
2. 定时采集可运行。
3. 失败任务可重跑。
4. 每次采集有明确统计。

### 阶段 6：平台专用采集器

目标：逐步接入具体平台。

建议优先级：

1. 知乎：内容文本友好。
2. 小红书：业务价值高，但建议优先 External API。
3. 抖音：采集难度高，建议优先 External API。

---

## 十三、验收清单

真实采集 MVP 最终验收：

1. Mock 模式仍可用。
2. external_api 监控源可创建。
3. 外部 API 能返回真实 posts/comments。
4. posts/comments/leads 正常入库。
5. crawl_task 状态准确。
6. 前端可配置真实采集参数。
7. 文档说明接入方式。
8. API Key、Cookie、Token 不泄漏。
9. smoke test 通过。
10. 失败场景有清晰错误信息。
