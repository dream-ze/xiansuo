# DB Design

## 一、文档作用

记录线索雷达 MVP 的核心数据库模型、字段含义和接口范围。本文档以 `backend/app/models/` 实际代码为准。

## 数据库连接

- 本地开发：`postgresql+psycopg2://loan_radar:loan_radar_password@localhost:5432/loan_radar`
- Docker 部署：`postgresql+psycopg2://loan_radar:loan_radar_password@postgres:5432/loan_radar`
- 启动 PostgreSQL：`docker compose up postgres -d`
- 运行迁移：`cd backend && alembic upgrade head`

## 二、数据库模型

模型总览（9 个表）：

| # | 表名 | 代码文件 | 说明 |
|---|------|----------|------|
| 1 | monitor_sources | `monitor_source.py` | 监控源配置 |
| 2 | pending_competitor_accounts | `pending_competitor.py` | 待审核同行账号 |
| 3 | crawl_tasks | `crawl_task.py` | 采集任务 |
| 4 | posts | `post.py` | 帖子池 |
| 5 | comments | `comment.py` | 评论池 |
| 6 | leads | `lead.py` | 线索池 |
| 7 | daily_reports | `daily_report.py` | 今日获客报告 |
| 8 | crm_customers | `crm.py` | CRM 客户 |
| 9 | crm_follow_records | `crm.py` | CRM 跟进记录 |

Alembic 迁移版本（12 个）：`ae22605e776e` → `l9m0n1o2p3q4`

### 1. monitor_sources

字段：

- id
- source_type：keyword / competitor_account / manual_post / hot_post_rule
- platform：xhs / douyin / zhihu

  > 当前 MVP 仅支持以上 3 个平台，传入其他平台将返回 400。后续版本将逐步开放 kuaishou / bilibili / weibo / tieba。
- name
- value
- config JSON（包含以下字段）：
  - `collector_type`：`media_crawler` / `mock`
  - `mode`：`test` / `real`
  - `login_type`：`qrcode` / `cookie` / `phone`
  - `enable_comments`：bool
  - `max_posts`：int，默认 10（1-1000）
  - `max_comments_per_post`：int，默认 50（1-100）
  - `timeout_seconds`：int，默认 30（5-300）
  - `retry_times`：int，默认 3（1-10）
  - `rate_limit_seconds`：int，默认 1（0-60）
  - `cookies`：string，可选
  - `user_agent`：string，可选
  - `time_range`：`7d` / `15d` / `30d` / `90d`，为空则不限制
- enabled
- schedule_enabled：bool，是否启用定时采集
- schedule_cron：Cron 表达式，如 `0 */2 * * *`
- last_scheduled_at：上次定时触发时间
- last_crawled_at
- created_at
- updated_at

说明：

- keyword：value 存关键词
- competitor_account：value 存账号主页链接
- manual_post：value 存帖子链接
- hot_post_rule：value 存规则名称，config 存筛选条件
- `time_range` 设置后，采集时 `max_posts` 自动提升至 80（`TIME_RANGE_BOOSTED_MAX_POSTS`），入库前按 `publish_time` 过滤

### 2. pending_competitor_accounts

字段：

- id
- platform
- account_name
- profile_url
- source_keyword
- source_post_id
- discover_reason
- competitor_score
- content_relevance_score
- interaction_score
- lead_potential_score
- risk_score
- recent_post_count
- recent_comment_count
- suspected_lead_count
- status：pending / approved / ignored
- created_at
- updated_at

### 3. crawl_tasks

字段：

- id
- source_id
- source_type
- source_value：采集来源值（关键词、帖子链接等）
- platform
- status：pending / running / success / failed
- progress：当前进度描述（queued / collecting / saving_posts / scoring_leads）
- limit_count：采集数量限制，默认 20
- retry_count：已重试次数
- max_retries：最大重试次数，默认 3
- last_error_type：最近一次错误分类（retry_service 的 ErrorCategory）
- failure_type：失败类型分类（failure_classifier 的 FailureType），可选值：media_crawler_unreachable / platform_not_supported / auth_required / captcha_or_risk_control / timeout / empty_result / parser_error / unknown
- started_at
- finished_at
- error_message：脱敏后的错误信息
- post_count
- comment_count
- collected_posts：实际采集到的帖子数
- collected_comments：实际采集到的评论数
- lead_count
- discovered_competitor_count
- duplicate_post_count
- duplicate_comment_count
- created_at
- updated_at

### 4. posts

字段：

- id
- platform
- source_id
- source_type
- post_id：平台原始帖子 ID
- content_hash：内容 MD5 哈希，用于去重
- title
- content
- post_url
- author_name
- author_profile_url
- like_count
- comment_count
- collect_count
- publish_time
- is_hot
- raw_data JSON
- created_at
- updated_at

唯一约束：`(platform, post_id)`

### 5. comments

字段：

- id
- platform
- post_id：平台原始帖子 ID
- comment_id：平台原始评论 ID
- content_hash：内容 MD5 哈希，用于去重
- user_name
- user_profile_url
- content
- like_count
- publish_time
- is_suspected_demand
- demand_type
- risk_level
- raw_data JSON
- created_at
- updated_at

唯一约束：`(platform, comment_id)`

### 6. leads

字段：

- id
- platform
- source_id
- source_type
- source_post_id：关联帖子 ID（Integer，指向 posts.id）
- source_comment_id
- user_name
- user_profile_url
- content_hash：评论内容 MD5 哈希，用于相同内容去重
- content
- lead_level：A / B / C / D
- lead_score
- demand_type
- risk_level
- evidence JSON
- reason
- follow_up_script
- status：new / contacted / interested / invalid / converted
- notes：备注
- crm_customer_id：关联 CRM 客户 ID（线索转客户后自动填充）
- crm_opportunity_id：关联 CRM 商机 ID（预留字段）
- converted_to_crm_at：线索转客户时间
- is_duplicate：bool，是否为疑似重复线索
- duplicate_group_id：重复组 ID（`dup-` 前缀的 12 位随机字符串）
- duplicate_reason：重复原因
- created_at
- updated_at

唯一约束：`(platform, source_comment_id)`

### 7. daily_reports

字段：

- id
- report_date
- platform
- source_count
- post_count
- comment_count
- lead_count
- a_lead_count
- b_lead_count
- c_lead_count
- d_lead_count
- top_demands JSON
- top_keywords JSON
- hot_posts JSON
- content_suggestions JSON
- follow_up_suggestions JSON
- risk_warnings JSON
- a_lead_details JSON：A级线索详情列表
- typical_evidence JSON：典型需求证据
- discovered_competitors JSON：发现的同行账号
- tomorrow_suggestions JSON：明日采集建议
- crm_stats JSON：CRM 统计数据
- created_at
- updated_at

### 8. crm_customers

字段：

- id
- source_type：`lead_conversion`（线索转化）/ `manual`（手动录入）/ `import`（导入）
- lead_id：关联线索 ID（线索转化时有值）
- platform
- source_channel：来源渠道（小红书/抖音/知乎/微信/电话/朋友介绍/线下/员工自拓/其他）
- source_url
- source_post_id：关联帖子 ID（Integer，指向 posts.id）
- customer_name
- nickname
- phone
- wechat
- city
- demand_type
- demand_description
- intended_amount：意向金额（Float）
- lead_level：A / B / C / D
- status：pending / contacted / interested / wechat_added / applied / converted / invalid
- owner_name：负责人
- entered_by：录入人
- notes
- next_follow_up_at：下次跟进时间（带时区）
- last_follow_up_at：最后跟进时间（带时区）
- converted_at：转化时间（带时区）
- created_at
- updated_at

### 9. crm_follow_records

字段：

- id
- customer_id：关联客户 ID
- follow_type：phone / wechat / message / visit / other
- content：跟进内容
- next_follow_up_at：下次跟进时间（带时区）
- created_at

## 三、后端接口要求

### 1. 监控源管理

- 创建监控源（含 time_range 配置、定时采集配置）
- 查询监控源列表
- 启用/停用监控源
- 删除监控源
- 手动触发某个监控源采集
- 定时采集调度管理（APScheduler，Cron 表达式）
- 调度器状态查询

### 2. 采集任务

- 创建采集任务
- 查询采集任务列表
- 查询采集任务详情
- 重新运行失败任务
- 采集任务队列管理（CrawlTaskQueue，同一时间仅执行一个任务）
- 队列状态查询

### 3. 帖子池

- 查询帖子列表
- 按平台筛选
- 按来源类型筛选
- 按是否爆款筛选

### 4. 评论池

- 查询评论列表
- 按平台筛选
- 按需求类型筛选
- 按是否疑似需求筛选

### 5. 线索池

- 查询线索列表
- 按 A/B/C/D 筛选
- 按需求类型筛选
- 按风险等级筛选
- 按平台筛选
- 按重复标记筛选
- 按是否已转 CRM 筛选
- 按创建时间筛选
- 导出 CSV
- 线索转 CRM 客户

### 6. 今日获客报告

- 生成今日报告
- 查询今日报告
- 导出今日报告（Markdown 格式）
- 查询历史报告

### 7. 同行账号发现

- 查询待审核同行账号
- 审核通过，加入 monitor_sources，source_type = competitor_account
- 忽略账号
- 查看发现原因和评分

### 8. 轻 CRM 跟进台

- CRM 仪表板（统计概览、跟进提醒：已逾期/今日/明日/本周）
- 客户列表（支持跟进提醒过滤：overdue/today/tomorrow/this_week/none）
- 手动创建客户
- 线索转客户（两种入口：CRM 页面 / 线索页面）
- 更新客户信息
- 添加跟进记录
- 查看跟进记录列表

### 9. 仪表板

- 全局统计概览（今日/昨日/累计数据对比）
- CRM 跟进提醒统计
- MediaCrawler 健康状态（HTTP Bridge / 内嵌模式）
- 最近 A 级线索和采集任务

### 10. 评分规则

- 获取评分规则
- 更新评分规则
- 测试评分效果（单条/批量）
- 重载评分规则
