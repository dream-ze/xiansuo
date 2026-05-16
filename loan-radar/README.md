# 智获客 · 助贷线索雷达 MVP

面向助贷行业的获客线索雷达，基于 MediaCrawler 实现多平台真实采集，帮助助贷从业者从社交媒体发现潜在客户。

## 核心链路

监控源管理 → 采集任务 → MediaCrawler 采集 → 帖子池 → 评论池 → 线索识别 → 线索池 → 今日获客报告 → CSV 导出 → 同行账号发现池

## 当前能力

- **采集器**：仅支持 `media_crawler`（基于 MediaCrawler 开源项目）
- **支持平台**：小红书（xhs）、抖音（douyin）、知乎（zhihu）
- **监控源类型**：关键词搜索、同行账号、指定帖子链接、爆款规则
- **线索状态流转**：新线索 → 已跟进 → 有意向 → 无效 / 已转化
- **今日报告**：扫描概况、A级线索详情、典型证据、建议跟进话术、发现的同行账号、明日建议
- **同行发现**：自动发现同行账号，审核通过后加入监控源

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

### 1. 启动 MediaCrawler API 服务

```bash
cd D:\Project\MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 验证服务

- 后端健康检查：`curl http://localhost:8001/health`
- MediaCrawler 状态：`curl http://localhost:8001/api/monitor-sources/media-crawler/health`
- 前端页面：`http://localhost:5173`

## Smoke Test

```bash
python backend/scripts/media_crawler_smoke_test.py
```

环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SMOKE_BASE_URL` | `http://127.0.0.1:8001` | 后端地址 |
| `SMOKE_TIMEOUT_SECONDS` | `30` | HTTP 请求超时 |
| `CRAWL_WAIT_SECONDS` | `10` | 等待采集完成秒数 |

## 文档索引

- `docs/PRD.md`：产品目标、范围和阶段边界
- `docs/DEMO_FLOW.md`：Demo 演示流程
- `docs/TASK_BACKLOG.md`：任务拆分和优先级
- `docs/API.md`：接口文档
- `docs/DB_DESIGN.md`：数据库设计

## 本阶段不做

- 不做 CRM、员工管理、复杂权限、自动发布
- 不做登录绕过、验证码处理、代理池、Cookie 池
- 不做指纹伪装、风控绕过、反爬绕过
