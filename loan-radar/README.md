# 智获客 · 助贷线索雷达 MVP

面向助贷行业的获客线索雷达，基于 MediaCrawler 实现多平台真实采集，帮助助贷从业者从社交媒体发现潜在客户。

## 核心链路

```
监控源管理 → 定时采集调度 → 采集任务队列 → MediaCrawler 采集 → 时间范围过滤 → 帖子池 → 评论池 → 线索识别与去重 → 线索池 → 线索转 CRM → 轻 CRM 跟进台 → 今日获客报告 → CSV/Markdown 导出 → 同行账号发现 → 评分规则管理 → 仪表板
```

## 当前能力

- **采集器**：仅支持 `media_crawler`（基于 MediaCrawler 开源项目）
- **支持平台**：小红书（xhs）、抖音（douyin）、知乎（zhihu）
- **监控源类型**：关键词搜索、同行账号、指定帖子链接、爆款规则
- **时间范围过滤**：支持 7d/15d/30d/90d 时间范围采集，设置后自动提升采集量（max_posts 提升至 80）并按发布时间过滤帖子和评论
- **线索状态流转**：新线索 → 已跟进 → 有意向 → 无效 / 已转化
- **线索去重**：同用户相似评论去重 + 相同内容去重，支持重复标记和分组
- **轻 CRM 跟进台**：线索转客户（两种入口）、手动录入客户、跟进记录、跟进时间提醒（已逾期/今日/明日/本周）、7 种客户状态管理
- **今日报告**：扫描概况、A级线索详情、典型证据、建议跟进话术、同行账号、明日建议、CRM 统计，支持 Markdown 导出
- **同行发现**：自动发现同行账号，审核通过后加入监控源
- **CSV 导出**：线索池支持一键导出 CSV
- **定时采集**：支持 Cron 表达式配置定时采集（APScheduler）
- **评分规则管理**：可视化编辑线索评分规则，单条/批量测试评分效果，热重载
- **仪表板**：全局统计概览，今日/昨日对比，CRM 跟进提醒，MediaCrawler 健康状态
- **采集任务队列**：同一时间仅执行一个采集任务，支持队列状态查询
- **失败类型分类**：8 种失败类型，前端展示中文标签和处理建议

## 前端页面

| 路由 | 菜单名称 | 说明 |
|------|----------|------|
| `/` | 工作台 | 仪表板：全局统计、CRM 提醒、MediaCrawler 健康状态 |
| `/collection` | 监控源 | 监控源管理 + 采集任务中心（双 Tab） |
| `/leads` | 线索池 | 线索管理、帖子池、评论池、评分规则（子路由） |
| `/crm` | CRM 跟进 | CRM 仪表板 + 客户列表 + 跟进记录 |
| `/pending-competitors` | 同行发现 | 同行账号审核 |
| `/daily-reports` | 获客报告 | 今日报告生成与展示 |

## 目录结构

```text
loan-radar/
  backend/
    app/           # FastAPI 后端
      collectors/  # 采集器
        media_crawler/  # MediaCrawler 采集器（HTTP Bridge + 内嵌模式）
        _deprecated/    # 已废弃采集器（mock/playwright 等）
      api/routes/  # API 路由（14 个模块）
      services/    # 业务逻辑（17 个服务）
      models/      # 数据模型（9 个模型）
      schemas/     # Pydantic Schemas
      config/      # 评分规则配置
    alembic/       # 数据库迁移（12 个版本）
    scripts/       # Smoke Test 等脚本
  frontend/
    src/           # React + TypeScript + Ant Design 前端
      pages/       # 页面组件
      api/         # API 客户端
      routes/      # 路由配置
  mediacrawler/   # MediaCrawler 子项目
  docs/           # 产品和开发文档
```

## 本地启动

### 1. 启动 PostgreSQL

```bash
docker compose up postgres -d
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

### 5. 生成演示数据

```powershell
cd backend
python scripts/seed_demo_data.py
```

脚本运行后生成：
- 3 个监控源（关键词、同行账号、指定帖子）
- 10 条帖子、50 条评论、29+ 条线索（含 A/B/C/D 四个等级）
- 5 个待审核同行账号
- 1 份今日报告

脚本支持重复运行，会先清理旧 demo 数据再重新生成。所有演示数据标记 `raw_data.demo = true`，不会与真实数据混淆。

## Docker 部署

一键启动全部服务（PostgreSQL + MediaCrawler + 后端 + 前端）：

```bash
docker compose up -d
```

服务端口：
- 前端：`http://localhost:80`
- 后端 API：`http://localhost:8001`
- MediaCrawler API：`http://localhost:8080`
- PostgreSQL：`localhost:5432`

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEDIA_CRAWLER_HOME` | - | MediaCrawler 目录路径，设置后使用内嵌模式 |
| `ENABLE_MOCK_COLLECTOR` | `false` | 是否启用演示采集器 |
| `DATABASE_URL` | `postgresql+psycopg2://loan_radar:loan_radar_password@localhost:5432/loan_radar` | 数据库连接串 |
| `APP_ENV` | `development` | 运行环境（production 时禁用演示数据接口） |
| `SMOKE_BASE_URL` | `http://127.0.0.1:8001` | Smoke Test 后端地址 |
| `SMOKE_TIMEOUT_SECONDS` | `30` | HTTP 请求超时 |
| `CRAWL_WAIT_SECONDS` | `15` | 等待采集完成秒数 |
| `SMOKE_REPORT_DIR` | `reports` | 验收报告输出目录 |

## 验收脚本

```powershell
cd backend
python smoke_test_demo.py
```

测试链路：创建 media_crawler 监控源 → 创建采集任务 → 采集失败不崩溃 → 写入错误信息 → 线索列表可查询 → 日报可生成 → 同行账号接口可用 → CSV 可导出

## 文档索引

- `docs/PRD.md`：产品目标、范围和阶段边界
- `docs/API.md`：接口文档（15 个模块）
- `docs/DB_DESIGN.md`：数据库设计（9 个模型）
- `docs/DEMO_FLOW.md`：Demo 演示流程
- `docs/TASK_BACKLOG.md`：任务拆分和优先级

## 本阶段不做

- 不做员工管理、复杂权限、自动发布
- 不做登录绕过、验证码处理、代理池、Cookie 池
- 不做指纹伪装、风控绕过、反爬绕过
- 不做多租户、智能体编排
