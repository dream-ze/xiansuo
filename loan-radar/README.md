# 智获客 · 助贷线索雷达

面向助贷行业的获客线索雷达，基于 MediaCrawler 实现多平台真实采集，帮助助贷从业者从社交媒体发现潜在客户。集成小红书运营模块，支持账号管理、内容创作、AI 改写与自动发布。

## 核心链路

### 线索雷达

```
监控源管理 → 定时采集调度 → 采集任务队列 → MediaCrawler 采集 → 时间范围过滤 → 帖子池 → 评论池 → 线索识别与去重 → 线索池 → 线索转 CRM → 轻 CRM 跟进台 → 今日获客报告 → CSV/Markdown 导出 → 同行账号发现 → 评分规则管理 → 仪表板
```

### 小红书运营

```
账号矩阵管理（QR/手机/Cookie 登录） → 笔记发现与收藏 → 关键词组管理 → AI 内容改写/生成 → 图片工坊/视频工坊 → 草稿工坊 → 发布中心 → 自动运营任务 → 数据洞察
```

## 当前能力

### 线索雷达

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

### 小红书运营

- **用户认证**：注册/登录/JWT Token（access + refresh），密码 PBKDF2 加密
- **账号矩阵管理**：小红书 PC 端 / 创作者端账号管理，支持二维码登录、手机验证码登录、Cookie 导入，Cookie 加密存储，PC Cookie 自动同步创作者端
- **笔记发现与收藏**：基于账号批量采集小红书笔记，笔记详情、评论、素材（图片/视频）保存
- **关键词组管理**：分组管理采集关键词，支持多平台（xhs/douyin/kuaishou/weibo/xianyu/taobao）
- **AI 内容创作**：
  - 笔记改写（基于参考笔记 AI 改写）
  - 笔记生成（主题 + 参考 + 指令）
  - 标题生成、标签生成、文本润色
  - AI 封面图生成、AI 图片生成
  - 图片描述、视频描述
- **图片工坊**：图片上传、AI 合成封面图、图片缩放裁剪
- **视频工坊**：视频上传、ffmpeg 截取封面帧、AI 视频描述
- **草稿工坊**：AI 草稿管理、编辑、发送至发布中心
- **发布中心**：小红书创作者端发布（即时/定时），支持话题、位置、隐私设置，素材上传，发布状态跟踪
- **自动运营**：自动发布任务配置，关键词驱动，调度执行（手动/定时/周期）
- **数据洞察**：运营总览（笔记数、账号健康度、互动数据）、热门内容、热门话题、评论分析、竞品对标
- **标签系统**：笔记标签管理，标签颜色自定义
- **通知系统**：站内通知（采集/线索/任务/账号/发布事件），未读计数，按级别分类
- **任务中心**：统一任务管理，任务状态/进度/耗时/子任务，调度器状态
- **模型配置**：AI 模型管理（文本/图片），API Key 加密存储，默认模型切换
- **文件管理**：媒体文件上传/下载，图片合成/缩放，文件权限校验

## 前端页面

### 线索雷达

| 路由 | 菜单名称 | 说明 |
|------|----------|------|
| `/` | 工作台 | 仪表板：全局统计、CRM 提醒、MediaCrawler 健康状态 |
| `/collection` | 采集中心 | 监控源管理 + 采集任务中心（双 Tab） |
| `/posts` | 帖子池 | 采集帖子列表 |
| `/leads` | 线索池 | 线索管理、评论池、评分规则（子路由） |
| `/crm` | CRM 跟进 | CRM 仪表板 + 客户列表 + 跟进记录 |
| `/pending-competitors` | 同行发现 | 同行账号审核 |
| `/daily-reports` | 获客报告 | 今日报告生成与展示 |

### 小红书运营

| 路由 | 菜单名称 | 说明 |
|------|----------|------|
| `/xhs/dashboard` | 运营总览 | XHS 运营数据概览 |
| `/xhs/accounts` | 账号矩阵 | 小红书账号管理（QR/手机/Cookie 登录） |
| `/xhs/discovery` | 笔记发现 | 笔记搜索与收藏 |
| `/xhs/crawler` | 数据抓取 | 小红书数据采集 |
| `/xhs/keywords` | 关键词组 | 采集关键词分组管理 |
| `/xhs/analytics` | 数据洞察 | 运营数据分析 |
| `/xhs/image-studio` | 图片工坊 | 图片上传、AI 封面合成、缩放裁剪 |
| `/xhs/video-studio` | 视频工坊 | 视频上传、封面截取、AI 描述 |
| `/xhs/library` | 内容库 | 已收藏笔记管理 |
| `/xhs/drafts` | 草稿工坊 | AI 草稿编辑与管理 |
| `/xhs/publish` | 发布中心 | 小红书笔记发布 |
| `/xhs/auto-ops` | 自动运营 | 自动发布任务配置 |

### 通用

| 路由 | 菜单名称 | 说明 |
|------|----------|------|
| `/login` | 登录 | 用户登录/注册 |
| `/tasks` | 任务中心 | 统一任务管理与调度状态 |
| `/models` | 模型配置 | AI 模型（文本/图片）管理 |
| `/settings` | 系统设置 | 系统参数配置 |

## 目录结构

```text
loan-radar/
  apis/              # 小红书 API 封装（PC/创作者端 API + 登录 API）
  backend/
    app/
      adapters/      # 平台适配器（XHS PC/创作者端 API 适配器）
        xhs/         # 小红书适配器（creator_api, creator_login, pc_api, pc_login）
      api/routes/    # API 路由（29 个模块）
      collectors/    # 采集器
        media_crawler/  # MediaCrawler 采集器（HTTP Bridge + 内嵌模式）
        xhs_sdk/     # 小红书 SDK 采集器
        _deprecated/ # 已废弃采集器
      services/      # 业务逻辑（25+ 个服务）
      models/        # 数据模型（22 个模型）
      schemas/       # Pydantic Schemas
      core/          # 核心模块（config, database, security, deps, platforms, time）
      config/        # 评分规则配置
      utils/         # 工具函数
    alembic/         # 数据库迁移（17 个版本）
    scripts/         # Smoke Test 等脚本
    storage/         # 本地文件存储（媒体文件）
  frontend/
    src/
      pages/         # 页面组件（20+ 个页面）
        xhs/         # 小红书运营页面（12 个）
        LeadsPage/   # 线索池（含子组件）
      components/    # 通用组件
        account/     # 账号管理组件（QR 登录/手机登录/Cookie 导入）
      api/           # API 客户端（雷达 + XHS）
      lib/           # 工具库（platforms, time）
      routes/        # 路由配置
  mediacrawler/      # MediaCrawler 子项目
  static/            # 静态资源（XHS JS 脚本、前端截图）
  xhs_utils/         # 小红书工具库（签名、Cookie、HTTP 等）
  docs/              # 产品和开发文档
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
| `DATABASE_URL` | `postgresql+psycopg2://loan_radar:loan_radar_password@localhost:5432/loan_radar` | 数据库连接串 |
| `APP_ENV` | `development` | 运行环境（production 时禁用演示数据接口） |
| `SECRET_KEY` | `dev-only-change-me-in-production-32ch` | JWT 签名密钥（生产环境必须修改） |
| `FERNET_KEY` | - | Cookie/API Key 加密密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access Token 过期时间（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh Token 过期时间（天） |
| `MEDIA_CRAWLER_HOME` | - | MediaCrawler 目录路径，设置后使用内嵌模式 |
| `MEDIA_CRAWLER_API_URL` | `http://127.0.0.1:8080` | MediaCrawler API 地址 |
| `MEDIA_CRAWLER_TIMEOUT` | `300` | MediaCrawler 请求超时（秒） |
| `ENABLE_MOCK_COLLECTOR` | `false` | 是否启用演示采集器 |
| `SCHEDULER_ENABLED` | `true` | 是否启用定时调度 |
| `SCHEDULER_INTERVAL_SECONDS` | `60` | 调度器检查间隔（秒） |
| `CORS_ORIGINS` | `http://localhost:5173,...` | CORS 允许的来源 |
| `ASSET_STORAGE_TYPE` | `local` | 资产存储类型 |
| `FRONTEND_SERVE_STATIC` | `false` | 是否由后端服务前端静态文件 |
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
- `docs/API.md`：接口文档（29 个模块）
- `docs/DB_DESIGN.md`：数据库设计（22 个模型）
- `docs/DEMO_FLOW.md`：Demo 演示流程
- `docs/TASK_BACKLOG.md`：任务拆分和优先级

## 本阶段不做

- 不做员工管理、复杂权限
- 不做登录绕过、验证码处理、代理池
- 不做指纹伪装、风控绕过、反爬绕过
- 不做多租户、智能体编排
