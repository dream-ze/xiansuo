# DB Design

## 一、文档作用

记录线索雷达 Demo 可成交版的核心数据库模型、字段含义和后续接口范围。

当前文档是设计依据，不代表所有模型、迁移和接口已经实现。具体实现必须按 `CODEX_TASK_RULES.md` 分步骤推进。

## 二、数据库模型

### 1. monitor_sources

字段：

- id
- source_type：keyword / competitor_account / manual_post / hot_post_rule
- platform：xhs / douyin / zhihu / kuaishou / bilibili / weibo / tieba / other

  > 注意：monitor_source_service 校验接受以上 8 个平台，但 MediaCrawler 当前仅支持 xhs / douyin / zhihu 三个平台的采集。创建 kuaishou / bilibili / weibo / tieba / other 平台的监控源会成功，但触发采集时会因 MediaCrawler 不支持而失败。
- name
- value
- config JSON
- enabled
- last_crawled_at
- created_at
- updated_at

说明：

- keyword：value 存关键词
- competitor_account：value 存账号主页链接
- manual_post：value 存帖子链接
- hot_post_rule：value 存规则名称，config 存筛选条件

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
- limit_count：采集数量限制，默认 20
- started_at
- finished_at
- error_message
- post_count
- comment_count
- collected_posts：实际采集到的帖子数
- collected_comments：实际采集到的评论数
- lead_count
- discovered_competitor_count
- created_at
- updated_at

### 4. posts

字段：

- id
- platform
- source_id
- source_type
- post_id
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

### 5. comments

字段：

- id
- platform
- post_id
- comment_id
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

### 6. leads

字段：

- id
- platform
- source_id
- source_type
- source_post_id
- source_comment_id
- user_name
- content
- lead_level：A / B / C / D
- lead_score
- demand_type
- risk_level
- evidence JSON
- reason
- follow_up_script
- status：new / contacted / invalid / converted
- created_at
- updated_at

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
- created_at
- updated_at

## 三、后端接口要求

### 1. 监控源管理

- 创建监控源
- 查询监控源列表
- 启用/停用监控源
- 删除监控源
- 手动触发某个监控源采集

### 2. 采集任务

- 创建采集任务
- 查询采集任务列表
- 查询采集任务详情
- 重新运行失败任务

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
- 导出 CSV/Excel

### 6. 今日获客报告

- 生成今日报告
- 查询今日报告
- 查询历史报告

### 7. 同行账号发现

- 查询待审核同行账号
- 审核通过，加入 monitor_sources，source_type = competitor_account
- 忽略账号
- 查看发现原因和评分
