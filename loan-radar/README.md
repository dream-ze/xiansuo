# 智获客 · 助贷线索雷达

面向助贷行业的一体化获客系统，集成线索雷达和小红书运营，帮助助贷从业者从社交媒体发现潜在客户并自动运营内容。

## 一体化链路

```
配置账号/关键词/同行账号 → 采集内容 → 帖子池/评论池 → 识别贷款需求线索 → 线索池分级 → CRM 跟进 → 每日获客报告
同时：帖子池 → 收藏到内容库 → AI 改写生成小红书草稿 → 发布中心 → 数据洞察
```

## 一键启动

### Docker 部署（推荐）

```bash
docker compose up -d
```

启动后访问：`http://localhost`

### 本地开发

```bash
# 1. 启动 PostgreSQL
docker compose up postgres -d

# 2. 启动后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload

# 3. 启动前端
cd frontend
npm install
npm run dev
```

## 首次启动说明

1. 启动服务后，打开 `http://localhost`（Docker 部署）或 `http://localhost:5173`（本地开发）
2. 首次使用需注册账号：点击登录页"注册"，输入用户名和密码
3. 生成演示数据（可选）：
   - 方式一：在采集中心页面点击"生成演示数据"
   - 方式二：运行 `cd backend && python scripts/seed_demo_data.py`

## 默认端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 (Nginx) | 80 | Web UI 入口 |
| 后端 API | 8001 | FastAPI 服务 |
| MediaCrawler | 8080 | 采集引擎 |
| PostgreSQL | 5432 | 数据库 |

## 环境变量

### 后端关键环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_ENV` | `development` | 环境：development / production |
| `DATABASE_URL` | `postgresql+psycopg2://loan_radar:loan_radar_password@localhost:5432/loan_radar` | 数据库连接 |
| `SECRET_KEY` | 开发默认值 | JWT 签名密钥，生产环境必须设置 |
| `MEDIA_CRAWLER_API_URL` | `http://127.0.0.1:8080` | MediaCrawler API 地址 |
| `SCHEDULER_ENABLED` | `true` | 是否启用定时采集调度 |
| `CORS_ORIGINS` | `http://localhost:5173,...` | CORS 允许的来源 |

### 前端环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE_URL` | `""` (同域) | API 基础 URL，生产环境留空由 Nginx 代理 |

## 小红书账号配置

1. 进入 **XHS 运营 → 账号矩阵**
2. 选择登录方式：
   - **二维码登录**：PC 端扫码登录
   - **手机验证码登录**：输入手机号获取验证码
   - **Cookie 导入**：从浏览器复制 Cookie 导入
3. 登录成功后，Cookie 加密存储，PC Cookie 自动同步到创作者端
4. 建议至少配置一个 PC 账号（用于搜索/采集）和一个 Creator 账号（用于发布）

## 演示数据生成

```powershell
cd backend
python scripts/seed_demo_data.py
```

生成内容：
- 3 个监控源（关键词、同行账号、指定帖子）
- 10 条帖子、50 条评论、29+ 条线索（含 A/B/C/D 四个等级）
- 5 个待审核同行账号
- 1 份今日报告

## 完整演示流程

1. 打开首页 → 登录
2. 采集中心 → 添加关键词"征信花了" → 点击采集
3. 任务进入队列 → 查看采集任务状态
4. 采集完成（或失败但有明确错误信息）
5. 帖子池/评论池 → 查看采集内容
6. 线索池 → 查看评分、证据链、跟进话术
7. A 级线索 → 转入 CRM
8. CRM 跟进台 → 跟进记录
9. 获客报告 → 生成今日报告
10. 帖子池 → 选择帖子 → 收藏到内容库
11. 内容库 → 选择笔记 → 生成小红书草稿
12. 草稿工坊 → 编辑草稿 → 发送到发布中心
13. 发布中心 → 确认发布
14. 自动运营 → 创建任务 → 立即执行 → 查看生成的草稿

## 常见问题排查

### 前端无法连接后端

- 检查后端是否启动：`curl http://localhost:8001/health`
- Docker 部署：确保 Nginx 配置中 `proxy_pass` 指向 `loan-radar-backend:8001`
- 本地开发：确保 `VITE_API_BASE_URL` 设置为 `http://localhost:8001`

### 采集任务一直排队

- 检查 MediaCrawler 是否健康：`curl http://localhost:8080/api/health`
- 检查是否有 Cookie：采集中心 → MediaCrawler 健康状态
- 查看采集任务错误信息：采集中心 → 任务详情

### 数据库迁移失败

- 确保 PostgreSQL 正在运行
- 检查 `DATABASE_URL` 环境变量
- 手动执行：`cd backend && alembic upgrade head`

### AI 生成失败

- 检查模型配置：模型配置页面 → 确认默认文本模型已设置
- 确认 API Key 有效
- 自动运营任务在 AI 不可用时会回退到模板生成

## 重要声明

**交付版采用"自动生成 + 人工确认发布"模式**：
- 草稿生成后需人工审核确认，不会自动真实发布
- 不做风控绕过、验证码绕过、指纹伪装
- 采集行为依赖 MediaCrawler 开源项目，需合法合规使用
- 小红书发布需要有效的创作者端 Cookie，Cookie 过期需重新登录

## 目录结构

```text
loan-radar/
  apis/              # 小红书 API 封装
  backend/
    app/
      adapters/      # 平台适配器
      api/routes/    # API 路由（29 个模块）
      collectors/    # 采集器（media_crawler / xhs_sdk）
      services/      # 业务逻辑（25+ 个服务）
      models/        # 数据模型
      schemas/       # Pydantic Schemas
      core/          # 核心模块
    alembic/         # 数据库迁移
    scripts/         # 工具脚本
    entrypoint.sh    # Docker 入口脚本
  frontend/
    src/
      pages/         # 页面组件
      api/           # API 客户端
      routes/        # 路由配置
    nginx.conf       # Nginx 配置
  mediacrawler/      # MediaCrawler 子项目
  scripts/           # 全局脚本
  docker-compose.yml # Docker Compose 配置
```
