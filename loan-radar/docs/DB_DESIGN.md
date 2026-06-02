# DB Design

## 一、文档作用

记录智获客的数据库模型、字段含义和接口范围。本文档以 `backend/app/models/` 实际代码为准。

## 数据库连接

- 本地开发：`postgresql+psycopg2://loan_radar:loan_radar_password@localhost:5432/loan_radar`
- Docker 部署：`postgresql+psycopg2://loan_radar:loan_radar_password@postgres:5432/loan_radar`
- 启动 PostgreSQL：`docker compose up postgres -d`
- 运行迁移：`cd backend && alembic upgrade head`

## 二、数据库模型

模型总览（22 个表）：

| # | 表名 | 代码文件 | 说明 | 模块 |
|---|------|----------|------|------|
| 1 | users | `user.py` | 用户账号 | 通用 |
| 2 | platform_accounts | `platform_account.py` | 平台账号（小红书 PC/创作者端） | 小红书运营 |
| 3 | account_cookie_versions | `platform_account.py` | 账号 Cookie 版本（加密存储） | 小红书运营 |
| 4 | login_sessions | `login_session.py` | 登录会话（QR/手机登录中间态） | 小红书运营 |
| 5 | monitor_sources | `monitor_source.py` | 监控源配置 | 线索雷达 |
| 6 | monitoring_snapshots | `monitoring_snapshot.py` | 监控目标快照 | 小红书运营 |
| 7 | pending_competitor_accounts | `pending_competitor.py` | 待审核同行账号 | 线索雷达 |
| 8 | crawl_tasks | `crawl_task.py` | 采集任务 | 线索雷达 |
| 9 | posts | `post.py` | 帖子池 | 线索雷达 |
| 10 | post_assets | `post_asset.py` | 帖子素材（图片/视频） | 线索雷达 |
| 11 | comments | `comment.py` | 评论池 | 线索雷达 |
| 12 | leads | `lead.py` | 线索池 | 线索雷达 |
| 13 | daily_reports | `daily_report.py` | 今日获客报告 | 线索雷达 |
| 14 | crm_customers | `crm.py` | CRM 客户 | 线索雷达 |
| 15 | crm_follow_records | `crm.py` | CRM 跟进记录 | 线索雷达 |
| 16 | notes | `note.py` | 小红书笔记 | 小红书运营 |
| 17 | note_assets | `note.py` | 笔记素材（图片/视频） | 小红书运营 |
| 18 | note_comments | `note.py` | 笔记评论 | 小红书运营 |
| 19 | tags | `post_tag.py` | 标签 | 小红书运营 |
| 20 | note_tags | `post_tag.py` | 笔记-标签关联（多对多） | 小红书运营 |
| 21 | keyword_groups | `keyword_group.py` | 关键词组 | 小红书运营 |
| 22 | ai_drafts | `ai.py` | AI 草稿 | 小红书运营 |
| 23 | draft_assets | `ai.py` | 草稿素材 | 小红书运营 |
| 24 | ai_generated_assets | `ai.py` | AI 生成素材 | 小红书运营 |
| 25 | model_configs | `ai.py` | AI 模型配置 | 小红书运营 |
| 26 | publish_jobs | `publish.py` | 发布任务 | 小红书运营 |
| 27 | publish_assets | `publish.py` | 发布素材 | 小红书运营 |
| 28 | auto_tasks | `auto_task.py` | 自动运营任务 | 小红书运营 |
| 29 | tasks | `task.py` | 统一任务 | 通用 |
| 30 | notifications | `notification.py` | 站内通知 | 通用 |
| 31 | api_logs | `api_log.py` | API 调用日志 | 通用 |
| 32 | compliance_rules | `compliance.py` | 合规规则 | 智能工作流 |
| 33 | knowledge_entries | `knowledge.py` | 知识库条目 | 智能工作流 |
| 34 | workflow_runs | `workflow.py` | 工作流运行记录 | 智能工作流 |
| 35 | workflow_logs | `workflow.py` | 工作流节点日志 | 智能工作流 |
| 36 | approval_queue | `approval.py` | 审批队列 | 智能工作流 |
| 37 | agent_conversations | `agent.py` | 智能体对话记录 | 智能体 |

Alembic 迁移版本（18 个）：`ae22605e776e` → `q2r3s4t5u6v7_add_agent_conversations_table`

---

### 1. users

字段：

- id：主键
- username：用户名（唯一索引）
- password_hash：密码哈希（PBKDF2_SHA256，260000 次迭代）
- created_at：创建时间

说明：用户认证系统，JWT Token 签发基于 `user.id`。

---

### 2. platform_accounts

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- platform：平台标识（如 `xhs`，索引）
- sub_type：子类型（`pc` / `creator`，可为空）
- external_user_id：平台外部用户 ID（可为空）
- nickname：昵称
- avatar_url：头像 URL
- status：账号状态（`valid` / `expired` / `unknown` 等）
- status_message：状态消息
- profile_json：用户资料 JSON
- created_at：创建时间
- updated_at：更新时间

说明：小红书 PC 端和创作者端账号统一管理，通过 `sub_type` 区分。同一用户可绑定多个账号。

---

### 3. account_cookie_versions

字段：

- id：主键
- platform_account_id：关联平台账号 ID（外键 → platform_accounts.id，索引）
- encrypted_cookies：加密后的 Cookie 文本（Fernet 对称加密）
- created_at：创建时间

说明：Cookie 按版本管理，每次登录/导入创建新版本。解密使用 `SECRET_KEY` 派生的 Fernet 密钥。

---

### 4. login_sessions

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- platform：平台标识（索引）
- sub_type：子类型（`pc` / `creator`，可为空）
- status：会话状态（`pending` / `confirmed` / `expired`）
- login_method：登录方式（`qr` / `phone` / `cookie`）
- phone_mask：手机号掩码（可为空）
- qr_id：二维码 ID（可为空）
- code：验证码（可为空）
- qr_url：二维码 URL（可为空）
- encrypted_temp_cookies：加密的临时 Cookie（登录中间态，可为空）
- created_at：创建时间

说明：QR 码和手机登录的中间态数据，登录成功后 Cookie 转存至 `account_cookie_versions`。

---

### 5. monitor_sources

字段：

- id
- source_type：keyword / competitor_account / manual_post / hot_post_rule
- platform：xhs / douyin / zhihu
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

---

### 6. monitoring_snapshots

字段：

- id：主键
- target_id：关联监控源 ID（外键 → monitor_sources.id，索引）
- payload：快照数据 JSON（可为空）
- created_at：创建时间

说明：XHS 监控目标刷新时保存的快照数据，用于对比变化。

---

### 7. pending_competitor_accounts

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

---

### 8. crawl_tasks

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
- last_error_type：最近一次错误分类
- failure_type：失败类型分类，可选值：media_crawler_unreachable / platform_not_supported / auth_required / captcha_or_risk_control / timeout / empty_result / parser_error / unknown
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

---

### 9. posts

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

---

### 10. post_assets

字段：

- id：主键
- post_id：关联帖子 ID（外键 → posts.id，索引）
- asset_type：素材类型（`image` / `video`）
- url：素材 URL
- local_path：本地存储路径
- sort_order：排序序号

说明：帖子的图片/视频素材，采集时保存。

---

### 11. comments

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

---

### 12. leads

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

---

### 13. daily_reports

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

---

### 14. crm_customers

字段：

- id
- source_type：`lead_conversion` / `manual` / `import`
- lead_id：关联线索 ID（线索转化时有值）
- platform
- source_channel：来源渠道（小红书/抖音/知乎/微信/电话/朋友介绍/线下/员工自拓/其他）
- source_url
- source_post_id：关联帖子 ID
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

---

### 15. crm_follow_records

字段：

- id
- customer_id：关联客户 ID
- follow_type：phone / wechat / message / visit / other
- content：跟进内容
- next_follow_up_at：下次跟进时间（带时区）
- created_at

---

### 16. notes

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- platform_account_id：关联平台账号 ID（外键 → platform_accounts.id，索引）
- platform：平台标识（索引）
- note_id：小红书笔记 ID（索引）
- title：笔记标题
- content：笔记正文
- author_name：作者名称
- raw_json：原始数据 JSON（可为空）
- created_at：创建时间

说明：小红书笔记数据，通过平台账号采集后保存。`note_id` 为小红书平台的笔记唯一标识。

---

### 17. note_assets

字段：

- id：主键
- note_id：关联笔记 ID（外键 → notes.id，索引）
- asset_type：素材类型（`image` / `video`）
- url：素材 URL
- local_path：本地存储路径
- sort_order：排序序号

---

### 18. note_comments

字段：

- id：主键
- note_id：关联笔记 ID（外键 → notes.id，索引）
- comment_id：评论 ID（索引）
- user_name：评论者名称
- user_id：评论者平台 ID（可为空）
- content：评论内容
- like_count：点赞数
- parent_comment_id：父评论 ID（可为空，支持嵌套评论）
- created_at_remote：远程创建时间（可为空）
- raw_json：原始数据 JSON（可为空）

---

### 19. tags

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- name：标签名称
- color：标签颜色（默认 `#111111`）

说明：用户自定义标签，用于笔记分类管理。同一用户下标签名称唯一。

---

### 20. note_tags

字段：

- note_id：关联笔记 ID（外键 → notes.id，主键）
- tag_id：关联标签 ID（外键 → tags.id，主键）

说明：笔记-标签多对多关联表。

---

### 21. keyword_groups

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- name：关键词组名称
- keywords：关键词列表（Text，JSON 序列化存储）
- platform：平台标识（默认 `xhs`）
- created_at：创建时间
- updated_at：更新时间

说明：采集关键词分组管理，支持多平台（xhs/douyin/kuaishou/weibo/xianyu/taobao）。

---

### 22. ai_drafts

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- model_config_id：关联模型配置 ID（外键 → model_configs.id，可为空）
- platform：平台标识（默认 `xhs`，索引）
- title：草稿标题
- body：草稿正文
- content：草稿内容（备用字段）
- prompt：生成提示词
- tags：标签列表 JSON（可为空）
- source_note_id：来源笔记 ID（外键 → notes.id，可为空，AI 改写时关联原笔记）
- intent：意图（`publish` / 其他）
- status：状态（`draft` / `published` / 其他）
- created_at：创建时间
- updated_at：更新时间

---

### 23. draft_assets

字段：

- id：主键
- draft_id：关联草稿 ID（外键 → ai_drafts.id，索引）
- ai_draft_id：关联 AI 草稿 ID（外键 → ai_drafts.id，索引）
- asset_type：素材类型（`image` / `video`）
- url：素材 URL
- local_path：本地存储路径
- sort_order：排序序号

---

### 24. ai_generated_assets

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- model_config_id：关联模型配置 ID（外键 → model_configs.id，可为空）
- draft_id：关联草稿 ID（外键 → ai_drafts.id，可为空）
- asset_type：素材类型（`image` / `video`）
- prompt：生成提示词
- model_name：模型名称
- params：生成参数 JSON（可为空）
- url：素材 URL
- file_path：文件路径
- local_path：本地存储路径
- created_at：创建时间

---

### 25. model_configs

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- name：配置名称
- model_type：模型类型（`text` / `image`，索引）
- provider：模型提供商
- model_id：模型 ID
- model_name：模型名称
- api_key_encrypted：加密的 API Key（旧字段）
- encrypted_api_key：加密的 API Key（新字段）
- base_url：API 基础 URL
- is_default：是否为默认模型
- created_at：创建时间
- updated_at：更新时间

说明：AI 模型配置管理，API Key 使用 Fernet 加密存储。每个用户每种 `model_type` 只能有一个默认模型。默认文本模型为 `gpt-5.4`。

---

### 26. publish_jobs

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- platform_account_id：关联平台账号 ID（外键 → platform_accounts.id，索引，可为空）
- source_draft_id：关联草稿 ID（外键 → ai_drafts.id，可为空）
- platform：平台标识（索引，默认 `xhs`）
- title：发布标题
- body：发布正文
- publish_mode：发布模式（`immediate` / `scheduled`）
- publish_options：发布选项 JSON（话题、位置、隐私等）
- status：状态（`pending` / `uploading` / `publishing` / `published` / `failed`）
- scheduled_at：定时发布时间（可为空）
- external_note_id：平台返回的笔记 ID
- publish_error：发布错误信息
- published_at：发布成功时间（可为空）
- created_at：创建时间

---

### 27. publish_assets

字段：

- id：主键
- publish_job_id：关联发布任务 ID（外键 → publish_jobs.id，索引）
- asset_type：素材类型（`image` / `video`）
- file_path：文件路径
- upload_status：上传状态（`pending` / `uploaded` / `failed`）
- creator_media_id：创作者端素材 ID
- upload_error：上传错误信息
- creator_upload_info：创作者端上传信息 JSON

---

### 28. auto_tasks

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- name：任务名称
- task_type：任务类型（`auto_publish` 等）
- config：任务配置 JSON（包含 keywords、pc_account_id、creator_account_id、ai_instruction、schedule_type、schedule_time、schedule_days、schedule_interval_hours、total_published）
- status：状态（`active` / `paused` / 其他）
- last_run_at：上次运行时间（可为空）
- next_run_at：下次运行时间（可为空）
- created_at：创建时间
- updated_at：更新时间

---

### 29. tasks

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- platform：平台标识（索引）
- task_type：任务类型（如 `creator_publish`、`creator_publish_scheduler`、`monitoring_refresh` 等）
- status：状态（`pending` / `running` / `success` / `failed`）
- progress：进度百分比（0-100）
- payload：任务载荷 JSON（可为空）
- created_at：创建时间
- started_at：开始时间（可为空）
- finished_at：完成时间（可为空）
- error_type：错误类型（可为空）
- retry_count：重试次数
- max_retries：最大重试次数（默认 3）
- parent_task_id：父任务 ID（外键 → tasks.id，可为空，支持子任务）

说明：统一任务管理表，支持父子任务层级。`task_type` 区分不同业务场景的任务。

---

### 30. notifications

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- type：通知类型（默认 `info`）
- title：通知标题
- message：通知消息
- body：通知正文
- level：通知级别（`info` / `warning` / `error` / `success`）
- is_read：是否已读
- source_task_id：来源任务 ID（可为空）
- source_type：来源类型（如 `crawl_task`、`lead`、`task`、`account`、`account_expired`、`publish_job`，可为空）
- source_id：来源 ID（可为空）
- created_at：创建时间

---

### 31. api_logs

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，可为空，索引）
- platform_account_id：关联平台账号 ID（外键 → platform_accounts.id，可为空，索引）
- method：HTTP 方法
- path：请求路径
- request_body：请求体（可为空）
- status_code：HTTP 状态码（可为空）
- response_body：响应体（可为空）
- error_message：错误信息（可为空）
- duration_ms：耗时毫秒（可为空）
- created_at：创建时间

说明：关键 API 调用日志，用于审计和问题排查。

---

## 三、后端接口要求

### 1. 用户认证

- 用户注册（用户名 + 密码）
- 用户登录（返回 JWT access + refresh Token）
- Token 刷新
- 获取当前用户信息

### 2. 监控源管理

- 创建监控源（含 time_range 配置、定时采集配置）
- 查询监控源列表
- 启用/停用监控源
- 删除监控源
- 手动触发某个监控源采集
- 定时采集调度管理（APScheduler，Cron 表达式）
- 调度器状态查询

### 3. 采集任务

- 创建采集任务
- 查询采集任务列表
- 查询采集任务详情
- 重新运行失败任务
- 采集任务队列管理
- 队列状态查询

### 4. 帖子池

- 查询帖子列表
- 按平台筛选
- 按来源类型筛选
- 按是否爆款筛选

### 5. 评论池

- 查询评论列表
- 按平台筛选
- 按需求类型筛选
- 按是否疑似需求筛选

### 6. 线索池

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

### 7. 今日获客报告

- 生成今日报告
- 查询今日报告
- 导出今日报告（Markdown 格式）
- 查询历史报告

### 8. 同行账号发现

- 查询待审核同行账号
- 审核通过
- 忽略账号

### 9. 轻 CRM 跟进台

- CRM 仪表板
- 客户列表
- 手动创建客户
- 线索转客户
- 更新客户信息
- 添加跟进记录
- 查看跟进记录列表

### 10. 仪表板

- 全局统计概览
- CRM 跟进提醒统计
- MediaCrawler 健康状态

### 11. 评分规则

- 获取/更新/测试/批量测试/重载评分规则

### 12. 平台账号管理

- 查询账号列表
- Cookie 导入（PC/创作者端）
- QR 码登录
- 手机验证码登录
- 账号状态检查

### 13. 笔记管理

- 笔记列表
- 批量保存笔记
- 笔记详情
- 笔记评论
- 笔记素材
- 笔记标签关联
- 笔记导出

### 14. AI 内容创作

- 笔记改写
- 笔记生成
- 标题生成
- 标签生成
- 文本润色
- 封面图生成
- 图片生成
- 图片描述
- 视频描述

### 15. 草稿管理

- 草稿列表
- 创建草稿
- 更新草稿
- 发送至发布中心

### 16. 发布管理

- 发布任务列表
- 创建发布任务
- 更新发布任务
- 执行发布
- 发布素材管理

### 17. 视频工坊

- 视频列表
- 视频上传
- 截取封面帧
- AI 视频描述

### 18. 文件管理

- 文件上传
- 文件下载
- 图片合成
- 图片缩放裁剪

### 19. 标签管理

- 标签列表
- 创建/更新/删除标签
- 笔记标签关联

### 20. 关键词组

- 关键词组列表
- 创建/更新/删除关键词组

### 21. XHS 监控

- 监控目标列表
- 创建监控目标
- 刷新监控目标
- 删除监控目标

### 22. XHS 数据洞察

- 运营总览
- 热门内容
- 热门话题
- 评论分析
- 竞品对标

### 23. XHS 自动运营

- 自动任务列表
- 创建/更新/删除自动任务
- 执行自动任务

### 24. 通知

- 通知列表
- 未读计数
- 标记已读
- 全部标记已读

### 25. 任务中心

- 任务列表
- 任务详情（含子任务）
- 调度器状态

### 26. 模型配置

- 模型配置列表
- 创建/更新/删除模型配置
- 设置默认模型

---

### 32. compliance_rules

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- category：规则类别（`platform_rule` / `industry_regulation` / `internal_policy`，索引）
- rule_text：规则文本
- rule_description：规则描述（可为空）
- severity：严重程度（`low` / `medium` / `high` / `critical`，默认 `medium`）
- is_active：是否启用（bool，默认 True）
- created_at：创建时间
- updated_at：更新时间

说明：合规审核规则，用于工作流中的合规检查节点。`category` 区分平台规则、行业规范和内部策略三类。默认 9 条规则可通过 `/api/compliance-rules/seed-defaults` 初始化。

---

### 33. knowledge_entries

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- source_type：素材类型（`material` / `platform_rule` / `quality_script`，索引）
- source_id：来源 ID（可为空，关联笔记/帖子等原始数据 ID）
- content：知识内容文本
- embedding_id：向量嵌入 ID（可为空，索引，用于关联 ChromaDB 中的向量）
- entry_metadata：元数据 JSON（可为空，存储平台、作者等附加信息）
- created_at：创建时间
- updated_at：更新时间

说明：RAG 知识库条目，`source_type` 区分产品素材、平台规则和优质话术。向量数据存储在 ChromaDB（`./storage/chroma`），`embedding_id` 用于关联。每用户独立 Collection（`user_{id}_knowledge`）。

---

### 34. workflow_runs

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，可为空，索引）
- workflow_type：工作流类型（`lead_scoring` / `script_generation` / `content_publish` / `agent_react`，索引）
- workflow_id：工作流运行唯一 ID（String(128)，唯一索引）
- state：运行状态（`pending` / `running` / `paused` / `completed` / `failed` / `cancelled`，默认 `pending`，索引）
- input_data：输入数据 JSON（可为空）
- output_data：输出数据 JSON（可为空）
- current_node：当前执行节点（可为空）
- paused_at_node：暂停所在节点（可为空）
- error_node：出错节点（可为空）
- error_message：错误信息（Text，默认空）
- retry_count：重试次数（默认 0）
- parent_workflow_id：父工作流 ID（可为空，支持嵌套工作流）
- created_at：创建时间
- updated_at：更新时间
- completed_at：完成时间（可为空）

说明：工作流运行记录，支持 LangGraph 和自研 WorkflowEngine 两种引擎。`paused` 状态表示工作流因合规风险门控暂停，等待人工审批后通过 `/api/workflows/runs/{workflow_id}/resume` 恢复。

---

### 35. workflow_logs

字段：

- id：主键
- workflow_id：关联工作流运行 ID（String(128)，索引）
- node_name：节点名称（如 `rule_prescreen`、`ai_lead_identify`、`compliance_check` 等）
- event_type：事件类型（`completed` / `failed` / `skipped`）
- input_snapshot：输入快照 JSON（可为空）
- output_snapshot：输出快照 JSON（可为空）
- error_message：错误信息（可为空）
- duration_ms：执行耗时毫秒（可为空）
- llm_tokens_used：LLM Token 消耗（可为空）
- llm_cost_estimate：LLM 费用估算（Numeric(10,6)，可为空）
- created_at：创建时间

说明：工作流节点执行日志，记录每个节点的输入输出和性能指标。`duration_ms` 和 `llm_tokens_used` 用于成本监控和性能优化。

---

### 36. approval_queue

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- workflow_id：关联工作流运行 ID（String(128)，可为空，索引）
- workflow_type：工作流类型（可为空）
- content_type：内容类型（`follow_up_script` / `draft`）
- content_id：关联内容 ID（可为空，如线索 ID 或草稿 ID）
- content_snapshot：内容快照 JSON（默认空对象）
- risk_level：风险等级（`low` / `medium` / `high` / `critical`，默认 `medium`，索引）
- compliance_result：合规检查结果 JSON（可为空）
- status：审批状态（`pending` / `approved` / `rejected`，默认 `pending`，索引）
- reviewer_id：审核人 ID（外键 → users.id，可为空）
- review_comment：审核意见（Text，可为空）
- reviewed_at：审核时间（可为空）
- created_at：创建时间

说明：审批队列，由工作流风险门控节点自动创建。当合规检查发现风险时，工作流暂停并创建审批记录，等待人工审核。审核通过后工作流继续执行。

---

### 37. agent_conversations

字段：

- id：主键
- user_id：关联用户 ID（外键 → users.id，索引）
- thread_id：对话线程 ID（String(128)，索引）
- role：消息角色（`user` / `assistant` / `tool`）
- content：消息内容（Text，默认空）
- tool_calls：工具调用信息 JSON（可为空，assistant 消息的工具调用记录）
- metadata_：元数据 JSON（可为空，存储迭代次数、工具名称等附加信息）
- created_at：创建时间

说明：ReAct 智能体对话记录，按 `thread_id` 分组管理多轮对话。`tool_calls` 记录 assistant 调用的工具列表，`metadata_` 存储工具执行结果等附加信息。对话上下文通过 `ConversationBufferMemory` 管理，支持从数据库加载历史消息。
