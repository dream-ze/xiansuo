# Demo 演示流程

## 目标

用 5 到 8 分钟展示线索雷达的 MediaCrawler 采集能力：

1. 关键词搜索采集可稳定运行。
2. 指定帖子链接可以采集，成功或失败都有可核验结果。
3. 线索识别、日报、导出完整链路可跑通。

## 前置条件

1. 启动 MediaCrawler API 服务：

```bash
cd D:\Project\MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

2. 启动后端：

```bash
cd backend
uvicorn app.main:app --reload
```

3. 启动前端：

```bash
cd frontend
npm run dev
```

4. 确认 MediaCrawler 健康检查通过：访问 `http://localhost:8001/api/monitor-sources/media-crawler/health`

## 演示路径

1. 打开前端首页（仪表板），查看统计概览。
2. 进入"监控源管理"。
3. 创建关键词监控源：
   - `source_type`: `keyword`
   - `platform`: `xhs`（小红书）
   - `collector_type`: `media_crawler`
   - `value`: `征信花了`
4. 点击"立即采集"，进入采集任务中心确认任务状态。
5. 采集成功后，进入帖子池、评论池，展示采集到的真实数据。
6. 进入线索池，展示线索识别结果（A/B/C/D 等级），点击来源帖子可跳转。
7. 点击"导出 CSV"，下载线索数据。
8. 进入今日报告，点击"生成今日报告"。
9. 回到监控源管理，创建指定帖子监控源：
   - `source_type`: `manual_post`
   - `platform`: `xhs`
   - `collector_type`: `media_crawler`
   - `value`: 一个小红书笔记链接
10. 点击"立即采集"。
11. 如果成功，进入帖子池查看原链接，进入评论池按帖子 ID 核验评论，再进入线索池查看是否识别出线索。
12. 如果失败，进入采集任务中心展示 `error_message`，说明系统会把采集失败记录为任务状态，不影响主服务。

## 讲解边界

本 Demo 不做登录绕过、验证码、代理池、批量搜索或反爬绕过。当前仅支持小红书、抖音、知乎三个平台。MediaCrawler 采集 MVP 的价值是验证"关键词/帖子链接 -> 帖子/评论 -> 线索识别 -> 报告/导出"这条链路。

## 无 MediaCrawler 服务时的演示

如果 MediaCrawler API 服务不在线，当前系统无法完成采集演示（Factory 仅支持 media_crawler）。后续计划恢复 MockCollector 到 Factory 路由，保证无外部服务时演示可跑。
