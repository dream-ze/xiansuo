# Demo 演示流程

## 目标

用 5 到 8 分钟展示助贷线索雷达的完整 MVP 能力：

1. 关键词搜索采集可稳定运行。
2. 指定帖子链接可以采集，成功或失败都有可核验结果。
3. 线索识别、状态管理、日报、导出、同行发现完整链路可跑通。

## 前置条件

### 方式一：使用 MediaCrawler 真实采集

1. 启动 MediaCrawler API 服务：

```bash
cd D:\Project\MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

2. 启动后端：

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload
```

3. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

4. 确认 MediaCrawler 健康检查通过：访问 `http://localhost:8001/api/monitor-sources/media-crawler/health`

5. 运行 Smoke Test：

```bash
python backend/scripts/media_crawler_smoke_test.py
```

### 方式二：使用演示模式（无需 MediaCrawler）

如果 MediaCrawler API 服务不在线，可以使用 Mock 演示模式跑通完整链路。

1. 启动后端（设置环境变量）：

```bash
cd backend
ENABLE_MOCK_COLLECTOR=true pip install -r requirements.txt
alembic upgrade head
ENABLE_MOCK_COLLECTOR=true uvicorn app.main:app --port 8001 --reload
```

Windows PowerShell：

```powershell
cd backend
$env:ENABLE_MOCK_COLLECTOR = "true"
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --port 8001 --reload
```

2. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

3. 验证演示模式已启用：访问 `http://localhost:8001/api/collectors`，返回结果中应包含 `mock` 采集器。

4. 一键生成演示数据：

方式一：使用脚本直接初始化（推荐，无需启动后端）

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

脚本支持重复运行，会先清理旧 demo 数据再重新生成。

## 演示路径

### 使用真实采集（MediaCrawler 在线）

1. 打开前端首页（仪表板），查看统计概览。
2. 进入"监听源"页面，页面顶部提示"当前采集依赖 MediaCrawler API 服务"。
3. 创建关键词监控源：
   - `source_type`: `keyword`
   - `platform`: `xhs`（小红书）—— 平台选项仅展示 xhs/douyin/zhihu
   - `collector_type`: `media_crawler`（默认值，唯一选项）
   - `value`: `征信花了`
4. 点击"立即采集"，进入采集任务中心确认任务状态。
5. 在采集任务列表查看任务详情：
   - 列表展示：任务 ID、平台、来源类型、来源值、状态、帖子/评论/线索/同行数量、失败类型、开始/结束时间
   - 点击"详情"打开任务详情弹窗，分区展示基础信息、采集配置、采集结果统计
   - 失败任务：弹窗显示错误详情、原因分析、修复建议，支持一键"重试采集"
   - 运行中/排队中任务：弹窗显示 loading spinner 和当前进度
   - 成功任务：弹窗提供快捷入口（查看帖子、查看评论、查看线索、生成日报）
6. 采集成功后，进入帖子池、评论池，展示采集到的真实数据。
7. 进入线索池，展示线索识别结果（A/B/C/D 等级）：
   - 每条线索展示：来源平台、来源帖子、评论内容、命中证据、判断理由、跟进话术、跟进状态、备注
   - 可修改线索状态：新线索 → 已跟进 → 有意向 → 无效 / 已转化
   - 可添加备注
   - 点击来源帖子可跳转
8. 点击"导出 CSV"，下载线索数据（包含备注列）。
9. 进入今日报告，选择平台（全平台/小红书/抖音/知乎），点击"生成今日报告"：
   - **今日扫描概况**：监控源数量、帖子数量、评论数量、线索数量、A级线索数量，含线索等级分布条形图
   - **A级线索 Top 10**：用户名、评论内容、需求类型、判断理由、建议话术，按评分排序
   - **典型需求证据**：命中关键词标签、金额信息、高频需求柱状图、高频关键词标签云
   - **同行账号发现**：账号名、平台、发现原因、建议是否监控
   - **明日采集建议**：推荐关键词、推荐同行方向、推荐内容选题、跟进提示
   - **合规提醒**：避免承诺下款、避免夸大利率、避免诱导负债、建议使用咨询/评估类话术
   - 点击"复制摘要"可一键复制纯文本版报告
   - 空数据状态友好提示（如"今日暂无A级线索"）
10. 进入"同行发现"页面，查看自动发现的同行账号：
   - 支持通过/忽略操作
   - 通过后可加入监控源
11. 回到监听源管理，创建指定帖子监控源：
    - `source_type`: `manual_post`
    - `platform`: `xhs`
    - `value`: 一个小红书笔记链接
12. 点击"立即采集"。
13. 如果成功，进入帖子池查看原链接，进入评论池按帖子 ID 核验评论，再进入线索池查看是否识别出线索。
14. 如果失败，进入采集任务中心展示任务详情弹窗，查看错误信息、原因分析和修复建议，点击"重试采集"重新执行。

### 使用演示模式（无需 MediaCrawler）

1. 确保后端以 `ENABLE_MOCK_COLLECTOR=true` 启动。
2. 打开前端监控源页面，页面顶部显示"🎭 演示模式已启用"。
3. 点击"🎭 一键生成演示数据"按钮，系统自动创建 4 个演示监控源并触发采集：
   - 演示 - 征信花了（小红书/关键词）
   - 演示 - 急用5万周转（抖音/关键词）
   - 演示 - 负债高能不能做（知乎/关键词）
   - 演示 - 爆款规则（小红书/爆款规则）
4. 等待采集任务完成（Mock 采集器即时生成数据）。
5. 进入采集任务中心，查看任务列表和详情弹窗：
   - 列表展示：任务 ID、平台、来源类型、来源值、状态、帖子/评论/线索/同行数量、失败类型、开始/结束时间
   - 点击"详情"打开任务详情弹窗，分区展示基础信息、采集配置、采集结果统计
   - 成功任务提供快捷入口：查看帖子、查看评论、查看线索、生成日报
6. 进入帖子池，查看演示帖子（贴近助贷场景：征信花了、急用5万、负债高、有逾期等）。
7. 进入评论池，查看演示评论（包含需求类和非需求类评论）。
8. 进入线索池，展示线索识别结果（A/B/C/D 等级），可修改状态、添加备注、导出 CSV。
9. 进入今日报告，选择平台（全平台/小红书/抖音/知乎），点击"生成今日报告"，查看完整交付报告：
   - **今日扫描概况**：监控源数量、帖子数量、评论数量、线索数量、A级线索数量，含线索等级分布条形图
   - **A级线索 Top 10**：用户名、评论内容、需求类型、判断理由、建议话术，按评分排序
   - **典型需求证据**：命中关键词标签、金额信息、高频需求柱状图、高频关键词标签云
   - **同行账号发现**：账号名、平台、发现原因、建议是否监控
   - **明日采集建议**：推荐关键词、推荐同行方向、推荐内容选题、跟进提示
   - **合规提醒**：避免承诺下款、避免夸大利率、避免诱导负债、建议使用咨询/评估类话术
   - 点击"复制摘要"可一键复制纯文本版报告
   - 空数据状态友好提示（如"今日暂无A级线索"）
10. 进入"同行发现"页面，查看自动发现的疑似同行账号。
11. 所有演示数据均标记 `raw_data.demo = true`，可与真实数据区分。

也可以手动创建 mock 类型的监控源：
- `collector_type`: `mock`（演示采集模式）
- `source_type`: 任意（keyword/competitor_account/manual_post/hot_post_rule）
- `platform`: 任意
- `value`: 任意关键词

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENABLE_MOCK_COLLECTOR` | `false` | 是否启用演示采集器。设为 `true` 后，可在前端选择 mock 采集器或一键生成演示数据 |
| `MEDIA_CRAWLER_HOME` | - | MediaCrawler 目录路径，设置后使用内嵌模式 |

## API 接口

### 一键初始化演示数据（脚本方式）

```powershell
cd backend
python scripts/seed_demo_data.py
```

直接写入数据库生成完整演示数据，无需启动后端服务。支持重复运行（先清理旧 demo 数据）。

### 一键初始化演示数据（接口方式）

```
POST /api/monitor-sources/demo/seed
```

仅在开发环境（`APP_ENV != production`）可用，生产环境返回 403。

返回示例：

```json
{
  "success": true,
  "data": {
    "message": "演示数据初始化完成",
    "stats": {
      "sources": 3,
      "posts": 10,
      "comments": 50,
      "leads": 29,
      "lead_levels": {"A": 16, "B": 6, "C": 4, "D": 3},
      "competitors": 5,
      "crawl_tasks": 3,
      "report_date": "2026-05-17"
    },
    "tip": "所有演示数据均标记 raw_data.demo=true，可与真实数据区分"
  }
}
```

### 一键生成演示数据（采集方式）

```
POST /api/monitor-sources/demo/generate
```

仅在 `ENABLE_MOCK_COLLECTOR=true` 时可用，否则返回 403。

返回示例：

```json
{
  "success": true,
  "data": {
    "message": "演示数据生成中，请稍后查看帖子池、评论池、线索池和日报",
    "demo_sources": [
      {"id": 1, "name": "演示 - 征信花了", "source_type": "keyword", "platform": "xhs"}
    ],
    "crawl_tasks": [
      {"task_id": 1, "source_id": 1, "queue_position": 0}
    ],
    "tip": "所有演示数据均标记 raw_data.demo=true，可与真实数据区分"
  }
}
```

## 讲解边界

本 Demo 不做登录绕过、验证码、代理池、批量搜索或反爬绕过。当前仅支持小红书、抖音、知乎三个平台。MVP 的价值是验证"关键词/帖子链接 → 帖子/评论 → 线索识别 → 状态管理 → 报告/导出 → 同行发现"这条完整链路。日报页面已重构为客户可读的交付报告，包含扫描概况、A级线索详情、需求证据、同行发现、明日建议和合规提醒六大板块，支持按平台筛选和一键复制摘要。采集任务中心已增强，支持任务详情弹窗（基础信息、采集配置、结果统计、错误信息与修复建议）、失败任务重试、运行中任务 loading 状态、成功任务快捷跳转（帖子/评论/线索/日报）。

## 数据安全

- 演示模式生成的所有数据均标记 `raw_data.demo = true`
- 演示数据的 URL 使用 `demo.local` 域名，不会与真实数据混淆
- `ENABLE_MOCK_COLLECTOR` 默认为 `false`，生产环境不会意外启用演示模式
- 演示数据可通过 `raw_data.demo` 字段筛选和清理
