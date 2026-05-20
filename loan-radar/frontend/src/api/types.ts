export type MonitorSource = {
  id: number;
  source_type: string;
  platform: string;
  name: string;
  value: string;
  config: unknown;
  enabled: boolean;
  schedule_enabled: boolean;
  schedule_cron: string | null;
  last_scheduled_at: string | null;
  last_crawled_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MonitorSourceCreatePayload = {
  source_type: string;
  platform: string;
  name: string;
  value: string;
  config?: unknown;
  enabled?: boolean;
  schedule_enabled?: boolean;
  schedule_cron?: string | null;
  last_crawled_at?: string | null;
};

export type CollectorCapability = {
  name: string;
  description: string;
  status: string;
  supports: string[];
  config?: unknown;
};

export type CollectorCapabilitiesResponse = {
  collectors: Record<string, CollectorCapability>;
  summary?: {
    ready?: string[];
    implementing?: string[];
    planned?: string[];
  };
};

export type CrawlTask = {
  id: number;
  source_id: number | null;
  source_type: string;
  source_value?: string | null;
  platform: string;
  status: string;
  progress: string | null;
  limit_count?: number;
  retry_count?: number;
  max_retries?: number;
  last_error_type?: string | null;
  failure_type?: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  post_count: number;
  comment_count: number;
  collected_posts?: number;
  collected_comments?: number;
  lead_count: number;
  discovered_competitor_count: number;
  duplicate_post_count: number;
  duplicate_comment_count: number;
  queue_position?: number;
  created_at: string;
  updated_at: string;
};

export type CollectionTaskCreatePayload = {
  platform: string;
  source_type: "keyword" | "account" | "post_url";
  source_value: string;
  limit_count: number;
};

export type CrawlTaskListResponse = {
  items: CrawlTask[];
  total: number;
  page: number;
  page_size: number;
};

export type FailureTypeMeta = {
  value: string;
  label: string;
  description: string;
  suggestion: string;
};

export type FailureTypesMetaResponse = Record<string, FailureTypeMeta>;

export type Lead = {
  id: number;
  platform: string;
  source_id: number;
  source_type: string;
  source_post_id: number | null;
  source_comment_id: number | null;
  source_post_title: string | null;
  source_post_url: string | null;
  user_name: string | null;
  user_profile_url: string | null;
  content: string | null;
  lead_level: string;
  lead_score: number;
  demand_type: string | null;
  risk_level: string | null;
  evidence: unknown;
  reason: string | null;
  follow_up_script: string | null;
  status: string;
  notes: string | null;
  crm_customer_id: number | null;
  crm_opportunity_id: number | null;
  converted_to_crm_at: string | null;
  is_duplicate: boolean;
  duplicate_group_id: string | null;
  duplicate_reason: string | null;
  comment_publish_time: string | null;
  created_at: string;
  updated_at: string;
};

export type LeadListResponse = {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
};

export type LeadQueryParams = {
  lead_level?: string;
  demand_type?: string;
  risk_level?: string;
  platform?: string;
  status?: string;
  source_type?: string;
  keyword?: string;
  source_post_id?: number;
  source_comment_id?: number;
  is_duplicate?: boolean | string;
  converted_to_crm?: boolean | string;
  created_after?: string;
  page?: number;
  page_size?: number;
};

export type LeadStatusUpdatePayload = {
  status: string;
  notes?: string | null;
};

export type LeadConvertToCrmPayload = {
  owner_name?: string | null;
  next_follow_up_at?: string | null;
};

export type LeadConvertToCrmResult = {
  customer: CrmCustomer;
};

export type Post = {
  id: number;
  platform: string;
  source_id: number;
  source_type: string;
  post_id: string;
  title: string | null;
  content: string | null;
  post_url: string | null;
  author_name: string | null;
  author_profile_url: string | null;
  like_count: number;
  comment_count: number;
  collect_count: number;
  publish_time: string | null;
  is_hot: boolean;
  lead_count: number;
  raw_data: unknown;
  created_at: string;
  updated_at: string;
};

export type PostListResponse = {
  items: Post[];
  total: number;
  page: number;
  page_size: number;
};

export type PostQueryParams = {
  platform?: string;
  source_type?: string;
  source_id?: number;
  is_hot?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
};

export type Comment = {
  id: number;
  platform: string;
  post_id: string;
  comment_id: string;
  user_name: string | null;
  user_profile_url: string | null;
  content: string | null;
  like_count: number;
  publish_time: string | null;
  is_suspected_demand: boolean;
  demand_type: string | null;
  risk_level: string | null;
  has_lead: boolean;
  raw_data: unknown;
  created_at: string;
  updated_at: string;
};

export type CommentListResponse = {
  items: Comment[];
  total: number;
  page: number;
  page_size: number;
};

export type CommentQueryParams = {
  platform?: string;
  demand_type?: string;
  risk_level?: string;
  is_suspected_demand?: boolean;
  post_id?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
};

export type CrmCustomer = {
  id: number;
  source_type: string;
  lead_id: number | null;
  platform: string | null;
  source_channel: string | null;
  source_url: string | null;
  source_post_id: number | null;
  customer_name: string | null;
  nickname: string | null;
  phone: string | null;
  wechat: string | null;
  city: string | null;
  demand_type: string | null;
  demand_description: string | null;
  intended_amount: number | null;
  lead_level: string | null;
  status: string;
  owner_name: string | null;
  entered_by: string | null;
  notes: string | null;
  next_follow_up_at: string | null;
  last_follow_up_at: string | null;
  converted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmCustomerManualCreate = {
  customer_name?: string | null;
  nickname?: string | null;
  phone?: string | null;
  wechat?: string | null;
  source_channel?: string | null;
  demand_type?: string | null;
  demand_description?: string | null;
  intended_amount?: number | null;
  city?: string | null;
  lead_level?: string | null;
  owner_name?: string | null;
  entered_by?: string | null;
  notes?: string | null;
  next_follow_up_at?: string | null;
};

export type CrmFollowRecord = {
  id: number;
  customer_id: number;
  follow_type: string;
  content: string;
  next_follow_up_at: string | null;
  created_at: string;
};

export type CrmListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type CrmDashboard = {
  total_customers: number;
  lead_conversion_count: number;
  manual_count: number;
  today_new: number;
  today_manual: number;
  pending_follow: number;
  interested: number;
  converted: number;
  overdue_follow: number;
  today_follow_up_count: number;
  tomorrow_follow_up_count: number;
  this_week_follow_up_count: number;
  status_counts: Record<string, number>;
  level_counts: Record<string, number>;
};

export type PendingCompetitor = {
  id: number;
  platform: string;
  account_name: string;
  profile_url: string;
  source_keyword: string | null;
  source_post_id: number | null;
  discover_reason: string | null;
  competitor_score: number;
  content_relevance_score: number;
  interaction_score: number;
  lead_potential_score: number;
  risk_score: number;
  recent_post_count: number;
  recent_comment_count: number;
  suspected_lead_count: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type PendingCompetitorQueryParams = {
  platform?: string;
  status?: string;
  min_score?: number;
};

export type ApprovePendingCompetitorResponse = {
  pending_competitor: PendingCompetitor;
  monitor_source: MonitorSource;
};

export type DailyReport = {
  id: number;
  report_date: string;
  platform: string;
  source_count: number;
  post_count: number;
  comment_count: number;
  lead_count: number;
  a_lead_count: number;
  b_lead_count: number;
  c_lead_count: number;
  d_lead_count: number;
  top_demands: unknown;
  top_keywords: unknown;
  hot_posts: unknown;
  content_suggestions: unknown;
  follow_up_suggestions: unknown;
  risk_warnings: unknown;
  a_lead_details: unknown;
  typical_evidence: unknown;
  discovered_competitors: unknown;
  tomorrow_suggestions: unknown;
  crm_stats: {
    today_new_customers: number;
    today_follow_count: number;
    interested_count: number;
    converted_count: number;
    overdue_follow_remind: number;
  } | null;
  created_at: string;
  updated_at: string;
};

export type QueueStatus = {
  active_task_id: number | null;
  queue_size: number;
  queue_items: number[];
};

export type DashboardStats = {
  source_count: number;
  today_task_count: number;
  today_post_count: number;
  today_comment_count: number;
  today_lead_count: number;
  today_a_lead_count: number;
  total_task_count: number;
  total_post_count: number;
  total_comment_count: number;
  total_lead_count: number;
  total_a_lead_count: number;
  yesterday_lead_count: number;
  yesterday_a_lead_count: number;
  yesterday_post_count: number;
  pending_competitor_count: number;
  crm_today_new: number;
  crm_pending_follow: number;
  crm_overdue_follow: number;
  crm_converted: number;
  xhs_notes_count: number;
  xhs_notes_today: number;
  recent_a_leads: Array<{
    id: number;
    platform: string;
    user_name: string;
    content: string;
    lead_score: number;
    lead_level: string;
    demand_type: string;
    follow_up_script: string;
    created_at: string;
  }>;
  recent_tasks: Array<{
    id: number;
    source_type: string;
    source_value: string;
    platform: string;
    status: string;
    post_count: number;
    comment_count: number;
    lead_count: number;
    error_message: string;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
  }>;
};

export type MediaCrawlerHealth = {
  status: string;
  mode: string;
  api_base_url?: string;
  media_crawler_home?: string;
  shared_db: { available: boolean; path?: string };
  supported_platforms: Array<{ value: string; label: string }>;
};

export type SchedulerStatus = {
  running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run_time: string | null;
  }>;
};

export type ScoringDimension = {
  name: string;
  weight: number;
  patterns: string[];
  score_per_hit: number;
  max_score: number;
  description: string;
};

export type ScoringRules = {
  version: string;
  dimensions: ScoringDimension[];
  negative_patterns: string[];
  negation_patterns: string[];
  lead_level_thresholds: Record<string, number>;
  demand_type_rules: Array<{ keywords: string[]; type: string }>;
  risk_keywords: string[];
  amount_pattern: string;
};

export type ScoringTestResult = {
  lead_level: string;
  lead_score: number;
  demand_type: string;
  risk_level: string;
  evidence: Record<string, unknown>;
  reason: string;
  follow_up_script: string;
  is_suspected_demand: boolean;
};

export type DemoGenerateResult = {
  message: string;
  demo_sources: Array<{
    id: number;
    name: string;
    source_type: string;
    platform: string;
  }>;
  crawl_tasks: Array<{
    task_id: number;
    source_id: number;
    queue_position: number;
  }>;
  tip: string;
};

export type CookiePlatformStatus = {
  platform: string;
  total_accounts: number;
  active_accounts: number;
  expired_accounts: number;
  cookies_available: boolean;
  crawl_ready: boolean;
};

export type CookieStatusResponse = {
  platforms: CookiePlatformStatus[];
};
