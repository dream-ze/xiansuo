# 智获客

智获客是一个面向 Demo 可成交版的获客线索雷达项目。

当前阶段推进 Demo 可成交版的最小可运行闭环，并加入指定公开帖子链接的真实采集 MVP：

监控源管理 -> 采集任务 -> Mock / Playwright 采集 -> 帖子池 -> 评论池 -> 线索识别 -> 线索池 -> 今日获客报告 -> CSV 导出 -> 同行账号发现池。

## 当前步骤

当前重点：

1. 保留 MockCollector，保证演示和回归测试稳定。
2. 支持 `manual_post + playwright`：用户粘贴公开帖子链接，系统尝试采集帖子和评论。
3. 不做登录、验证码、代理池、批量关键词搜索或反爬绕过。
4. 采集失败写入采集任务 `error_message`，不影响后端服务。

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

如需测试 Playwright 真实采集：

```bash
python -m playwright install chromium
```

## 步骤 23：后端全链路 Smoke Test

新增脚本：`backend/scripts/smoke_test.py`

### 运行前准备

1. 启动后端服务，并确保 `http://127.0.0.1:8000/health` 可访问。
2. 确保数据库迁移已执行，且后端可正常读写。
3. （可选）如需测试 `manual_post + playwright` 成功分支，配置可访问的测试贴文链接。

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

示例：

```bash
SMOKE_BASE_URL=http://127.0.0.1:8000 TEST_MANUAL_POST_URL=https://example.com python backend/scripts/smoke_test.py
```

### 通过标准

- 脚本会逐步打印 `[STEP n]` 和 `[OK]`/`[FAIL]`。
- 所有步骤完成后输出 `PASS`，进程退出码为 `0`。
- 任一步骤失败会输出 `FAIL`、失败步骤号、失败原因和 traceback，进程退出码为非 `0`。

### 失败排查建议

1. 查看脚本控制台中首个 `[FAIL]` 对应的步骤号与错误信息。
2. 查看后端运行日志（uvicorn 控制台）中同一时段的请求与异常栈。
3. 若失败发生在 Playwright 分支，优先检查：
  - `TEST_MANUAL_POST_URL` 是否可访问且为 `http/https`
  - 运行环境是否安装了 `playwright` 及浏览器依赖
  - 目标页面是否可被无头浏览器加载
