# 交付指南

> 版本：MVP 试用版 | 最后更新：2026-05

## 1. 系统定位

智获客 · 助贷线索雷达是一款面向助贷行业的社交媒体获客工具。系统通过 MediaCrawler 从小红书、抖音、知乎等平台采集公开帖子与评论，利用规则引擎自动识别潜在贷款需求，生成带评分、等级、跟进话术的线索，帮助助贷从业者高效发现意向客户。

**核心链路：**

```
监控源管理 → 采集任务 → 多平台采集 → 帖子池 → 评论池 → 线索识别 → 线索池 → 今日获客报告 → CSV 导出 → 同行账号发现
```

**当前版本为 MVP 试用版**，不承诺全平台覆盖、自动发布、CRM 集成、多租户等企业级能力。

## 2. 当前版本能力

| 能力 | 说明 |
|------|------|
| 多平台采集 | 小红书、抖音、知乎（依赖 MediaCrawler） |
| 监控源管理 | 关键词搜索、同行账号、指定帖子链接、爆款规则 |
| 线索识别 | 规则引擎评分，A/B/C/D 四级，含需求类型、风险等级、证据、跟进话术 |
| 线索去重 | 同平台同评论精确去重 + 同用户相似内容疑似重复标记 |
| 线索状态管理 | 新线索 → 已跟进 → 有意向 → 无效 / 已转化 |
| 今日获客报告 | 扫描概况、A级线索 Top 10、典型需求证据、同行发现、明日建议、合规提醒 |
| 报告导出 | 支持 Markdown 导出，文件名 `loan-radar-report-YYYY-MM-DD.md` |
| CSV 导出 | 线索数据导出，含重复标记列 |
| 同行账号发现 | 自动发现疑似同行，支持审核通过后加入监控源 |
| 获客驾驶舱 | 首页展示 7 项核心指标、最近 A 级线索、采集任务状态、MediaCrawler 健康状态 |
| 采集任务中心 | 任务列表 + 详情弹窗（基础信息、采集配置、结果统计、错误与修复建议） |
| 失败重试 | 失败任务支持一键重试，含失败类型分类和修复建议 |
| 演示模式 | 无需 MediaCrawler 即可跑通完整链路，一键生成演示数据 |

## 3. 支持平台

| 平台 | 代码 | 采集方式 | 状态 |
|------|------|----------|------|
| 小红书 | `xhs` | MediaCrawler API | 已支持 |
| 抖音 | `douyin` | MediaCrawler API | 已支持 |
| 知乎 | `zhihu` | MediaCrawler API | 已支持 |

## 4. 不支持内容

本版本为 MVP 试用版，以下内容**不在当前范围内**：

- **平台**：微信、微博、快手、B 站、贴吧等
- **功能**：CRM 集成、员工管理、复杂权限、自动发布、多租户
- **技术**：登录绕过、验证码处理、代理池、Cookie 池、指纹伪装、风控绕过、反爬绕过
- **数据**：私信采集、付费内容采集、非公开内容采集

## 5. 本地部署方式

### 5.1 前置条件

- Python 3.11+
- Node.js 20+
- SQLite（内置，无需额外安装）
- MediaCrawler（如需真实采集）

### 5.2 启动后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload
```

### 5.3 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5.4 验证服务

| 检查项 | 地址 | 期望结果 |
|--------|------|----------|
| 后端健康 | `http://localhost:8001/health` | `{"status": "ok"}` |
| 前端页面 | `http://localhost:5173` | 首页加载成功 |
| MediaCrawler | `http://localhost:8001/api/monitor-sources/media-crawler/health` | `status: "ok"` |

## 6. Docker Compose 部署方式

项目已提供后端和前端 Dockerfile，可使用 Docker Compose 一键部署。

### 6.1 docker-compose.yml 示例

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - ENABLE_MOCK_COLLECTOR=false
      - MEDIA_CRAWLER_HOME=/opt/MediaCrawler
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

### 6.2 启动

```bash
docker-compose up -d --build
```

### 6.3 验证

- 前端：`http://localhost`
- 后端 API：`http://localhost:8001/health`

### 6.4 注意事项

- 前端 Nginx 配置已包含 `/api/` 反向代理到后端
- 数据库文件默认存储在 `/app/data/`，建议挂载 volume 持久化
- 如需真实采集，需确保 MediaCrawler 服务可达

## 7. MediaCrawler 依赖说明

### 7.1 什么是 MediaCrawler

MediaCrawler 是一个开源的社交媒体采集框架，支持小红书、抖音、知乎等平台的数据采集。本系统通过 MediaCrawler API 实现真实采集。

### 7.2 两种接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| API 模式 | MediaCrawler 作为独立 API 服务运行，本系统通过 HTTP 调用 | 生产环境 |
| 内嵌模式 | 设置 `MEDIA_CRAWLER_HOME` 环境变量，本系统直接调用 MediaCrawler | 开发调试 |

### 7.3 启动 MediaCrawler API 服务

```bash
cd /path/to/MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

### 7.4 健康检查

```bash
curl http://localhost:8001/api/monitor-sources/media-crawler/health
```

正常返回：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "mode": "api",
    "supported_platforms": [
      {"value": "xhs", "label": "小红书"},
      {"value": "douyin", "label": "抖音"},
      {"value": "zhihu", "label": "知乎"}
    ]
  }
}
```

### 7.5 MediaCrawler 不可用时的表现

- 首页获客驾驶舱显示黄色告警条："MediaCrawler 不在线，无法执行真实采集"
- 创建采集任务会失败，任务状态变为 `failed`，失败类型为 `采集服务不可用`
- 建议切换为演示模式或启动 MediaCrawler 服务

## 8. Demo 模式说明

### 8.1 适用场景

- 客户演示，无需搭建 MediaCrawler 环境
- 功能验收，验证完整链路
- 开发调试，快速生成测试数据

### 8.2 启用方式

设置环境变量 `ENABLE_MOCK_COLLECTOR=true`：

```powershell
# Windows PowerShell
$env:ENABLE_MOCK_COLLECTOR = "true"
uvicorn app.main:app --port 8001 --reload
```

```bash
# Linux / macOS
ENABLE_MOCK_COLLECTOR=true uvicorn app.main:app --port 8001 --reload
```

### 8.3 一键生成演示数据

```powershell
cd backend
python scripts/seed_demo_data.py
```

生成内容：

| 数据 | 数量 |
|------|------|
| 监控源 | 3 个（关键词、同行账号、指定帖子） |
| 帖子 | 10 条 |
| 评论 | 50 条 |
| 线索 | 29+ 条（含 A/B/C/D 四级） |
| 待审核同行 | 5 个 |
| 今日报告 | 1 份 |

### 8.4 数据安全

- 所有演示数据标记 `raw_data.demo = true`
- 演示数据 URL 使用 `demo.local` 域名
- `ENABLE_MOCK_COLLECTOR` 默认 `false`，生产环境不会意外启用
- 脚本支持重复运行，会先清理旧 demo 数据

## 9. 常见问题

### Q: 启动后端报错 `ModuleNotFoundError`

确保已安装依赖：`pip install -r requirements.txt`，并确认 Python 版本为 3.11+。

### Q: 前端页面空白

1. 确认后端已启动且 `http://localhost:8001/health` 返回正常
2. 检查浏览器控制台是否有跨域错误
3. 如后端端口非 8001，需设置 `VITE_API_BASE_URL` 环境变量

### Q: 采集任务一直处于"排队中"

1. 检查采集队列状态：`http://localhost:8001/api/collection/tasks/queue/status`
2. 确认 MediaCrawler 服务是否在线
3. 查看后端日志是否有异常

### Q: 线索数为 0

1. 确认评论内容包含贷款相关关键词
2. 检查评分规则配置：`http://localhost:8001/api/scoring-rules`
3. 确认评论的 `is_suspected_demand` 字段是否为 `true`

### Q: 报告生成失败

1. 确认当日有采集数据
2. 检查后端日志中的日报生成错误信息
3. 尝试指定平台生成：`POST /api/daily-reports/generate?platform=xhs`

### Q: 数据库迁移失败

```bash
cd backend
alembic upgrade head
```

如仍有问题，检查 `alembic/versions/` 目录下迁移文件是否完整。

## 10. 采集失败原因说明

系统对采集失败进行自动分类，每种类型提供原因分析和修复建议：

| 失败类型 | 标签 | 原因 | 修复建议 |
|----------|------|------|----------|
| `media_crawler_unreachable` | 采集服务不可用 | MediaCrawler API 未启动或无法连接 | 启动 MediaCrawler 服务，或切换为演示模式 |
| `platform_not_supported` | 平台不支持 | 当前采集器不支持该平台 | 选择支持的平台（小红书/抖音/知乎） |
| `auth_required` | 登录态失效 | Cookie 过期或账号登录态失效 | 重新获取平台 Cookie，更新监控源配置 |
| `captcha_or_risk_control` | 疑似风控拦截 | 触发验证码或风控策略 | 稍后重试，或更换账号/Cookie |
| `timeout` | 采集超时 | 任务在规定时间内未完成 | 检查网络，减少采集数量，稍后重试 |
| `empty_result` | 采集无结果 | 采集完成但无数据 | 检查关键词是否正确，目标平台是否有相关内容 |
| `parser_error` | 数据解析失败 | 采集到数据但解析出错 | 可能是平台页面结构变更，联系管理员 |
| `unknown` | 未知错误 | 未预期的错误 | 查看详细错误信息，联系管理员 |

在采集任务详情弹窗中，失败任务会显示完整的错误详情、原因分析和修复建议。

## 11. 客户演示流程

### 11.1 准备（2 分钟）

1. 确认后端和前端已启动
2. 运行 `python scripts/seed_demo_data.py` 生成演示数据
3. 打开前端首页，确认获客驾驶舱数据正常显示

### 11.2 演示步骤（5-8 分钟）

1. **首页驾驶舱**：展示核心指标（监控源、帖子、评论、线索、A级线索、待审核同行）
2. **监控源管理**：展示已创建的监控源，说明关键词/账号/帖子三种采集方式
3. **采集任务中心**：展示任务列表，点击"详情"查看采集结果统计和快捷操作
4. **线索池**：展示 A/B/C/D 级线索，演示状态修改、备注、去重标记
5. **今日获客报告**：点击"生成今日报告"，展示完整交付报告（扫描概况、A级线索、证据、同行发现、明日建议、合规提醒）
6. **CSV 导出**：点击"导出 CSV"，下载线索数据
7. **同行发现**：展示自动发现的同行账号，演示审核操作

### 11.3 演示要点

- 强调"从关键词到线索"的完整链路
- 展示 A 级线索的评分、证据和跟进话术
- 展示报告的客户可读性
- 说明合规边界（不做登录绕过、风控绕过）

## 12. 合规边界说明

### 12.1 系统原则

本系统仅采集社交媒体**公开可见**的帖子和评论，不涉及任何非公开内容。

### 12.2 不做内容

| 不做 | 说明 |
|------|------|
| 登录绕过 | 不破解平台登录机制 |
| 验证码处理 | 不自动识别或绕过验证码 |
| 代理池 | 不搭建或使用代理 IP 池 |
| Cookie 池 | 不批量管理或轮换 Cookie |
| 指纹伪装 | 不伪造浏览器指纹 |
| 风控绕过 | 不绕过平台风控策略 |
| 反爬绕过 | 不对抗平台反爬机制 |
| 私信采集 | 不采集用户私信内容 |
| 付费内容 | 不采集需付费才能查看的内容 |

### 12.3 跟进合规提醒

系统在今日获客报告中内置合规提醒：

- 跟进时**避免承诺下款**
- **避免夸大利率**
- **避免诱导负债**
- 建议使用**咨询/评估类话术**

### 12.4 数据使用

- 采集数据仅用于客户意向识别和跟进
- 不对采集数据进行二次分发
- 演示数据标记 `raw_data.demo = true`，与真实数据严格区分
- 建议定期清理过期数据
