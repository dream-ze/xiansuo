const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
const defaultApiBaseUrl = "http://localhost:8001";
const rawApiBaseUrl = viteEnv?.VITE_API_BASE_URL || defaultApiBaseUrl;
export const API_BASE_URL = rawApiBaseUrl.replace(/\/$/, "");

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  message: string;
};

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
  created_at: string;
  updated_at: string;
};

export type CrmCustomer = {
  id: number;
  name: string;
  phone: string | null;
  contact_info: string | null;
  owner_name: string | null;
  source_lead_id: number | null;
  source_platform: string | null;
  source_type: string | null;
  source_post_id: number | null;
  source_comment_id: number | null;
  source_summary: string | null;
  demand_amount: number | null;
  loan_purpose: string | null;
  qualification_summary: string | null;
  risk_level: string | null;
  customer_level: string | null;
  status: string;
  evidence: unknown;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmOpportunity = {
  id: number;
  customer_id: number;
  source_lead_id: number | null;
  name: string;
  customer_name: string | null;
  owner_name: string | null;
  stage: string;
  estimated_amount: number | null;
  expected_close_date: string | null;
  probability: number;
  loss_reason: string | null;
  next_step: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmTask = {
  id: number;
  customer_id: number | null;
  opportunity_id: number | null;
  contract_id: number | null;
  customer_name: string | null;
  opportunity_name: string | null;
  title: string;
  task_type: string;
  owner_name: string | null;
  due_at: string | null;
  status: string;
  priority: string;
  suggestion: string | null;
  is_overdue: boolean;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmFollowUp = {
  id: number;
  customer_id: number;
  opportunity_id: number | null;
  contract_id: number | null;
  customer_name: string | null;
  opportunity_name: string | null;
  owner_name: string | null;
  follow_up_type: string;
  content: string;
  customer_feedback: string | null;
  next_action: string | null;
  next_follow_up_at: string | null;
  stage_before: string | null;
  stage_after: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmContract = {
  id: number;
  customer_id: number;
  opportunity_id: number | null;
  product_id: number | null;
  customer_name: string | null;
  contract_no: string | null;
  title: string;
  owner_name: string | null;
  amount: number;
  signed_at: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmReceivablePlan = {
  id: number;
  customer_id: number;
  contract_id: number;
  customer_name: string | null;
  contract_title: string | null;
  owner_name: string | null;
  amount: number;
  due_date: string;
  status: string;
  received_amount: number;
  notes: string | null;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
};

export type CrmListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type CrmDashboard = {
  total_leads: number;
  converted_leads: number;
  conversion_rate: number;
  customer_count: number;
  opportunity_count: number;
  won_count: number;
  lost_count: number;
  win_rate: number;
  pending_task_count: number;
  overdue_task_count: number;
  upcoming_receivable_count: number;
  overdue_receivable_count: number;
  stage_counts: Record<string, number>;
  source_counts: Record<string, number>;
};

export type LeadConvertToCrmPayload = {
  owner_name?: string | null;
  next_follow_up_at?: string | null;
};

export type LeadConvertToCrmResult = {
  customer: CrmCustomer;
  opportunity: CrmOpportunity;
  task: CrmTask;
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
  page?: number;
  page_size?: number;
};

export type CrmCustomerPayload = {
  name: string;
  phone?: string | null;
  contact_info?: string | null;
  owner_name?: string | null;
  demand_amount?: number | null;
  loan_purpose?: string | null;
  qualification_summary?: string | null;
  risk_level?: string | null;
  customer_level?: string | null;
  status?: string;
  notes?: string | null;
};

export type CrmFollowUpPayload = {
  customer_id: number;
  opportunity_id?: number | null;
  contract_id?: number | null;
  owner_name?: string | null;
  follow_up_type?: string;
  content: string;
  customer_feedback?: string | null;
  next_action?: string | null;
  next_follow_up_at?: string | null;
  stage_before?: string | null;
  stage_after?: string | null;
};

export type CrmTaskPayload = {
  customer_id?: number | null;
  opportunity_id?: number | null;
  contract_id?: number | null;
  title: string;
  task_type?: string;
  owner_name?: string | null;
  due_at?: string | null;
  status?: string;
  priority?: string;
  suggestion?: string | null;
};

export type LeadStatusUpdatePayload = {
  status: string;
  notes?: string | null;
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
  created_at: string;
  updated_at: string;
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  let payload: ApiResponse<T> | null = null;
  try {
    payload = (await response.json()) as ApiResponse<T>;
  } catch {
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status} ${response.statusText}`);
    }
    throw new Error("响应格式错误，无法解析 JSON");
  }

  if (!response.ok || !payload.success) {
    throw new Error(payload.message || `请求失败: ${response.status} ${response.statusText}`);
  }

  return payload.data;
}

export function getMonitorSources() {
  return requestJson<MonitorSource[]>("/api/monitor-sources");
}

export function createMonitorSource(payload: MonitorSourceCreatePayload) {
  return requestJson<MonitorSource>("/api/monitor-sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function toggleMonitorSource(id: number, enabled: boolean) {
  return requestJson<MonitorSource>(`/api/monitor-sources/${id}/toggle?enabled=${enabled}`, {
    method: "PATCH",
  });
}

export function deleteMonitorSource(id: number) {
  return requestJson<{ id: number }>(`/api/monitor-sources/${id}`, {
    method: "DELETE",
  });
}

export function crawlMonitorSource(id: number) {
  return requestJson<CrawlTask>(`/api/monitor-sources/${id}/crawl`, {
    method: "POST",
  });
}

export function updateMonitorSource(id: number, payload: Partial<MonitorSourceCreatePayload>) {
  return requestJson<MonitorSource>(`/api/monitor-sources/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export type SchedulerStatus = {
  running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run_time: string | null;
  }>;
};

export function getSchedulerStatus() {
  return requestJson<SchedulerStatus>("/api/monitor-sources/scheduler/status");
}

export async function getCollectorsCapabilities() {
  const response = await fetch(`${API_BASE_URL}/api/collectors`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`采集器能力接口响应异常: ${response.status} ${response.statusText}`);
  }

  if (!response.ok) {
    throw new Error(`采集器能力接口请求失败: ${response.status} ${response.statusText}`);
  }

  if (payload && typeof payload === "object" && "success" in payload && "data" in payload) {
    const wrapped = payload as ApiResponse<CollectorCapabilitiesResponse>;
    if (!wrapped.success || !wrapped.data) {
      throw new Error(wrapped.message || "采集器能力接口返回失败");
    }
    return wrapped.data;
  }

  return payload as CollectorCapabilitiesResponse;
}

export function getCrawlTasks() {
  return requestJson<CrawlTaskListResponse>("/api/crawl-tasks");
}

export function getCollectionTasks(params: {
  status?: string;
  source_type?: "keyword" | "account" | "post_url";
  page?: number;
  page_size?: number;
} = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return requestJson<CrawlTaskListResponse>(`/api/collection/tasks${queryString ? `?${queryString}` : ""}`);
}

export function getCollectionTask(id: number) {
  return requestJson<CrawlTask>(`/api/collection/tasks/${id}`);
}

export function createCollectionTask(payload: CollectionTaskCreatePayload) {
  return requestJson<CrawlTask>("/api/collection/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runCollectionTask(id: number) {
  return requestJson<CrawlTask>(`/api/collection/tasks/${id}/run`, {
    method: "POST",
  });
}

export function getCrawlTask(id: number) {
  return requestJson<CrawlTask>(`/api/crawl-tasks/${id}`);
}

export function rerunCrawlTask(id: number) {
  return requestJson<CrawlTask>(`/api/crawl-tasks/${id}/rerun`, {
    method: "POST",
  });
}

export type FailureTypeMeta = {
  value: string;
  label: string;
  description: string;
  suggestion: string;
};

export type FailureTypesMetaResponse = Record<string, FailureTypeMeta>;

export function getFailureTypesMeta() {
  return requestJson<FailureTypesMetaResponse>("/api/crawl-tasks/failure-types/meta");
}

export function getLeads(params: LeadQueryParams = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return requestJson<LeadListResponse>(`/api/leads${queryString ? `?${queryString}` : ""}`);
}

export function getPosts(params: PostQueryParams = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return requestJson<PostListResponse>(`/api/posts${queryString ? `?${queryString}` : ""}`);
}

export function getPost(postId: number) {
  return requestJson<Post>(`/api/posts/${postId}`);
}

export function getComments(params: CommentQueryParams = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return requestJson<CommentListResponse>(`/api/comments${queryString ? `?${queryString}` : ""}`);
}

export function getPendingCompetitors(params: PendingCompetitorQueryParams = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  return requestJson<PendingCompetitor[]>(`/api/pending-competitors${queryString ? `?${queryString}` : ""}`);
}

export function approvePendingCompetitor(id: number) {
  return requestJson<ApprovePendingCompetitorResponse>(`/api/pending-competitors/${id}/approve`, {
    method: "POST",
  });
}

export function ignorePendingCompetitor(id: number) {
  return requestJson<PendingCompetitor>(`/api/pending-competitors/${id}/ignore`, {
    method: "POST",
  });
}

export function updateLeadStatus(id: number, status: string, notes?: string | null) {
  return requestJson<Lead>(`/api/leads/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, notes } satisfies LeadStatusUpdatePayload),
  });
}

export function convertLeadToCrm(id: number, payload: LeadConvertToCrmPayload = {}) {
  return requestJson<LeadConvertToCrmResult>(`/api/leads/${id}/convert-to-crm`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCrmDashboard() {
  return requestJson<CrmDashboard>("/api/crm/dashboard");
}

export function getCrmCustomers(params: { owner_name?: string; status?: string; keyword?: string; page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return requestJson<CrmListResponse<CrmCustomer>>(`/api/crm/customers${queryString ? `?${queryString}` : ""}`);
}

export function createCrmCustomer(payload: CrmCustomerPayload) {
  return requestJson<CrmCustomer>("/api/crm/customers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCrmCustomer(id: number, payload: Partial<CrmCustomerPayload>) {
  return requestJson<CrmCustomer>(`/api/crm/customers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getCrmOpportunities(params: { owner_name?: string; stage?: string; customer_id?: number; page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return requestJson<CrmListResponse<CrmOpportunity>>(`/api/crm/opportunities${queryString ? `?${queryString}` : ""}`);
}

export function updateCrmOpportunity(id: number, payload: Partial<CrmOpportunity>) {
  return requestJson<CrmOpportunity>(`/api/crm/opportunities/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getCrmFollowUps(params: { customer_id?: number; opportunity_id?: number; page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return requestJson<CrmListResponse<CrmFollowUp>>(`/api/crm/follow-ups${queryString ? `?${queryString}` : ""}`);
}

export function createCrmFollowUp(payload: CrmFollowUpPayload) {
  return requestJson<CrmFollowUp>("/api/crm/follow-ups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCrmTasks(params: { owner_name?: string; status?: string; customer_id?: number; page?: number; page_size?: number } = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return requestJson<CrmListResponse<CrmTask>>(`/api/crm/tasks${queryString ? `?${queryString}` : ""}`);
}

export function createCrmTask(payload: CrmTaskPayload) {
  return requestJson<CrmTask>("/api/crm/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCrmTask(id: number, payload: Partial<CrmTask>) {
  return requestJson<CrmTask>(`/api/crm/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getCrmContracts(params: { customer_id?: number; status?: string } = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return requestJson<CrmContract[]>(`/api/crm/contracts${queryString ? `?${queryString}` : ""}`);
}

export function getCrmReceivablePlans(params: { customer_id?: number; status?: string } = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
  });
  const queryString = searchParams.toString();
  return requestJson<CrmReceivablePlan[]>(`/api/crm/receivable-plans${queryString ? `?${queryString}` : ""}`);
}

export async function exportLeadsCsv(params: LeadQueryParams = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  const response = await fetch(`${API_BASE_URL}/api/leads/export${queryString ? `?${queryString}` : ""}`);
  if (!response.ok) {
    throw new Error(`导出失败: ${response.status}`);
  }
  return response.blob();
}

export function generateDailyReport(platform?: string) {
  const query = platform ? `?platform=${platform}` : "";
  return requestJson<DailyReport>(`/api/daily-reports/generate${query}`, { method: "POST" });
}

export function getTodayReport(platform?: string) {
  const query = platform ? `?platform=${platform}` : "";
  return requestJson<DailyReport>(`/api/daily-reports/today${query}`);
}

export function listDailyReports(platform?: string) {
  const query = platform ? `?platform=${platform}` : "";
  return requestJson<DailyReport[]>(`/api/daily-reports${query}`);
}

export async function exportDailyReport(format: string = "markdown", platform?: string) {
  const params = new URLSearchParams();
  params.set("format", format);
  if (platform) params.set("platform", platform);
  const response = await fetch(`${API_BASE_URL}/api/daily-reports/today/export?${params.toString()}`);
  if (!response.ok) {
    let message = `导出失败: ${response.status}`;
    try {
      const body = await response.json();
      if (body.message) message = body.message;
    } catch {}
    throw new Error(message);
  }
  return response.blob();
}

export type QueueStatus = {
  active_task_id: number | null;
  queue_size: number;
  queue_items: number[];
};

export type DashboardStats = {
  source_count: number;
  task_count: number;
  post_count: number;
  comment_count: number;
  lead_count: number;
  a_lead_count: number;
  pending_competitor_count: number;
  recent_a_leads: Array<{
    id: number;
    platform: string;
    user_name: string;
    content: string;
    lead_score: number;
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

export function getDashboardStats() {
  return requestJson<DashboardStats>("/api/dashboard/stats");
}

export function getMediaCrawlerHealth() {
  return requestJson<MediaCrawlerHealth>("/api/dashboard/media-crawler-health");
}

export function getQueueStatus() {
  return requestJson<QueueStatus>("/api/collection/tasks/queue/status");
}

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

export function getScoringRules() {
  return requestJson<ScoringRules>("/api/scoring-rules");
}

export function updateScoringRules(rules: ScoringRules) {
  return requestJson<ScoringRules>("/api/scoring-rules", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rules }),
  });
}

export function testScoring(text: string) {
  return requestJson<ScoringTestResult>("/api/scoring-rules/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export function reloadScoringRules() {
  return requestJson<{ version: string; message: string }>("/api/scoring-rules/reload", {
    method: "POST",
  });
}

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

export function generateDemoData() {
  return requestJson<DemoGenerateResult>("/api/monitor-sources/demo/generate", {
    method: "POST",
  });
}
