# 真实采集接入开发阶段与 Codex 提示词

> 本文档用于指导后续使用 Codex CLI 分阶段开发真实采集能力。
>
> 相关文档：
>
> - `docs/PRD.md`
> - `docs/REAL_COLLECTION_PLAN.md`
> - `docs/TASK_BACKLOG.md`
> - `docs/API.md`
>
> 重要原则：每个阶段独立提交；先写测试，再改代码；不要一次性让 Codex 做完整项目改造。

---

## 一、Codex 使用总规则

### 1.1 工作目录

在 Windows 中项目路径是：

```text
D:\Project\线索雷达\loan-radar
```

在 WSL / Codex 执行时使用：

```bash
cd /mnt/d/Project/线索雷达/loan-radar
```

如果路径中文导致某些工具异常，可创建临时软链接：

```bash
ln -sfn '/mnt/d/Project/线索雷达/loan-radar' /tmp/loan-radar
cd /tmp/loan-radar
```

### 1.2 Codex 推荐执行方式

```bash
codex exec --full-auto '<这里放阶段提示词>'
```

如果任务较大，建议每个阶段单独运行一次 Codex，不要把 P1-P6 一次性全部交给 Codex。

### 1.3 每阶段必须遵守

1. 先阅读相关文档。
2. 先检查现有代码，不要凭空重写。
3. 保持现有 MockCollector 行为不回退。
4. 保持现有 smoke test 能运行。
5. 不引入验证码绕过、风控绕过、账号池、代理池能力。
6. 不把 API Key、Cookie、Token 写入数据库、日志或 error_message。
7. 新增行为必须有测试或最小验证脚本。
8. 每阶段完成后输出：
   - 修改了哪些文件
   - 如何运行测试
   - 是否有后续 TODO

### 1.4 建议每阶段结束后执行

```bash
git diff --check
python -m compileall backend/app
```

如果后续补齐 pytest，再执行：

```bash
pytest backend/tests -q
```

---

## 二、开发阶段总览

| 阶段 | 名称 | 目标 | 是否改业务代码 |
|---|---|---|---|
| P0 | 文档阶段 | PRD、方案、任务清单、API 规划 | 否 |
| P1 | 采集器基础设施 | CollectorResult metadata、CollectorConfig、Factory、采集器能力接口 | 是 |
| P2 | External API 真实采集 MVP | 接入外部采集 API，完成真实数据入库链路 | 是 |
| P3 | Playwright / Generic Web 增强 | 支持 URL + selector 的低成本网页采集 | 是 |
| P4 | 前端真实采集配置 | 前端动态表单、测试采集按钮、状态展示 | 是 |
| P5 | 生产化增强 | 去重、last_crawled_at、raw_stats、重试、定时采集 | 是 |
| P6 | 平台专用采集器骨架 | xhs/douyin/zhihu collector 骨架和文档 | 是 |

---

## 三、P0：文档阶段

### 3.1 当前状态

P0 已完成，包含：

1. `docs/PRD.md`
2. `docs/REAL_COLLECTION_PLAN.md`
3. `docs/TASK_BACKLOG.md`
4. `docs/API.md`

### 3.2 P0 Codex 提示词

如果后续需要 Codex 重新检查和整理文档，可使用：

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请只修改 docs 下的文档，不要修改 backend 或 frontend 业务代码。

目标：检查并完善真实采集接入相关文档。

请阅读：
- docs/PRD.md
- docs/REAL_COLLECTION_PLAN.md
- docs/TASK_BACKLOG.md
- docs/API.md

要求：
1. 确保 PRD 描述从 Mock 闭环升级为真实采集接入 MVP。
2. 确保 REAL_COLLECTION_PLAN.md 包含采集器架构、ExternalApiCollector、GenericWebCollector、Playwright 增强、前端配置、数据库与去重、安全合规、阶段步骤。
3. 确保 TASK_BACKLOG.md 按 P0-P6 阶段拆分。
4. 确保 API.md 明确 /api/collectors、/api/collectors/validate-config、/api/collectors/test 是规划接口，尚未实现。
5. 不要新增业务代码。
6. 最后运行 git diff --check，并汇总修改内容。
```

---

## 四、P1：采集器基础设施

### 4.1 目标

建立真实采集接入的基础设施，但不实现 External API 的完整调用。

### 4.2 主要任务

1. 扩展 `CollectorResult`，增加 `metadata` 字段。
2. 新增 `CollectorConfig` 配置解析和校验工具。
3. 重构 `CollectorFactory`，支持明确的 collector_type 分发。
4. 不支持的 collector_type 返回明确错误，不再静默 fallback 到 Mock。
5. 新增采集器能力列表接口：`GET /api/collectors`。
6. 新增采集配置校验接口：`POST /api/collectors/validate-config`。
7. 注册 collectors router。
8. 确保现有 MockCollector / PlaywrightCollector 不回退。

### 4.3 建议修改文件

```text
backend/app/collectors/base.py
backend/app/collectors/config.py
backend/app/collectors/factory.py
backend/app/collectors/__init__.py
backend/app/api/routes/collectors.py
backend/app/main.py
backend/tests/test_collectors_config.py
backend/tests/test_collectors_routes.py
```

如果项目暂时没有 tests 目录，创建：

```text
backend/tests/
```

### 4.4 验收标准

1. `CollectorResult` 支持 metadata，现有代码不报错。
2. `CollectorFactory` 支持 mock、playwright。
3. unknown collector_type 会抛出明确 `ValueError`。
4. `GET /api/collectors` 返回采集器能力列表。
5. `POST /api/collectors/validate-config` 能校验 mock、playwright、external_api、generic_web 的基础配置。
6. `python -m compileall backend/app` 通过。
7. 新增测试通过。

### 4.5 P1 Codex 提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P1：采集器基础设施升级。

先阅读：
- docs/PRD.md
- docs/REAL_COLLECTION_PLAN.md
- docs/TASK_BACKLOG.md
- docs/API.md
- backend/app/collectors/base.py
- backend/app/collectors/factory.py
- backend/app/collectors/mock_collector.py
- backend/app/collectors/playwright_collector.py
- backend/app/main.py

目标：为真实采集接入建立基础设施，但不要实现 ExternalApiCollector 的真实 HTTP 调用。

必须完成：
1. 在 backend/app/collectors/base.py 中让 CollectorResult 支持 metadata: dict[str, Any] | None，默认 None 或空 dict，保持现有 MockCollector/PlaywrightCollector 不需要大改也能运行。
2. 新增 backend/app/collectors/config.py，提供 CollectorConfig 或等价函数，用于解析 source.config，至少支持字段：collector_type、mode、max_posts、max_comments_per_post、timeout_seconds、retry_times、rate_limit_seconds、entry_url、external_api、selectors。
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
7. 保持现有接口行为不回退。

限制：
1. 不要修改前端。
2. 不要实现真实平台爬虫。
3. 不要引入验证码绕过、代理池、Cookie 池。
4. 不要把 API Key 写入日志或错误信息。

完成后运行：
- python -m compileall backend/app
- 如能运行 pytest，则运行 pytest backend/tests -q
- git diff --check

最后汇总：修改文件、测试结果、后续 TODO。
```

---

## 五、P2：External API 真实采集 MVP

### 5.1 目标

通过 ExternalApiCollector 接入外部采集服务，最快实现真实数据进入系统。

### 5.2 主要任务

1. 新增 `ExternalApiCollector`。
2. 从 `source.config.external_api.endpoint` 读取外部 API 地址。
3. 从 `api_key_env` 指定的环境变量读取 API Key。
4. POST 请求外部 API。
5. 解析外部 API 返回的 posts/comments。
6. 转换为 `CollectedPost` / `CollectedComment`。
7. 支持 timeout、retry、错误脱敏。
8. 新增测试用 fake external API。

### 5.3 建议修改文件

```text
backend/app/collectors/external_api_collector.py
backend/app/collectors/factory.py
backend/app/collectors/__init__.py
backend/app/collectors/config.py
backend/tests/test_external_api_collector.py
backend/tests/test_crawl_pipeline_external_api.py
```

### 5.4 外部 API 请求协议

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

### 5.5 外部 API 响应协议

```json
{
  "posts": [],
  "comments": [],
  "metadata": {}
}
```

### 5.6 验收标准

1. external_api 监控源可被 CollectorFactory 正确路由。
2. ExternalApiCollector 能请求 fake API 并返回 CollectorResult。
3. 返回 posts/comments 可进入现有 pipeline。
4. 外部 API 超时/失败时 crawl_task failed。
5. 错误信息不泄漏 API Key。
6. compileall 和测试通过。

### 5.7 P2 Codex 提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P2：External API 真实采集 MVP。

先阅读：
- docs/REAL_COLLECTION_PLAN.md 的 ExternalApiCollector 章节
- docs/API.md 的真实采集接口规划
- backend/app/collectors/base.py
- backend/app/collectors/config.py
- backend/app/collectors/factory.py
- backend/app/services/crawl_pipeline_service.py

目标：实现 ExternalApiCollector，让系统可以通过外部采集 API 获取真实 posts/comments，并复用现有入库和线索评分 pipeline。

必须完成：
1. 新增 backend/app/collectors/external_api_collector.py。
2. ExternalApiCollector.collect(source) 从 source.config.external_api.endpoint 获取 endpoint。
3. 如果 config.external_api.api_key_env 存在，则从环境变量读取 API Key，并用 Authorization: Bearer <key> 发送。错误信息中禁止出现 key 值。
4. 请求方法使用 POST，Content-Type 为 application/json。
5. 请求体至少包含 platform、source_type、value、max_posts、max_comments_per_post、config。
6. 支持 timeout_seconds 和 retry_times。
7. 解析响应 JSON：posts、comments、metadata。
8. 将响应转换为 CollectedPost、CollectedComment、CollectorResult。
9. 对缺失 post_id/comment_id 的数据生成稳定 sha1 ID。
10. 更新 CollectorFactory：collector_type=external_api 时返回 ExternalApiCollector。
11. 更新 __init__.py 导出 ExternalApiCollector。
12. 新增测试：
    - 成功解析 fake API 响应
    - API Key 从环境变量读取但不会泄漏到错误信息
    - HTTP 500 / 超时 / 非法 JSON 时抛出明确异常
    - 缺失 ID 时生成稳定 ID

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

## 六、P3：Playwright / Generic Web 增强

### 6.1 目标

支持 URL + CSS selector 的通用网页采集，让非强风控网页可以低成本接入。

### 6.2 主要任务

1. PlaywrightCollector 支持 selectors。
2. PlaywrightCollector 支持 max_comments_per_post。
3. PlaywrightCollector 支持 timeout_seconds。
4. 新增 GenericWebCollector。
5. 支持 entry_url。
6. 支持评论为空策略。
7. selector 错误返回明确错误。

### 6.3 建议修改文件

```text
backend/app/collectors/playwright_collector.py
backend/app/collectors/generic_web_collector.py
backend/app/collectors/factory.py
backend/app/collectors/__init__.py
backend/tests/test_generic_web_collector.py
backend/tests/test_playwright_collector_config.py
```

### 6.4 验收标准

1. generic_web 可读取 entry_url + selectors。
2. 测试 HTML 页面可采集帖子和评论。
3. max_comments_per_post 生效。
4. timeout_seconds 生效。
5. selector 错误有明确错误。
6. 评论为空按配置处理，不默认导致整个系统崩溃。

### 6.5 P3 Codex 提示词

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
4. 更新 __init__.py 导出 GenericWebCollector。
5. 新增测试：
   - 使用本地静态 HTML 或 mock page 测试 selector 提取
   - max_comments_per_post 生效
   - selector 缺失或错误时错误信息明确

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

## 七、P4：前端真实采集配置

### 7.1 目标

让用户可以在前端配置真实采集参数。

### 7.2 主要任务

1. MonitorSourcesPage 支持动态 collector_type 表单。
2. Mock 模式显示基础数量字段。
3. External API 模式显示 provider、endpoint、api_key_env。
4. Generic Web 模式显示 CSS selector。
5. Playwright 模式显示 URL、timeout、评论上限。
6. 增加测试采集按钮。
7. 展示最近采集结果。

### 7.3 建议修改文件

```text
frontend/src/pages/MonitorSourcesPage.tsx
frontend/src/api/client.ts
frontend/src/App.tsx 或相关路由文件（如需要）
frontend/src/styles 或相关 CSS（如需要）
```

### 7.4 验收标准

1. 能创建 mock 监控源。
2. 能创建 external_api 监控源。
3. 能创建 generic_web 监控源。
4. config 结构符合 docs/PRD.md 和 docs/REAL_COLLECTION_PLAN.md。
5. 前端不会在接口未实现时错误调用规划接口，或者调用前有降级处理。
6. 构建通过。

### 7.5 P4 Codex 提示词

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请执行 P4：前端真实采集配置。

先阅读：
- docs/PRD.md 的监控源配置标准
- docs/REAL_COLLECTION_PLAN.md 的前端方案
- docs/API.md 的真实采集接口规划
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
6. 增加必要的类型定义。
7. 保持页面中文提示清晰。

限制：
1. 不要修改后端业务逻辑。
2. 不要硬编码真实 API Key。
3. 不要把 Cookie/API Key 放到前端明文字段中，api_key_env 只填写环境变量名。

完成后运行：
- npm run build（在 frontend 目录）
- git diff --check

最后汇总：修改文件、构建结果、前端配置示例、后续 TODO。
```

---

## 八、P5：生产化增强

### 8.1 目标

让真实采集从“能接入”变成“可持续运行”。

### 8.2 主要任务

1. posts 去重。
2. comments 去重。
3. 避免重复生成 leads。
4. 更新 monitor_sources.last_crawled_at。
5. 记录 raw_stats。
6. 支持失败重试策略。
7. 后续支持定时采集。

### 8.3 建议修改文件

```text
backend/app/services/crawl_pipeline_service.py
backend/app/services/crawl_task_service.py
backend/app/models/crawl_task.py
backend/app/schemas/crawl_task.py
backend/app/models/post.py
backend/app/models/comment.py
backend/tests/test_crawl_pipeline_dedupe.py
```

如果需要数据库字段变更，再补迁移方案。

### 8.4 验收标准

1. 重复采集同一 post/comment 不重复入库。
2. 重复 comment 不重复生成 lead。
3. last_crawled_at 正确更新。
4. crawl_task 统计准确。
5. 失败信息明确且脱敏。

### 8.5 P5 Codex 提示词

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
5. crawl_task 的 post_count/comment_count/lead_count 应统计本次新增数量，同时可在 raw_data 或后续字段中保留采集返回总数（如果当前模型没有 raw_stats 字段，不要强行大迁移，可先记录在日志或 TODO）。
6. 错误信息脱敏，禁止出现 API Key、Cookie、Token。
7. 新增测试覆盖重复采集不会重复入库和重复生成 lead。

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

## 九、P6：平台专用采集器骨架

### 9.1 目标

为小红书、抖音、知乎等平台提供标准扩展点，但不实现复杂风控绕过能力。

### 9.2 主要任务

1. 新增 XhsCollector 骨架。
2. 新增 DouyinCollector 骨架。
3. 新增 ZhihuCollector 骨架。
4. Factory 支持平台专用 collector_type。
5. 文档说明优先推荐 External API。
6. 平台直连能力只做可控、合规、低频场景。

### 9.3 建议修改文件

```text
backend/app/collectors/xhs_collector.py
backend/app/collectors/douyin_collector.py
backend/app/collectors/zhihu_collector.py
backend/app/collectors/factory.py
backend/app/collectors/__init__.py
docs/REAL_COLLECTION_PLAN.md
backend/tests/test_platform_collectors.py
```

### 9.4 验收标准

1. xhs/douyin/zhihu collector_type 有明确路由。
2. 未配置 external_api 或未实现直连时，返回明确错误。
3. 错误提示建议使用 External API。
4. 不包含验证码绕过、登录破解、代理池、账号池实现。

### 9.5 P6 Codex 提示词

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
6. 更新 __init__.py 导出这些 collector。
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

## 十、推荐执行顺序

建议严格按以下顺序执行：

1. P1：采集器基础设施。
2. P2：External API 真实采集 MVP。
3. P3：Generic Web / Playwright 增强。
4. P4：前端真实采集配置。
5. P5：去重和生产化增强。
6. P6：平台专用采集器骨架。

不要先做 P6。平台专用采集器风险最高，且不是最快落地真实采集的方式。

---

## 十一、每阶段完成后的通用验收 Prompt

每个阶段开发完成后，可以单独让 Codex 做一次检查：

```text
你在 D:\Project\线索雷达\loan-radar 项目中工作。请对刚完成的真实采集接入阶段做代码审查和验收，不要主动改代码，除非发现明确的小问题可以直接修复。

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

## 十二、阶段提交建议

每个阶段建议单独提交：

```bash
git add <本阶段文件>
git commit -m "feat: add collector infrastructure"
```

提交信息建议：

```text
docs: add real collection codex development steps
feat: add collector infrastructure
feat: add external api collector
feat: add generic web collector
feat: add real collection frontend config
feat: add crawl dedupe for real collection
feat: add platform collector skeletons
```
