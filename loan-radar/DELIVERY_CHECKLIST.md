# 交付检查清单

## 交付前必检项

### 1. 环境准备

- [ ] Docker 和 Docker Compose 已安装
- [ ] `docker compose config` 通过
- [ ] PostgreSQL 可连接
- [ ] 后端 `alembic upgrade head` 成功
- [ ] 后端 `/health` 返回 `{"status": "ok"}`

### 2. 前端构建

- [ ] `npm install` 无错误
- [ ] `npm run build` 通过
- [ ] Nginx 配置正确代理 `/api` 到后端
- [ ] 生产环境 `VITE_API_BASE_URL` 为空（同域代理）

### 3. 后端编译

- [ ] `python -m compileall app` 通过
- [ ] 所有 API 路由正常注册
- [ ] CORS 配置正确

### 4. 核心功能链路

- [ ] 注册/登录可用
- [ ] 添加关键词 → 创建采集任务
- [ ] 采集任务入队 → 状态可轮询
- [ ] 采集完成/失败 → 帖子池/评论池可查看
- [ ] 线索识别 → 线索池有评分、证据链、跟进话术
- [ ] A 级线索可转 CRM
- [ ] 每日获客报告可生成
- [ ] 帖子池可收藏到内容库
- [ ] 内容库可生成小红书草稿
- [ ] 草稿可发送到发布中心
- [ ] 自动运营任务执行后生成真实草稿
- [ ] 监控刷新创建真实采集任务

### 5. 核心 API 可用

- [ ] `GET /api/collection/tasks`
- [ ] `GET /api/leads`
- [ ] `GET /api/posts`
- [ ] `GET /api/daily-reports/today`
- [ ] `GET /api/xhs/analytics/overview`
- [ ] `GET /api/xhs/auto-ops/tasks`
- [ ] `GET /api/xhs/monitoring/targets`

### 6. 错误处理

- [ ] API 失败返回可读中文错误
- [ ] 前端展示错误原因和处理建议
- [ ] 采集失败不导致系统崩溃
- [ ] AI 生成失败有模板回退

### 7. 安全

- [ ] 生产环境 `SECRET_KEY` 已设置
- [ ] `API_BASE_URL` 不硬编码 localhost
- [ ] Cookie 加密存储
- [ ] 不做风控绕过/验证码绕过/指纹伪装

### 8. 文档

- [ ] README.md 包含一键启动、首次启动、端口、环境变量
- [ ] 小红书账号配置说明
- [ ] 演示数据生成说明
- [ ] 完整演示流程
- [ ] 常见问题排查
- [ ] 声明"自动生成 + 人工确认发布"

## 验收命令

```powershell
# 完整验收
check-delivery.bat

# Python 验收脚本
python scripts/delivery_check.py
```

## 交付结论标准

- 所有 P0 阻塞项已修复
- 主链路可走通（从配置到线索到 CRM）
- 小红书运营与线索雷达一体化
- 自动运营任务生成真实草稿
- 监控刷新创建真实采集任务
- check-delivery 脚本通过
- 无硬编码 localhost（生产环境）
