# 真实采集能力对齐验收（步骤 23.5）

本文用于验收前后端真实采集能力是否对齐，不新增大功能，只验证已实现能力。

## 0.1 Spider_XHS 关键词最小闭环（新增）

当前后端已支持 XHS provider 双通道驱动：

1. `pc`：使用内置 `XhsPcClient`。
2. `spider`：优先使用 Spider_XHS 适配器（需要额外依赖和路径配置）。
3. `auto`：优先 Spider_XHS，失败后回退 `pc`。

### 运行前环境变量

```powershell
$env:XHS_COOKIES = "你的登录cookie"
$env:XHS_PROVIDER_DRIVER = "spider"   # 可选: pc / spider / auto
$env:XHS_PROVIDER_FALLBACK_TO_PC = "true"  # spider 模式下失败时是否回退
$env:XHS_SPIDER_PATH = "D:\\path\\to\\Spider_XHS" # Spider_XHS 仓库根目录
```

说明：

1. `XHS_SPIDER_PATH` 未配置时，`spider` 模式会报错并提示路径。
2. 敏感信息（cookie/token/session）不会写入 error_message 明文。
3. 本阶段仅覆盖采集链路，不包含登录/发布能力。

## 1. 后端启动方式

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

健康检查：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

## 2. 前端启动方式

```powershell
cd frontend
npm install
npm run dev
```

默认访问：`http://127.0.0.1:5173`。

## 3. GET /api/collectors 验证方式

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/collectors -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/collectors/health -UseBasicParsing | Select-Object -ExpandProperty Content
```

应看到已注册采集器能力，且包含 `mock / playwright / external_api / generic_web / xhs`。

## 4. 创建 mock keyword 监控源

```json
{
  "source_type": "keyword",
  "platform": "xhs",
  "name": "mock-keyword-demo",
  "value": "征信花了",
  "config": {
    "collector_type": "mock",
    "max_posts": 5,
    "max_comments_per_post": 10
  },
  "enabled": true
}
```

## 5. 创建 manual_post + playwright 监控源

```json
{
  "source_type": "manual_post",
  "platform": "xhs",
  "name": "manual-playwright-demo",
  "value": "https://www.xiaohongshu.com/explore",
  "config": {
    "collector_type": "playwright",
    "max_posts": 1,
    "max_comments_per_post": 10
  },
  "enabled": true
}
```

## 6. 创建 external_api 监控源配置示例

```json
{
  "source_type": "keyword",
  "platform": "xhs",
  "name": "external-api-demo",
  "value": "征信修复",
  "config": {
    "collector_type": "external_api",
    "external_api": {
      "endpoint": "https://your-api.example.com/collect",
      "api_key_env": "EXTERNAL_COLLECTOR_API_KEY"
    },
    "max_posts": 5,
    "max_comments_per_post": 10
  },
  "enabled": true
}
```

## 7. 创建 generic_web 监控源配置示例

```json
{
  "source_type": "manual_post",
  "platform": "other",
  "name": "generic-web-demo",
  "value": "https://example.com/post/1",
  "config": {
    "collector_type": "generic_web",
    "entry_url": "https://example.com/post/1",
    "selectors": {
      "post_container": "article, .post",
      "title": "h1, h2",
      "content": "article, .content",
      "author": ".author",
      "comment_item": ".comment"
    },
    "max_posts": 3,
    "max_comments_per_post": 10
  },
  "enabled": true
}
```

## 8. 创建 xhs 监控源配置示例

```json
{
  "source_type": "keyword",
  "platform": "xhs",
  "name": "xhs-keyword-demo",
  "value": "https://www.xiaohongshu.com/explore",
  "config": {
    "collector_type": "xhs",
    "entry_url": "https://www.xiaohongshu.com/explore",
    "cookies": "sessionid=xxx; userid=yyy",
    "max_posts": 3,
    "max_comments_per_post": 5,
    "selectors": {
      "note_container": "div[class*='feed-item']",
      "title": "h2, h3",
      "content": "p, .desc",
      "author": ".author",
      "comment_item": "div[class*='comment']"
    }
  },
  "enabled": true
}
```

安全要求：

- cookies 仅用于本地开发测试。
- 不打印 cookie / api key / token。
- 不提交敏感配置到 Git。
- 生产环境使用安全凭证管理。
- 不做验证码绕过、账号池、代理池、签名逆向。

## 9. 触发“立即采集”

前端监控源列表点击“立即采集”，或调用：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/monitor-sources/{id}/crawl -Method POST -UseBasicParsing | Select-Object -ExpandProperty Content
```

## 10. 查看采集任务

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/crawl-tasks -UseBasicParsing | Select-Object -ExpandProperty Content
```

确认任务状态、post_count、comment_count、lead_count、error_message。

## 11. 查看帖子池 / 评论池 / 线索池

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/posts -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/comments -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/leads -UseBasicParsing | Select-Object -ExpandProperty Content
```

## 12. 常见失败原因

- `manual_post + playwright` 传入非 http/https 链接。
- `external_api` 缺少 `endpoint`，或 `api_key_env` 对应环境变量未设置。
- `generic_web` 缺少 `entry_url` 且 `value` 为空，或 selector 不匹配页面结构。
- `xhs` 缺少 cookies、cookies 失效或页面结构变更。
- 本地缺少 Playwright 浏览器依赖：

```powershell
python -m playwright install chromium
```

- 目标网页不可访问、网络超时或触发平台风控。
