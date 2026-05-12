# 线索雷达开发任务清单

## P0 已完成主链路

- [x] 项目骨架和基础文档
- [x] 数据库模型和 Alembic 迁移
- [x] Pydantic Schemas
- [x] 监控源 CRUD
- [x] MockCollector
- [x] 线索识别规则引擎
- [x] 触发采集完整链路
- [x] 线索查询和 CSV 导出
- [x] 今日报告生成
- [x] 同行账号发现池后端和前端页面
- [x] 前端基础页面：监控源、采集任务、帖子池、评论池、线索池、今日报告

## P1 当前任务：manual_post 真实公开链接采集 MVP

- [x] 将 Playwright 采集限制为 `manual_post`
- [x] 拆分通用页面解析器边界
- [x] 允许真实页面无评论时成功入库帖子
- [x] 创建监控源时校验 `manual_post + playwright` URL
- [x] 拒绝 `keyword + playwright`
- [x] 前端监控源页支持真实指定链接采集提示和默认配置
- [x] 帖子池展示原链接
- [x] 评论池支持按帖子 ID 核验
- [ ] 补充真实采集 smoke test 文档和演示流程

## P2 下一步：真实采集稳定性

- [ ] 采集结果去重：posts 按 `platform + post_id`
- [ ] 评论去重：comments 按 `platform + comment_id`
- [ ] 已存在评论不重复生成 lead
- [ ] 采集成功后更新 `monitor_sources.last_crawled_at`
- [ ] 错误信息脱敏
- [ ] 增加真实采集测试页面或本地 HTML fixture

## P3 后续：External API 接入

- [ ] 定义外部采集 API 标准协议
- [ ] 实现 ExternalApiCollector
- [ ] 支持 `endpoint`、`api_key_env`、`timeout`、`retry`
- [ ] 前端支持 external_api 配置
- [ ] 测试 API Key 不泄漏

## 暂缓

- [ ] CRM
- [ ] 员工管理
- [ ] 复杂权限
- [ ] 自动发布
- [ ] 登录态采集
- [ ] 验证码处理
- [ ] 代理池 / Cookie 池
- [ ] 真实平台关键词批量搜索
- [ ] 复杂智能体编排
