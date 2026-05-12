# 智获客 / 线索雷达真实采集接入交付文档

## 1. 交付结论

当前项目已经具备 Demo 闭环：

监控源管理 -> 采集任务 -> Mock 采集 -> 帖子池 -> 评论池 -> 线索识别 -> 线索池 -> 今日获客报告 -> CSV 导出。

下一阶段应优化为“真实采集可接入 MVP”。优先路线不是直接硬爬小红书/抖音等强风控平台，而是先做 External API 采集接入层，让系统可以消费第三方采集服务或用户自有采集服务返回的真实 posts/comments，再复用现有入库、评分、日报和导出链路。

本交付文档包含：

1. PRD。
2. 技术拆分。
3. 分阶段实施步骤。
4. 每个阶段可直接交给 Codex / Claude Code / 其他代码智能体执行的提示词。
5. 验收标准。
6. 合规边界。

相关已有文档：

- docs/PRD.md
- docs/REAL_COLLECTION_PLAN.md
- docs/CODEX_REAL_COLLECTION_STEPS.md
- docs/TASK_BACKLOG.md
- docs/API.md

---

## 2. PRD：真实采集接入 MVP

### 2.1 产品目标

把“智获客 / 线索雷达”从 Mock 演示系统升级为可接入真实内容源的获客线索雷达系统。

目标链路：

监控源管理 -> 采集任务 -> 真实采集器 -> 帖子池 -> 评论池 -> 线索识别 -> 线索池 -> 今日获客报告 -> CSV 导出。

### 2.2 核心用户

1. 贷款中介。
2. 助贷机构。
3. 贷款获客团队。
4. 私域运营团队。
5. 销售主管 / 老板。

### 2.3 核心场景

1. 用户配置关键词，例如“征信花了”“负债高”“急用钱”。
2. 用户配置同行账号、指定帖子链接或爆款规则。
3. 系统通过真实采集器获取帖子和评论。
4. 系统识别评论中的贷款需求、资质焦虑、资金周转、产品咨询等线索。
5. 用户在线索池查看高意向用户。
6. 用户查看今日获客报告。
7. 用户导出 CSV 交给销售跟进。

### 2.4 本阶段必须做

1. 保留 MockCollector，保证演示、测试、本地开发稳定。
2. 增加 collector_type 和 mode 配置。
3. 增加 CollectorConfig 配置解析和校验。
4. 增加 CollectorResult.metadata。
5. 增加 ExternalApiCollector，优先通过外部 API 接入真实采集数据。
6. 增强 PlaywrightCollector，支持 timeout、max_comments_per_post、selectors。
7. 增加 GenericWebCollector，支持 URL + CSS selector 的通用网页采集。
8. 增加采集器能力接口 GET /api/collectors。
9. 增加配置校验接口 POST /api/collectors/validate-config。
10. 前端支持创建 mock、playwright、generic_web、external_api 监控源。
11. 采集失败时写入 crawl_task.error_message，不能导致主服务崩溃。
12. 真实采集数据进入 posts/comments 后，继续复用现有 LeadScoringService 生成 leads。
13. 增加去重，避免重复采集重复生成 posts/comments/leads。
14. 文档说明真实采集接入方式和外部 API 协议。

### 2.5 本阶段不做

1. 不做自动私信。
2. 不做账号矩阵运营。
3. 不做验证码绕过。
4. 不做登录破解。
5. 不做风控绕过。
6. 不做批量注册。
7. 不做复杂代理池 / Cookie 池。
8. 不承诺小红书、抖音等强风控平台直连稳定采集。
9. 不做大规模分布式爬虫。

### 2.6 成功标准

1. Mock 模式仍然可用。
2. 可以创建 external_api 类型监控源。
3. 可以通过外部 API 拉回真实 posts/comments。
4. posts/comments 可以正常入库。
5. comments 可以正常生成 leads。
6. crawl_task 可以显示 success/failed 和错误信息。
7. 前端可以配置真实采集参数。
8. 不泄漏 API Key、Cookie、Token。
9. smoke test 仍然通过。
10. 重复采集不会重复产生大量线索。

---

## 3. 建议统一配置结构

monitor_sources.config 建议统一为：

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

---

## 4. 外部 API 标准协议

### 4.1 后端请求外部采集服务

```http
POST {endpoint}
Content-Type: application/json
Authorization: Bearer ***
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

### 4.2 外部采集服务响应

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

---

## 5. 实施阶段总览

| 阶段 | 名称 | 目标 | 是否改业务代码 |
|---|---|---|---|
| P0 | 文档阶段 | PRD、方案、任务清单、API 规划 | 否 |
| P1 | 采集器基础设施 | CollectorResult metadata、CollectorConfig、Factory、采集器能力接口 | 是 |
| P2 | External API 真实采集 MVP | 接入外部采集 API，完成真实数据入库链路 | 是 |
| P3 | Playwright / Generic Web 增强 | 支持 URL + CSS selector 的低成本网页采集 | 是 |
| P4 | 前端真实采集配置 | 动态表单、真实采集配置、状态展示 | 是 |
| P5 | 生产化增强 | 去重、last_crawled_at、错误脱敏、失败重试 | 是 |
| P6 | 平台专用采集器骨架 | xhs/douyin/zhihu collector 扩展点 | 是 |

推荐执行顺序：P1 -> P2 -> P3 -> P4 -> P5 -> P6。

不要先做 P6。平台专用采集器风险最高，不是最快交付真实采集的方式。

---

## 6. P1：采集器基础设施提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P1：采集器基础设施升级。

先阅读：
- docs/PRD.md
- docs/REAL_COLLECTION_PLAN.md
- docs/API.md
- backend/app/collectors/base.py
- backend/app/collectors/factory.py
- backend/app/collectors/mock_collector.py
- backend/app/collectors/playwright_collector.py
- backend/app/main.py

目标：为真实采集接入建立基础设施，但不要实现 ExternalApiCollector 的真实 HTTP 调用。

必须完成：
1. 在 backend/app/collectors/base.py 中让 CollectorResult 支持 metadata: dict[str, Any] | None，默认空 dict 或 None。
2. 新增 backend/app/collectors/config.py，用于解析 source.config，至少支持 collector_type、mode、max_posts、max_comments_per_post、timeout_seconds、retry_times、rate_limit_seconds、entry_url、external_api、selectors。
3. 重构 backend/app/collectors/factory.py：
   - collector_type=mock -> MockCollector
   - collector_type=playwright 且 source_type=manual_post -> PlaywrightCollector
   - collector_type=external_api 暂时抛出 NotImplementedError 或明确 ValueError，提示下一阶段实现
   - collector_type=generic_web 暂时抛出 NotImplementedError 或明确 ValueError，提示下一阶段实现
   - unknown collector_type 必须抛出明确 ValueError，不要静默 fallback 到 Mock
4. 新增 backend/app/api/routes/collectors.py：
   - GET /api/collectors 返回能力列表
   - POST /api/collectors/validate-config 校验配置，不执行采集
5. 在 backend/app/main.py 注册 collectors router。
6. 如果没有测试目录，创建 backend/tests。新增最小测试覆盖配置解析、factory unknown collector_type、能力列表接口。
7. 保持现有 MockCollector、PlaywrightCollector 和 smoke test 行为不回退。

限制：
1. 不要修改前端。
2. 不要实现真实平台爬虫。
3. 不要引入验证码绕过、代理池、Cookie 池。
4. 不要把 API Key 写入日志或错误信息。

完成后运行：
- python -m compileall backend/app
- pytest backend/tests -q（如果测试环境可用）
- git diff --check

最后汇总：修改文件、测试结果、后续 TODO。
```

---

## 7. P2：External API 真实采集 MVP 提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P2：External API 真实采集 MVP。

先阅读：
- docs/REAL_COLLECTION_PLAN.md 的 ExternalApiCollector 章节
- docs/API.md
- backend/app/collectors/base.py
- backend/app/collectors/config.py
- backend/app/collectors/factory.py
- backend/app/services/crawl_pipeline_service.py

目标：实现 ExternalApiCollector，让系统可以通过外部采集 API 获取真实 posts/comments，并复用现有入库和线索评分 pipeline。

必须完成：
1. 新增 backend/app/collectors/external_api_collector.py。
2. ExternalApiCollector.collect(source) 从 source.config.external_api.endpoint 获取 endpoint。
3. 如果 config.external_api.api_key_env 存在，则从环境变量读取 API Key，并用 Authorization: Bearer *** 发送。错误信息中禁止出现真实 key 值。
4. 请求方法使用 POST，Content-Type 为 application/json。
5. 请求体至少包含 platform、source_type、value、max_posts、max_comments_per_post、config。
6. 支持 timeout_seconds 和 retry_times。
7. 解析响应 JSON：posts、comments、metadata。
8. 将响应转换为 CollectedPost、CollectedComment、CollectorResult。
9. 对缺失 post_id/comment_id 的数据生成稳定 sha1 ID。
10. 更新 CollectorFactory：collector_type=external_api 时返回 ExternalApiCollector。
11. 更新 backend/app/collectors/__init__.py 导出 ExternalApiCollector。
12. 新增测试：
    - 成功解析 fake API 响应
    - API Key 从环境变量读取但不会泄漏到错误信息
    - HTTP 500 / 超时 / 非法 JSON 时抛出明确异常
    - 缺失 ID 时生成稳定 ID
13. 确保返回的 posts/comments 可以进入现有 crawl_pipeline_service 并生成 leads。

限制：
1. 不要做任何平台直连爬虫。
2. 不要改前端。
3. 不要引入代理池、Cookie 池、验证码绕过。
4. 不要破坏 MockCollector 和 PlaywrightCollector。

完成后运行：
- python -m compileall backend/app
- pytest backend/tests -q（如果测试环境可用）
- git diff --check

最后汇总：修改文件、测试结果、ExternalApiCollector 使用示例、后续 TODO。
```

---

## 8. P3：Playwright / Generic Web 增强提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P3：Playwright / Generic Web 采集增强。

先阅读：
- docs/REAL_COLLECTION_PLAN.md 的 Playwright / Generic Web 章节
- backend/app/collectors/playwright_collector.py
- backend/app/collectors/base.py
- backend/app/collectors/config.py
- backend/app/collectors/factory.py

目标：让系统支持 URL + CSS selector 的低成本网页采集。

必须完成：
1. 增强 PlaywrightCollector：
   - 从 source.config.timeout_seconds 读取超时时间
   - 从 source.config.max_comments_per_post 限制评论数量
   - 从 source.config.selectors 读取自定义 selector
   - 保留现有默认 selector fallback
2. 新增 backend/app/collectors/generic_web_collector.py：
   - 使用 Playwright 打开 entry_url 或 source.value
   - 根据 selectors.post_title / post_content / comment_item / comment_author / comment_content 提取内容
   - 返回 CollectedPost / CollectedComment
   - 缺失稳定 ID 时生成 sha1 ID
3. 更新 CollectorFactory：collector_type=generic_web 时返回 GenericWebCollector。
4. 更新 backend/app/collectors/__init__.py 导出 GenericWebCollector。
5. 新增测试：
   - 使用本地静态 HTML 或 mock page 测试 selector 提取
   - max_comments_per_post 生效
   - selector 缺失或错误时错误信息明确
6. 评论为空时不要默认导致整个系统崩溃，可返回 metadata.warnings 或按配置决定失败。

限制：
1. 不要实现平台专用爬虫。
2. 不要处理验证码绕过。
3. 不要引入账号池或代理池。
4. 不要破坏 ExternalApiCollector、MockCollector、PlaywrightCollector 现有基本行为。

完成后运行：
- python -m compileall backend/app
- pytest backend/tests -q（如果测试环境可用）
- git diff --check

最后汇总：修改文件、测试结果、generic_web config 示例、后续 TODO。
```

---

## 9. P4：前端真实采集配置提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P4：前端真实采集配置。

先阅读：
- docs/PRD.md 的监控源配置标准
- docs/REAL_COLLECTION_PLAN.md 的前端方案
- docs/API.md
- frontend/src/pages/MonitorSourcesPage.tsx
- frontend/src/api/client.ts

目标：升级监控源创建页面，让用户可以创建 mock、playwright、generic_web、external_api 类型的监控源配置。

必须完成：
1. 在 MonitorSourcesPage 中把 collector_type 选择项扩展为：mock、playwright、generic_web、external_api。
2. 根据 collector_type 动态显示配置字段：
   - mock：max_posts、max_comments_per_post
   - playwright：entry_url/value、timeout_seconds、max_comments_per_post
   - generic_web：entry_url、post_title、post_content、comment_item、comment_author、comment_content selectors
   - external_api：provider、endpoint、api_key_env、max_posts、max_comments_per_post
3. createPayloadFromForm 生成符合文档标准的 config。
4. 保留现有创建、删除、启停、立即采集功能。
5. 如果 /api/collectors/test 尚未实现，测试采集按钮可以先不启用，或显示“接口待实现”，不要导致页面崩溃。
6. 增加必要的 TypeScript 类型定义。
7. 保持页面中文提示清晰。
8. 前端只填写 api_key_env 环境变量名，不填写真实 API Key。

限制：
1. 不要修改后端业务逻辑。
2. 不要硬编码真实 API Key。
3. 不要把 Cookie/API Key 放到前端明文字段中。

完成后运行：
- cd frontend && npm run build
- git diff --check

最后汇总：修改文件、构建结果、前端配置示例、后续 TODO。
```

---

## 10. P5：生产化增强提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P5：真实采集生产化增强。

先阅读：
- docs/REAL_COLLECTION_PLAN.md 的数据库与去重策略
- backend/app/services/crawl_pipeline_service.py
- backend/app/services/crawl_task_service.py
- backend/app/models/post.py
- backend/app/models/comment.py
- backend/app/models/lead.py
- backend/app/models/monitor_source.py

目标：增加去重和采集统计能力，让重复采集不会重复产生大量 posts/comments/leads。

必须完成：
1. 在 crawl_pipeline_service 中实现 posts 去重：优先按 platform + post_id 判断已有数据。
2. 实现 comments 去重：优先按 platform + comment_id 判断已有数据。
3. 对已存在的 comment 不重复生成 lead。
4. 采集成功后更新 monitor_source.last_crawled_at。
5. crawl_task 的 post_count/comment_count/lead_count 应统计本次新增数量。
6. 如当前模型没有 raw_stats 字段，不要强行大迁移，可以先在 metadata 或 TODO 中记录后续增强方案。
7. 错误信息脱敏，禁止出现 API Key、Cookie、Token。
8. 新增测试覆盖重复采集不会重复入库和重复生成 lead。

限制：
1. 如果需要数据库迁移，先给出最小迁移方案，不要引入大规模 schema 重构。
2. 不要修改前端。
3. 不要实现定时调度，定时调度可以保留 TODO。

完成后运行：
- python -m compileall backend/app
- pytest backend/tests -q（如果测试环境可用）
- git diff --check

最后汇总：修改文件、测试结果、去重策略说明、后续 TODO。
```

---

## 11. P6：平台专用采集器骨架提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P6：平台专用采集器骨架。

先阅读：
- docs/REAL_COLLECTION_PLAN.md 的平台专用采集器章节
- backend/app/collectors/factory.py
- backend/app/collectors/base.py
- backend/app/collectors/external_api_collector.py（如果已实现）

目标：为 xhs、douyin、zhihu 增加 collector 骨架和明确错误提示，但不要实现任何风控绕过或复杂直连爬虫。

必须完成：
1. 新增 backend/app/collectors/xhs_collector.py。
2. 新增 backend/app/collectors/douyin_collector.py。
3. 新增 backend/app/collectors/zhihu_collector.py。
4. 每个 collector 都实现 collect(source)，当前可返回明确 NotImplementedError 或 ValueError，说明：平台专用直连暂未实现，建议使用 collector_type=external_api 接入合规采集服务。
5. 更新 CollectorFactory 支持 collector_type=xhs/douyin/zhihu。
6. 更新 backend/app/collectors/__init__.py 导出这些 collector。
7. 更新 docs/REAL_COLLECTION_PLAN.md，明确平台专用 collector 目前只是扩展点。
8. 新增测试：选择 xhs/douyin/zhihu collector_type 时错误信息明确且不误用 Mock。

限制：
1. 不要写验证码绕过。
2. 不要写账号池、代理池。
3. 不要模拟登录或破解接口。
4. 不要承诺平台直连稳定性。

完成后运行：
- python -m compileall backend/app
- pytest backend/tests -q（如果测试环境可用）
- git diff --check

最后汇总：修改文件、测试结果、平台 collector 当前能力边界、后续 TODO。
```

---

## 12. 每阶段完成后的验收提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请对刚完成的真实采集接入阶段做代码审查和验收。不要主动大改代码，除非发现明确的小问题可以直接修复。

请检查：
1. 是否符合 docs/PRD.md、docs/REAL_COLLECTION_PLAN.md、docs/TASK_BACKLOG.md。
2. 是否破坏现有 MockCollector 和 smoke test 链路。
3. 是否有 API Key、Cookie、Token 泄漏风险。
4. 是否引入验证码绕过、账号池、代理池、风控绕过等不允许能力。
5. 是否有未处理异常或静默 fallback 到 Mock 的问题。
6. 是否有测试覆盖关键行为。
7. 是否需要更新 docs/API.md 或 docs/REAL_COLLECTION_PLAN.md。

请运行：
- git diff --check
- python -m compileall backend/app
- 如果有测试，运行 pytest backend/tests -q
- 如果改了前端，进入 frontend 运行 npm run build

最后输出：
- 通过项
- 风险项
- 必须修复项
- 建议后续项
```

---

## 13. 项目当前状态判断

基于当前代码检查：

1. backend/app/collectors/factory.py 当前仅 mock 和 manual_post + playwright，其他类型会 fallback 到 Mock。
2. backend/app/collectors/base.py 的 CollectorResult 当前还没有 metadata。
3. backend/app/collectors/external_api_collector.py 当前不存在。
4. backend/app/collectors/generic_web_collector.py 当前不存在。
5. backend/app/api/routes/collectors.py 当前不存在。
6. frontend/src/pages/MonitorSourcesPage.tsx 当前仅有 mock、playwright 两种 collector_type。
7. crawl_pipeline_service 当前直接新增 posts/comments/leads，尚未看到去重逻辑。

因此建议从 P1 开始执行，P1 和 P2 完成后就能具备“真实采集可接入”的最小交付能力。

---

## 14. 最小可交付版本范围

如果只追求最快可交付，建议只做 P1 + P2 + P4 的 External API 部分：

1. P1：采集器基础设施。
2. P2：ExternalApiCollector。
3. P4：前端增加 external_api 配置。
4. 补充 smoke test 和文档。

该版本可以做到：

1. 用户在前端创建 external_api 监控源。
2. 后端调用外部采集服务。
3. 外部服务返回真实 posts/comments。
4. 系统入库并生成 leads。
5. 用户查看线索池和日报。

P3、P5、P6 可作为增强版本继续迭代。
