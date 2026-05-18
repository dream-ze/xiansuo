# 智获客 · 助贷线索雷达 MVP

面向助贷行业的获客线索雷达，基于 MediaCrawler 实现多平台真实采集，帮助助贷从业者从社交媒体发现潜在客户。

## 核心链路

监控源管理 → 采集任务 → MediaCrawler 采集 → 帖子池 → 评论池 → 线索识别 → 线索池 → 今日获客报告 → CSV 导出 → 同行账号发现池

## 当前能力

- **采集器**：支持 `media_crawler`（真实采集）和 `mock`（演示采集，需启用）
- **支持平台**：小红书（xhs）、抖音（douyin）、知乎（zhihu）
- **监控源类型**：关键词搜索、同行账号、指定帖子链接、爆款规则
- **线索状态流转**：新线索 → 已跟进 → 有意向 → 无效 / 已转化
- **今日报告**：扫描概况、A级线索详情、典型证据、建议跟进话术、发现的同行账号、明日建议
- **同行发现**：自动发现同行账号，审核通过后加入监控源
- **演示模式**：无需 MediaCrawler 服务即可跑通完整链路

## 目录结构

```text
loan-radar/
  backend/
    app/           # FastAPI 后端
    alembic/       # 数据库迁移
    scripts/       # Smoke Test 等脚本
  frontend/
    src/           # React + TypeScript 前端
  docs/           # 产品和开发文档
```

## 本地启动

### 方式一：使用 MediaCrawler 真实采集

#### 1. 启动 MediaCrawler API 服务

```bash
cd D:\Project\MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

#### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload
```

#### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

#### 4. 验证服务

- 后端健康检查：`curl http://localhost:8001/health`
- MediaCrawler 状态：`curl http://localhost:8001/api/monitor-sources/media-crawler/health`
- 前端页面：`http://localhost:5173`

### 方式二：使用演示模式（无需 MediaCrawler）

如果 MediaCrawler API 服务不在线，可以使用 Mock 演示模式跑通完整链路。

#### 1. 启动后端（启用演示模式）

Windows PowerShell：

```powershell
cd backend
$env:ENABLE_MOCK_COLLECTOR = "true"
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload
```

Linux / macOS：

```bash
cd backend
ENABLE_MOCK_COLLECTOR=true pip install -r requirements.txt
alembic upgrade head
ENABLE_MOCK_COLLECTOR=true uvicorn app.main:app --port 8001 --reload
```

#### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

#### 3. 一键生成演示数据

方式一：使用脚本直接初始化（推荐）

```powershell
cd backend
python scripts/seed_demo_data.py
```

方式二：通过 API 触发

```bash
curl -X POST http://localhost:8001/api/monitor-sources/demo/generate
```

或在前端监控源页面点击"🎭 一键生成演示数据"按钮。

脚本运行后生成：
- 3 个监控源（关键词、同行账号、指定帖子）
- 10 条帖子、50 条评论、29+ 条线索（含 A/B/C/D 四个等级）
- 5 个待审核同行账号
- 1 份今日报告

脚本支持重复运行，会先清理旧 demo 数据再重新生成。所有演示数据标记 `raw_data.demo = true`，不会与真实数据混淆。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_MOCK_COLLECTOR` | `false` | 是否启用演示采集器。设为 `true` 后可选择 mock 采集器或一键生成演示数据 |
| `MEDIA_CRAWLER_HOME` | - | MediaCrawler 目录路径，设置后使用内嵌模式 |
| `SMOKE_MODE` | `demo` | 验收脚本模式：`demo`（MockCollector 演示验收）或 `real`（真实 MediaCrawler 采集验收） |
| `SMOKE_BASE_URL` | `http://127.0.0.1:8001` | Smoke Test 后端地址 |
| `SMOKE_TIMEOUT_SECONDS` | `30` | HTTP 请求超时 |
| `CRAWL_WAIT_SECONDS` | `15` | 等待采集完成秒数 |
| `SMOKE_REPORT_DIR` | `reports` | 验收报告输出目录 |

## 交付验收脚本

验收脚本验证完整链路：健康检查 → 创建监控源 → 触发采集 → 帖子/评论/线索 → 日报 → CSV 导出。

### demo 模式（无需 MediaCrawler）

```powershell
# 1. 启动后端（启用演示模式）
$env:ENABLE_MOCK_COLLECTOR = "true"
uvicorn app.main:app --port 8001 --reload

# 2. 运行验收脚本
$env:SMOKE_MODE = "demo"
python backend/scripts/media_crawler_smoke_test.py
```

### real 模式（真实采集）

```powershell
# 1. 启动 MediaCrawler API 服务
# 2. 启动后端
uvicorn app.main:app --port 8001 --reload

# 3. 运行验收脚本
$env:SMOKE_MODE = "real"
python backend/scripts/media_crawler_smoke_test.py
```

验收结果输出到 `reports/smoke_test_result.json`，包含每步 PASS/FAIL、耗时、关键数量、失败原因和修复建议。

## 文档索引

- `docs/DELIVERY_GUIDE.md`：交付指南（系统定位、部署方式、合规边界、常见问题）
- `docs/ACCEPTANCE_CHECKLIST.md`：交付验收清单（15 项逐项检查）
- `docs/PRD.md`：产品目标、范围和阶段边界
- `docs/DEMO_FLOW.md`：Demo 演示流程（含演示模式说明）
- `docs/API.md`：接口文档
- `docs/DB_DESIGN.md`：数据库设计
- `docs/TASK_BACKLOG.md`：任务拆分和优先级

## 本阶段不做

- 不做 CRM、员工管理、复杂权限、自动发布
- 不做登录绕过、验证码处理、代理池、Cookie 池
- 不做指纹伪装、风控绕过、反爬绕过
