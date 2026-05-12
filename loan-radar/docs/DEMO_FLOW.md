# Demo 演示流程

## 目标

用 5 到 8 分钟展示线索雷达的两条能力：

1. Mock 主链路稳定可跑。
2. 指定公开帖子链接可以尝试真实采集，成功或失败都有可核验结果。

## 启动

后端：

```bash
cd backend
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm run dev
```

如需使用 Playwright 真实采集，先安装浏览器：

```bash
python -m playwright install chromium
```

## 演示路径

1. 打开前端首页。
2. 进入“监控源管理”。
3. 创建关键词监控源：
   - `source_type`: `keyword`
   - `platform`: `xhs`
   - `collector_type`: `mock`
   - `value`: `征信花了`
4. 点击“立即采集”，进入采集任务中心确认任务成功。
5. 进入帖子池、评论池、线索池，展示 Mock 数据如何变成 A/B/C/D 线索。
6. 进入今日报告，点击“生成今日报告”。
7. 回到监控源管理，创建指定帖子链接监控源：
   - `source_type`: `manual_post`
   - `collector_type`: `playwright`
   - `value`: 一个公开可访问的 `http/https` 帖子链接
8. 点击“立即采集”。
9. 如果成功，进入帖子池查看原链接，进入评论池按帖子 ID 核验评论，再进入线索池查看是否识别出线索。
10. 如果失败，进入采集任务中心展示 `error_message`，说明系统会把真实采集失败记录为任务状态，不影响主服务。

## 讲解边界

本 Demo 不做登录、验证码、代理池、批量搜索或反爬绕过。真实采集 MVP 的价值是验证“公开链接 -> 帖子/评论 -> 线索识别 -> 报告/导出”这条链路。
