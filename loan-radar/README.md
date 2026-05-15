# 智获客

智获客是一个面向 Demo 可成交版的获客线索雷达项目。

当前阶段推进 Demo 可成交版的最小可运行闭环，基于 MediaCrawler 实现多平台真实采集：

监控源管理 -> 采集任务 -> MediaCrawler 采集 -> 帖子池 -> 评论池 -> 线索识别 -> 线索池 -> 今日获客报告 -> CSV 导出 -> 同行账号发现池。

## 当前步骤

当前重点：

1. 基于 MediaCrawler 开源项目实现多平台真实采集（当前支持小红书、抖音、知乎）。
2. `collector_type` 当前仅支持 `media_crawler`，旧采集器（Mock/Playwright/ExternalApi/GenericWeb）代码存在但 Factory 不路由。
3. 前端监控源页面可配置 `collector_type`（当前应选择 `media_crawler`）。
4. 真实平台采集仍需小规模、合规、人工测试。
5. 不做登录绕过、验证码绕过、账号池、代理池、签名逆向。
6. 采集失败写入采集任务 `error_message`，不影响后端服务。

## 目录结构

```text
loan-radar/
  backend/
  frontend/
  docs/
  README.md
  CODEX_TASK_RULES.md
  docker-compose.yml
  .gitignore
```

## 文档索引

- `docs/PRD.md`：产品目标、范围和阶段边界。
- `docs/DB_DESIGN.md`：数据库设计说明入口。
- `docs/API.md`：接口设计说明入口。
- `docs/TASK_BACKLOG.md`：任务拆分和优先级清单。
- `docs/DEMO_FLOW.md`：Demo 演示流程。
- `docs/PROGRESS_AUDIT.md`：项目进度审计报告。
- `CODEX_TASK_RULES.md`：Codex 开发规则和限制。

## 本地启动

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

如需使用 MediaCrawler 真实采集，需先启动 MediaCrawler API 服务：

```bash
cd D:\Project\MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

可通过后端健康检查确认 MediaCrawler 服务状态：

```bash
curl http://localhost:8001/api/monitor-sources/media-crawler/health
```

## 后端全链路 Smoke Test

脚本：`backend/scripts/smoke_test.py`

> ⚠️ 当前 smoke_test 依赖 mock/playwright 采集器，但 Factory 仅支持 media_crawler，因此**当前无法通过**。需恢复 mock 到 Factory 路由或重写 smoke_test 后才能运行。

### 运行前准备

1. 启动后端服务，并确保 `http://127.0.0.1:8000/health` 可访问。
2. 确保数据库迁移已执行，且后端可正常读写。

### 运行命令

在项目根目录执行：

```bash
python backend/scripts/smoke_test.py
```

可选环境变量：

- `SMOKE_BASE_URL`：后端地址，默认 `http://127.0.0.1:8000`
- `TEST_MANUAL_POST_URL`：`manual_post` 测试链接，默认 `https://example.com/test-manual-post`
- `SMOKE_TIMEOUT_SECONDS`：单次 HTTP 请求超时秒数，默认 `30`
- `MIN_LEAD_LEVEL_CLASSES`：关键词线索至少覆盖的等级类别数（A/B/C/D），默认 `2`

### 通过标准

- 脚本会逐步打印 `[STEP n]` 和 `[OK]`/`[FAIL]`。
- 所有步骤完成后输出 `PASS`，进程退出码为 `0`。
- 任一步骤失败会输出 `FAIL`、失败步骤号、失败原因和 traceback，进程退出码为非 `0`。
