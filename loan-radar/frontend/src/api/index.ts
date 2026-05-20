import { buildSearchParams, requestJson } from "./request";
import type {
  ApprovePendingCompetitorResponse,
  CollectorCapabilitiesResponse,
  CollectionTaskCreatePayload,
  CommentListResponse,
  CommentQueryParams,
  CookieStatusResponse,
  CrawlTask,
  CrawlTaskListResponse,
  CrmCustomer,
  CrmCustomerManualCreate,
  CrmDashboard,
  CrmFollowRecord,
  DailyReport,
  DashboardStats,
  DemoGenerateResult,
  FailureTypesMetaResponse,
  Lead,
  LeadConvertToCrmPayload,
  LeadConvertToCrmResult,
  LeadListResponse,
  LeadQueryParams,
  MediaCrawlerHealth,
  MonitorSource,
  MonitorSourceCreatePayload,
  PendingCompetitor,
  PendingCompetitorQueryParams,
  PostListResponse,
  PostQueryParams,
  QueueStatus,
  ScoringRules,
  ScoringTestResult,
  SchedulerStatus,
} from "./types";

export { API_BASE_URL } from "./request";
export type * from "./types";

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

export function getSchedulerStatus() {
  return requestJson<SchedulerStatus>("/api/monitor-sources/scheduler/status");
}

export async function getCollectorsCapabilities() {
  const { API_BASE_URL } = await import("./request");
  const response = await fetch(`${API_BASE_URL}/api/collectors`, {
    headers: { "Content-Type": "application/json" },
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
    const wrapped = payload as { success: boolean; data: CollectorCapabilitiesResponse; message?: string };
    if (!wrapped.success || !wrapped.data) {
      throw new Error(wrapped.message || "采集器能力接口返回失败");
    }
    return wrapped.data;
  }
  return payload as CollectorCapabilitiesResponse;
}

export function generateDemoData() {
  return requestJson<DemoGenerateResult>("/api/monitor-sources/demo/generate", {
    method: "POST",
  });
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
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<CrawlTaskListResponse>(`/api/collection/tasks${qs ? `?${qs}` : ""}`);
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

export function getFailureTypesMeta() {
  return requestJson<FailureTypesMetaResponse>("/api/crawl-tasks/failure-types/meta");
}

export function getLeads(params: LeadQueryParams = {}) {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<LeadListResponse>(`/api/leads${qs ? `?${qs}` : ""}`);
}

export function updateLeadStatus(id: number, status: string, notes?: string | null) {
  return requestJson<Lead>(`/api/leads/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, notes }),
  });
}

export function convertLeadToCrm(id: number, payload: LeadConvertToCrmPayload = {}) {
  return requestJson<LeadConvertToCrmResult>(`/api/leads/${id}/convert-to-crm`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function exportLeadsCsv(params: LeadQueryParams = {}) {
  const { API_BASE_URL } = await import("./request");
  const qs = buildSearchParams(params as Record<string, unknown>);
  const response = await fetch(`${API_BASE_URL}/api/leads/export${qs ? `?${qs}` : ""}`);
  if (!response.ok) {
    throw new Error(`导出失败: ${response.status}`);
  }
  return response.blob();
}

export function getPosts(params: PostQueryParams = {}) {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<PostListResponse>(`/api/posts${qs ? `?${qs}` : ""}`);
}

export function getPost(postId: number) {
  return requestJson<import("./types").Post>(`/api/posts/${postId}`);
}

export function getComments(params: CommentQueryParams = {}) {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<CommentListResponse>(`/api/comments${qs ? `?${qs}` : ""}`);
}

export function getPendingCompetitors(params: PendingCompetitorQueryParams = {}) {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<PendingCompetitor[]>(`/api/pending-competitors${qs ? `?${qs}` : ""}`);
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

export function getCrmDashboard() {
  return requestJson<CrmDashboard>("/api/crm/dashboard");
}

export function getCrmCustomers(params: { source_type?: string; source_channel?: string; platform?: string; lead_level?: string; status?: string; owner_name?: string; keyword?: string; reminder?: string; page?: number; page_size?: number } = {}) {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<{ items: CrmCustomer[]; total: number; page: number; page_size: number }>(`/api/crm/customers${qs ? `?${qs}` : ""}`);
}

export function getCrmCustomer(id: number) {
  return requestJson<CrmCustomer>(`/api/crm/customers/${id}`);
}

export function createCrmCustomer(payload: CrmCustomerManualCreate) {
  return requestJson<CrmCustomer>("/api/crm/customers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCrmCustomer(id: number, payload: Partial<{ customer_name: string; nickname: string; phone: string; wechat: string; source_channel: string; demand_type: string; demand_description: string; intended_amount: number | null; city: string; lead_level: string; status: string; owner_name: string; entered_by: string; notes: string; next_follow_up_at: string | null }>) {
  return requestJson<CrmCustomer>(`/api/crm/customers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createCrmFollowRecord(customerId: number, payload: { follow_type?: string; content: string; next_follow_up_at?: string | null }) {
  return requestJson<CrmFollowRecord>(`/api/crm/customers/${customerId}/follow-records`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCrmFollowRecords(customerId: number, params: { page?: number; page_size?: number } = {}) {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<{ items: CrmFollowRecord[]; total: number; page: number; page_size: number }>(`/api/crm/customers/${customerId}/follow-records${qs ? `?${qs}` : ""}`);
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
  const { API_BASE_URL } = await import("./request");
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

export function getDashboardStats() {
  return requestJson<DashboardStats>("/api/dashboard/stats");
}

export function getMediaCrawlerHealth() {
  return requestJson<MediaCrawlerHealth>("/api/dashboard/media-crawler-health");
}

export function getQueueStatus() {
  return requestJson<QueueStatus>("/api/collection/tasks/queue/status");
}

export function getScoringRules() {
  return requestJson<ScoringRules>("/api/scoring-rules");
}

export function updateScoringRules(rules: ScoringRules) {
  return requestJson<ScoringRules>("/api/scoring-rules", {
    method: "PUT",
    body: JSON.stringify({ rules }),
  });
}

export function testScoring(text: string) {
  return requestJson<ScoringTestResult>("/api/scoring-rules/test", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function reloadScoringRules() {
  return requestJson<{ version: string; message: string }>("/api/scoring-rules/reload", {
    method: "POST",
  });
}

export type ConvertResult = {
  converted_count: number;
  skipped_count: number;
  failed_count: number;
  details: Array<{
    note_id?: number;
    post_id?: number;
    status: string;
    reason?: string;
    post_id_result?: number;
    note_id_result?: number;
    comments_converted?: number;
    leads_created?: number;
  }>;
};

export function convertNotesToPosts(payload: { note_ids: number[]; source_id?: number; source_type?: string }) {
  return requestJson<ConvertResult>("/api/content-pools/notes-to-posts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function convertPostsToNotes(payload: { post_ids: number[]; platform_account_id?: number | null }) {
  return requestJson<ConvertResult>("/api/content-pools/posts-to-notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCookieStatus() {
  return requestJson<CookieStatusResponse>("/api/accounts/cookie-status");
}
