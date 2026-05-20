import { requestJson, API_BASE_URL, buildSearchParams } from "./request";
import type {
  AppNotification,
  AutoTask,
  AutoTaskCreatePayload,
  AutoTaskRunResult,
  AutoTaskUpdatePayload,
  AnalyticsCommentInsight,
  AnalyticsHotTopic,
  AnalyticsReportPayload,
  AnalyticsReportResponse,
  AnalyticsTopContent,
  BenchmarkCreateDraftsResponse,
  BenchmarkOverview,
  BatchCreateDraftsPayload,
  BatchCreateDraftsResponse,
  BatchTagNotesPayload,
  BatchTagNotesResponse,
  ComposeImagePayload,
  CreateDraftPayload,
  DashboardOverview,
  Draft,
  DescribeImagePayload,
  GenerateNotePayload,
  GenerateCoverPayload,
  GenerateImagePayload,
  GenerateImageResult,
  GeneratedImageAsset,
  GenerateTagsPayload,
  GenerateTitlePayload,
  ImageUtilityFile,
  KeywordGroup,
  KeywordGroupDetail,
  KeywordGroupPayload,
  ModelConfig,
  ModelConfigPayload,
  ModelType,
  MonitoringNote,
  MonitoringRefreshResponse,
  MonitoringSnapshot,
  MonitoringTarget,
  MonitoringTargetPayload,
  NoteAsset,
  NoteComment,
  NotesExportPayload,
  NotesExportResponse,
  Paginated,
  PlatformAccount,
  PublishAsset,
  PublishAssetPayload,
  PublishJob,
  PublishJobUpdatePayload,
  PolishTextPayload,
  ResizeImagePayload,
  RewriteDraftPayload,
  RunDueTasksResponse,
  SchedulerStatus,
  SavedNote,
  SaveNotesResponse,
  SendDraftToPublishPayload,
  Tag,
  TagPayload,
  TaskRecord,
  UserImageFile,
  XhsNoteSearchResponse,
  XhsDataCrawlItem,
  XhsDataCrawlPayload,
  XhsSearchOptions,
  XhsSearchNote,
  XhsQrLoginSession,
} from "./xhs-types";

export type UploadedFile = {
  file_name: string;
  file_path: string;
  download_url: string;
  asset_type: "image" | "video";
  size: number;
};

export type DraftAsset = {
  id: number;
  draft_id: number;
  asset_type: "image" | "video" | string;
  url: string;
  local_path: string;
  sort_order: number;
};

export type SavedNoteFilters = {
  platform?: string;
  q?: string;
  tag_id?: number;
  has_assets?: boolean;
  has_comments?: boolean;
  page_size?: number;
};

type PlatformOrQuery<T extends Record<string, unknown> = Record<string, unknown>> = string | T;

function normalizePlatformQuery<T extends Record<string, unknown>>(
  platformOrQuery: PlatformOrQuery<T> | undefined,
  defaults: T,
): T {
  if (typeof platformOrQuery === "string") {
    return { ...defaults, platform: platformOrQuery } as T;
  }
  return { ...defaults, ...(platformOrQuery ?? {}) };
}

export function fetchXhsOverview(): Promise<DashboardOverview> {
  return requestJson<DashboardOverview>("/api/xhs/analytics/overview");
}

export function fetchXhsTopContent(): Promise<{ items: AnalyticsTopContent[] }> {
  return requestJson<{ items: AnalyticsTopContent[] }>("/api/xhs/analytics/top-content");
}

export function fetchXhsHotTopics(): Promise<{ items: AnalyticsHotTopic[] }> {
  return requestJson<{ items: AnalyticsHotTopic[] }>("/api/xhs/analytics/hot-topics");
}

export function fetchXhsCommentInsights(): Promise<AnalyticsCommentInsight> {
  return requestJson<AnalyticsCommentInsight>("/api/xhs/analytics/comment-insights");
}

export function fetchXhsBenchmarks(): Promise<BenchmarkOverview> {
  return requestJson<BenchmarkOverview>("/api/xhs/analytics/benchmarks");
}

export function createBenchmarkDrafts(targetId: number, limit = 5): Promise<BenchmarkCreateDraftsResponse> {
  return requestJson<BenchmarkCreateDraftsResponse>(`/api/xhs/analytics/benchmarks/${targetId}/create-drafts?limit=${limit}`, { method: "POST" });
}

export function createXhsAnalyticsReport(payload: AnalyticsReportPayload = { format: "json" }): Promise<AnalyticsReportResponse> {
  return requestJson<AnalyticsReportResponse>("/api/xhs/analytics/reports", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchAccounts(platform = "xhs"): Promise<PlatformAccount[]> {
  return requestJson<Paginated<PlatformAccount>>(`/api/accounts?platform=${platform}`).then((r) => r.items);
}

export function fetchSavedNoteIds(platform = "xhs"): Promise<string[]> {
  return requestJson<{ items: string[] }>(`/api/notes/ids?platform=${platform}`).then((r) => r.items);
}

export function fetchSavedNotes(platformOrFilters: string | SavedNoteFilters = "xhs"): Promise<Paginated<SavedNote>> {
  const params = typeof platformOrFilters === "string"
    ? { platform: platformOrFilters }
    : {
        platform: platformOrFilters.platform ?? "xhs",
        q: platformOrFilters.q || undefined,
        tag_id: platformOrFilters.tag_id,
        has_assets: platformOrFilters.has_assets,
        has_comments: platformOrFilters.has_comments,
        page_size: platformOrFilters.page_size,
      };
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<Paginated<SavedNote>>(`/api/notes${qs ? `?${qs}` : ""}`);
}

export function fetchSavedNote(noteId: number, _includeAssets = false): Promise<SavedNote> {
  return requestJson<SavedNote>(`/api/notes/${noteId}`);
}

export function fetchSavedNoteAssets(noteId: number): Promise<Paginated<NoteAsset>> {
  return requestJson<Paginated<NoteAsset>>(`/api/notes/${noteId}/assets`);
}

export function addNoteAsset(noteId: number, payload: { asset_type: string; url?: string; local_path?: string }): Promise<NoteAsset> {
  return requestJson<NoteAsset>(`/api/notes/${noteId}/assets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteNoteAsset(noteId: number, assetId: number): Promise<void> {
  return requestJson<void>(`/api/notes/${noteId}/assets/${assetId}`, { method: "DELETE" });
}

export function reorderNoteAssets(noteId: number, assetIds: number[]): Promise<void> {
  return requestJson<void>(`/api/notes/${noteId}/assets/reorder`, {
    method: "PUT",
    body: JSON.stringify({ asset_ids: assetIds }),
  });
}

export function fetchSavedNoteComments(noteId: number, page = 1): Promise<Paginated<NoteComment>> {
  return requestJson<Paginated<NoteComment>>(`/api/notes/${noteId}/comments?page=${page}&page_size=50`);
}

export function deleteSavedNote(noteId: number): Promise<{ id: number; status: string }> {
  return requestJson<{ id: number; status: string }>(`/api/notes/${noteId}`, { method: "DELETE" });
}

export function fetchTags(): Promise<Paginated<Tag>> {
  return requestJson<Paginated<Tag>>("/api/tags");
}

export function createTag(payload: TagPayload): Promise<Tag> {
  return requestJson<Tag>("/api/tags", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function batchTagNotes(payload: BatchTagNotesPayload): Promise<BatchTagNotesResponse> {
  return requestJson<BatchTagNotesResponse>("/api/notes/batch-tag", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function batchCreateDraftsFromNotes(payload: BatchCreateDraftsPayload): Promise<BatchCreateDraftsResponse> {
  return requestJson<BatchCreateDraftsResponse>("/api/notes/batch-create-drafts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function exportSavedNotes(payload: NotesExportPayload): Promise<NotesExportResponse> {
  return requestJson<NotesExportResponse>("/api/notes/export", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function downloadExportFile(downloadUrl: string, fileName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${downloadUrl}`);
  if (!response.ok) throw new Error(`下载失败: ${response.status}`);
  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

export async function uploadAssetFile(file: File): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append("file", file);
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE_URL}/api/files/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error((body as { message?: string }).message || `上传失败: ${response.status}`);
  }
  const payload = await response.json() as { success: boolean; data: UploadedFile; message: string };
  if (!payload.success) throw new Error(payload.message);
  return payload.data;
}

export async function createMediaObjectUrl(downloadUrl: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${downloadUrl}`);
  if (!response.ok) throw new Error(`获取媒体失败: ${response.status}`);
  const blob = await response.blob();
  return window.URL.createObjectURL(blob);
}

export function searchXhsNotes(payload: XhsSearchOptions): Promise<XhsNoteSearchResponse> {
  return requestJson<XhsNoteSearchResponse>("/api/xhs/pc/search/notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function crawlXhsDataStream(
  payload: XhsDataCrawlPayload,
  onItem: (index: number, item: XhsDataCrawlItem) => void,
  onProgress?: (message: string) => void,
  onError?: (message: string) => void,
): Promise<{ total: number; success_count: number; failed_count: number }> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE_URL}/api/xhs/crawl/data`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `HTTP ${response.status}`);
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response stream");
  const decoder = new TextDecoder();
  let buffer = "";
  let result = { total: 0, success_count: 0, failed_count: 0 };
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "item") onItem(event.index, event.item);
        else if (event.type === "progress") onProgress?.(event.message);
        else if (event.type === "error") onError?.(event.message);
        else if (event.type === "done") result = { total: event.total, success_count: event.success_count, failed_count: event.failed_count };
      } catch { /* skip malformed events */ }
    }
  }
  return result;
}

export function fetchXhsNoteDetail(payload: { account_id: number; url: string }): Promise<XhsSearchNote> {
  return requestJson<XhsSearchNote>("/api/xhs/pc/notes/detail", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchXhsNoteComments(payload: { account_id: number; note_url: string }): Promise<Paginated<NoteComment>> {
  return requestJson<{ total: number; items: NoteComment[] }>("/api/xhs/pc/notes/comments", {
    method: "POST",
    body: JSON.stringify(payload),
  }).then((r) => ({ total: r.total, page: 1, page_size: r.items.length, items: r.items }));
}

export function saveXhsNotesToLibrary(payload: { account_id: number; notes: XhsSearchNote[] }): Promise<SaveNotesResponse> {
  return requestJson<SaveNotesResponse>("/api/notes/batch-save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createDraftFromNote(payload: CreateDraftPayload): Promise<Draft> {
  return requestJson<Draft>("/api/drafts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchDrafts(platform = "xhs"): Promise<Paginated<Draft>> {
  return requestJson<Paginated<Draft>>(`/api/drafts?platform=${platform}`);
}

export function updateDraft(draftId: number, payload: { title?: string; body?: string; tags?: { id?: string; name: string }[] }): Promise<Draft> {
  return requestJson<Draft>(`/api/drafts/${draftId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteDraft(draftId: number): Promise<{ id: number; status: string }> {
  return requestJson<{ id: number; status: string }>(`/api/drafts/${draftId}`, { method: "DELETE" });
}

export function fetchDraftAssets(draftId: number): Promise<{ items: DraftAsset[] }> {
  return requestJson<{ items: DraftAsset[] }>(`/api/drafts/${draftId}/assets`);
}

export function addDraftAsset(draftId: number, payload: { asset_type: string; url?: string; local_path?: string }): Promise<DraftAsset> {
  return requestJson<DraftAsset>(`/api/drafts/${draftId}/assets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteDraftAsset(draftId: number, assetId: number): Promise<void> {
  return requestJson<void>(`/api/drafts/${draftId}/assets/${assetId}`, { method: "DELETE" });
}

export function updateDraftAsset(draftId: number, assetId: number, payload: { url?: string; local_path?: string }): Promise<DraftAsset> {
  return requestJson<DraftAsset>(`/api/drafts/${draftId}/assets/${assetId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function reorderDraftAssets(draftId: number, assetIds: number[]): Promise<void> {
  return requestJson<void>(`/api/drafts/${draftId}/assets/reorder`, {
    method: "PUT",
    body: JSON.stringify({ asset_ids: assetIds }),
  });
}

export function sendDraftToPublish(draftId: number, payload: SendDraftToPublishPayload): Promise<PublishJob> {
  return requestJson<PublishJob>(`/api/drafts/${draftId}/send-to-publish`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rewriteDraftWithAi(payload: RewriteDraftPayload): Promise<Draft> {
  return requestJson<Draft>("/api/ai/rewrite-note", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateNoteWithAi(payload: GenerateNotePayload): Promise<Draft> {
  return requestJson<Draft>("/api/ai/generate-note", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateTitleOptions(payload: GenerateTitlePayload): Promise<{ items: string[] }> {
  return requestJson<{ items: string[] }>("/api/ai/generate-title", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateTagOptions(payload: GenerateTagsPayload): Promise<{ items: string[] }> {
  return requestJson<{ items: string[] }>("/api/ai/generate-tags", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function polishTextWithAi(payload: PolishTextPayload): Promise<{ text: string }> {
  return requestJson<{ text: string }>("/api/ai/polish-text", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchGeneratedImageAssets(): Promise<Paginated<GeneratedImageAsset>> {
  return requestJson<Paginated<GeneratedImageAsset>>("/api/ai/images/assets");
}

export function deleteGeneratedImageAsset(assetId: number): Promise<void> {
  return requestJson<void>(`/api/ai/images/assets/${assetId}`, { method: "DELETE" });
}

export function deleteUserImage(fileName: string): Promise<void> {
  return requestJson<void>(`/api/files/images/${fileName}`, { method: "DELETE" });
}

export function generateCoverWithAi(payload: GenerateCoverPayload): Promise<GeneratedImageAsset> {
  return requestJson<GeneratedImageAsset>("/api/ai/images/generate-cover", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateImageWithAi(payload: GenerateImagePayload): Promise<GenerateImageResult> {
  return requestJson<GenerateImageResult>("/api/ai/images/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchUserImages(): Promise<{ items: UserImageFile[] }> {
  return requestJson<{ items: UserImageFile[] }>("/api/files/images");
}

export function describeImageWithAi(payload: DescribeImagePayload): Promise<{ text: string }> {
  return requestJson<{ text: string }>("/api/ai/images/describe", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function composeImageUtility(payload: ComposeImagePayload): Promise<ImageUtilityFile> {
  return requestJson<ImageUtilityFile>("/api/files/images/compose", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resizeImageUtility(payload: ResizeImagePayload): Promise<ImageUtilityFile> {
  return requestJson<ImageUtilityFile>("/api/files/images/resize", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchModelConfigs(modelType?: ModelType): Promise<Paginated<ModelConfig>> {
  const params = modelType ? `?model_type=${modelType}` : "";
  return requestJson<Paginated<ModelConfig>>(`/api/model-configs${params}`);
}

export function createModelConfig(payload: ModelConfigPayload): Promise<ModelConfig> {
  return requestJson<ModelConfig>("/api/model-configs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setDefaultModelConfig(configId: number): Promise<ModelConfig> {
  return requestJson<ModelConfig>(`/api/model-configs/${configId}/set-default`, { method: "POST" });
}

export function updateModelConfig(configId: number, payload: Partial<ModelConfigPayload>): Promise<ModelConfig> {
  return requestJson<ModelConfig>(`/api/model-configs/${configId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteModelConfig(configId: number): Promise<{ id: number; status: string }> {
  return requestJson<{ id: number; status: string }>(`/api/model-configs/${configId}`, { method: "DELETE" });
}

export function testModelConfig(configId: number): Promise<{ id: number; status: string; message: string }> {
  return requestJson<{ id: number; status: string; message: string }>(`/api/model-configs/${configId}/test`, { method: "POST" });
}

export function fetchNotifications(params: { page_size?: number } = {}): Promise<Paginated<AppNotification>> {
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<Paginated<AppNotification>>(`/api/notifications${qs ? `?${qs}` : ""}`);
}

export function markNotificationRead(id: number): Promise<AppNotification> {
  return requestJson<AppNotification>(`/api/notifications/${id}/read`, { method: "POST" });
}

export function markAllNotificationsRead(): Promise<{ marked: number }> {
  return requestJson<{ marked: number }>("/api/notifications/read-all", { method: "POST" });
}

export function fetchUnreadNotificationCount(): Promise<{ count: number; breakdown: Record<string, number> }> {
  return requestJson<{ count: number; breakdown: Record<string, number> }>("/api/notifications/unread-count");
}

export function fetchXhsTasks(params: PlatformOrQuery<{ platform?: string; page?: number; page_size?: number }> = {}): Promise<Paginated<TaskRecord>> {
  const normalized = normalizePlatformQuery(params, {});
  const qs = buildSearchParams(normalized as Record<string, unknown>);
  return requestJson<Paginated<TaskRecord>>(`/api/tasks${qs ? `?${qs}` : ""}`);
}

export function fetchXhsTask(taskId: number): Promise<TaskRecord> {
  return requestJson<TaskRecord>(`/api/tasks/${taskId}`);
}

export function cancelXhsTask(taskId: number): Promise<TaskRecord> {
  return requestJson<TaskRecord>(`/api/tasks/${taskId}/cancel`, { method: "POST" });
}

export function retryXhsTask(taskId: number): Promise<TaskRecord> {
  return requestJson<TaskRecord>(`/api/tasks/${taskId}/retry`, { method: "POST" });
}

export function fetchXhsSchedulerStatus(): Promise<SchedulerStatus> {
  return requestJson<SchedulerStatus>("/api/tasks/scheduler/status");
}

export function fetchKeywordGroups(platformOrQuery: PlatformOrQuery<{ platform?: string }> = "xhs"): Promise<Paginated<KeywordGroup>> {
  const params = normalizePlatformQuery(platformOrQuery, { platform: "xhs" });
  const qs = buildSearchParams(params as Record<string, unknown>);
  return requestJson<Paginated<KeywordGroup>>(`/api/keyword-groups${qs ? `?${qs}` : ""}`);
}

export function fetchKeywordGroupDetail(groupId: number): Promise<KeywordGroupDetail> {
  return requestJson<KeywordGroupDetail>(`/api/keyword-groups/${groupId}`);
}

export function createKeywordGroup(payload: KeywordGroupPayload): Promise<KeywordGroup> {
  return requestJson<KeywordGroup>("/api/keyword-groups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateKeywordGroup(groupId: number, payload: KeywordGroupPayload): Promise<KeywordGroup> {
  return requestJson<KeywordGroup>(`/api/keyword-groups/${groupId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteKeywordGroup(groupId: number): Promise<void> {
  return requestJson<void>(`/api/keyword-groups/${groupId}`, { method: "DELETE" });
}

export function fetchMonitoringTargets(): Promise<Paginated<MonitoringTarget>> {
  return requestJson<Paginated<MonitoringTarget>>("/api/xhs/monitoring/targets");
}

export function createMonitoringTarget(payload: MonitoringTargetPayload): Promise<MonitoringTarget> {
  return requestJson<MonitoringTarget>("/api/xhs/monitoring/targets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function refreshMonitoringTarget(targetId: number): Promise<MonitoringRefreshResponse> {
  return requestJson<MonitoringRefreshResponse>(`/api/xhs/monitoring/targets/${targetId}/refresh`, { method: "POST" });
}

export function deleteMonitoringTarget(targetId: number): Promise<void> {
  return requestJson<void>(`/api/xhs/monitoring/targets/${targetId}`, { method: "DELETE" });
}

export function fetchPublishJobs(params: PlatformOrQuery<{ platform?: string; status?: string; page?: number; page_size?: number }> = {}): Promise<Paginated<PublishJob>> {
  const normalized = normalizePlatformQuery(params, {});
  const qs = buildSearchParams(normalized as Record<string, unknown>);
  return requestJson<Paginated<PublishJob>>(`/api/publish/jobs${qs ? `?${qs}` : ""}`);
}

export function fetchPublishJob(jobId: number): Promise<PublishJob> {
  return requestJson<PublishJob>(`/api/publish/jobs/${jobId}`);
}

export function updatePublishJob(jobId: number, payload: PublishJobUpdatePayload): Promise<PublishJob> {
  return requestJson<PublishJob>(`/api/publish/jobs/${jobId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function cancelPublishJob(jobId: number): Promise<PublishJob> {
  return requestJson<PublishJob>(`/api/publish/jobs/${jobId}/cancel`, { method: "POST" });
}

export function addPublishAsset(jobId: number, payload: PublishAssetPayload): Promise<PublishAsset> {
  return requestJson<PublishAsset>(`/api/publish/jobs/${jobId}/assets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchPublishAssets(jobId: number): Promise<Paginated<PublishAsset>> {
  return requestJson<Paginated<PublishAsset>>(`/api/publish/jobs/${jobId}/assets`);
}

export function publishJobToCreator(jobId: number): Promise<PublishJob> {
  return requestJson<PublishJob>(`/api/publish/jobs/${jobId}/publish`, { method: "POST" });
}

export function fetchAutoTasks(): Promise<Paginated<AutoTask>> {
  return requestJson<Paginated<AutoTask>>("/api/xhs/auto-ops/tasks");
}

export function createAutoTask(payload: AutoTaskCreatePayload): Promise<AutoTask> {
  return requestJson<AutoTask>("/api/xhs/auto-ops/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAutoTask(taskId: number, payload: AutoTaskUpdatePayload): Promise<AutoTask> {
  return requestJson<AutoTask>(`/api/xhs/auto-ops/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAutoTask(taskId: number): Promise<void> {
  return requestJson<void>(`/api/xhs/auto-ops/tasks/${taskId}`, { method: "DELETE" });
}

export function runAutoTask(taskId: number): Promise<AutoTaskRunResult> {
  return requestJson<AutoTaskRunResult>(`/api/xhs/auto-ops/tasks/${taskId}/run`, { method: "POST" });
}

export function runDueAutoTasks(_platform = "xhs"): Promise<RunDueTasksResponse> {
  return requestJson<RunDueTasksResponse>("/api/xhs/auto-ops/run-due", { method: "POST" });
}

export function startQrLogin(): Promise<XhsQrLoginSession> {
  return requestJson<XhsQrLoginSession>("/api/accounts/xhs/qr-login/start", { method: "POST" });
}

export function checkQrLogin(sessionId: number): Promise<XhsQrLoginSession> {
  return requestJson<XhsQrLoginSession>(`/api/accounts/xhs/qr-login/check?session_id=${sessionId}`, { method: "POST" });
}

export function importCookieAccount(payload: { cookie_text: string; sub_type?: "pc" | "creator" }): Promise<PlatformAccount> {
  return requestJson<PlatformAccount>("/api/accounts/xhs/cookie-import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteAccount(accountId: number): Promise<void> {
  return requestJson<void>(`/api/accounts/${accountId}`, { method: "DELETE" });
}

export function refreshAccountStatus(accountId: number): Promise<PlatformAccount> {
  return requestJson<PlatformAccount>(`/api/accounts/${accountId}/refresh`, { method: "POST" });
}

export function checkAccount(accountId: number): Promise<PlatformAccount> {
  return requestJson<PlatformAccount>(`/api/accounts/${accountId}/check`, { method: "POST" });
}

export function importXhsCookieAccount(payload: {
  sub_type: "pc" | "creator";
  cookie_string: string;
  sync_creator?: boolean;
}): Promise<PlatformAccount> {
  return requestJson<PlatformAccount>("/api/accounts/import-cookie", {
    method: "POST",
    body: JSON.stringify({ platform: "xhs", ...payload }),
  });
}

export function createXhsPcQrLoginSession(payload?: { sync_creator?: boolean }): Promise<XhsQrLoginSession> {
  return requestJson<XhsQrLoginSession>("/api/xhs/login-sessions/pc/qrcode", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export function createXhsCreatorQrLoginSession(): Promise<XhsQrLoginSession> {
  return requestJson<XhsQrLoginSession>("/api/xhs/login-sessions/creator/qrcode", { method: "POST" });
}

export function pollXhsLoginSession(sessionId: number): Promise<XhsQrLoginSession> {
  return requestJson<XhsQrLoginSession>(`/api/xhs/login-sessions/${sessionId}`);
}

export function sendXhsPhoneCode(payload: {
  sub_type: "pc" | "creator";
  phone: string;
  sync_creator?: boolean;
}): Promise<{ session_id: number; status: string; message: string }> {
  return requestJson<{ session_id: number; status: string; message: string }>(
    `/api/xhs/login-sessions/${payload.sub_type}/phone/send-code`,
    { method: "POST", body: JSON.stringify({ phone: payload.phone, sync_creator: payload.sync_creator }) }
  );
}

export function confirmXhsPhoneLogin(payload: {
  sub_type: "pc" | "creator";
  session_id: number;
  phone: string;
  code: string;
  sync_creator?: boolean;
}): Promise<XhsQrLoginSession> {
  return requestJson<XhsQrLoginSession>(`/api/xhs/login-sessions/${payload.sub_type}/phone/confirm`, {
    method: "POST",
    body: JSON.stringify({ session_id: payload.session_id, phone: payload.phone, code: payload.code, sync_creator: payload.sync_creator }),
  });
}

export { fetchXhsTasks as fetchTasks, fetchXhsTask as fetchTask, cancelXhsTask as cancelTask, retryXhsTask as retryTask, fetchXhsSchedulerStatus as fetchSchedulerStatus, runDueAutoTasks as runDueTasks, fetchKeywordGroupDetail as fetchKeywordGroup, cancelPublishJob as deletePublishJob };

export interface VideoFile {
  file_name: string;
  url: string;
  size: number;
  duration: number;
  media_type: string;
}

export interface ExtractCoverResult {
  file_name: string;
  download_url: string;
  width: number;
  height: number;
}

export function fetchVideoFiles(page = 1, pageSize = 20): Promise<Paginated<VideoFile>> {
  return requestJson<Paginated<VideoFile>>(`/api/video-studio/videos?page=${page}&page_size=${pageSize}`);
}

export function deleteVideoFile(fileName: string): Promise<void> {
  return requestJson<void>(`/api/video-studio/videos/${fileName}`, { method: "DELETE" });
}

export function extractVideoCover(payload: {
  video_file_name: string;
  timestamp_seconds?: number;
  width?: number;
  height?: number;
}): Promise<ExtractCoverResult> {
  return requestJson<ExtractCoverResult>("/api/video-studio/extract-cover", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function describeVideoWithAi(payload: {
  video_url: string;
  instruction?: string;
}): Promise<{ text: string }> {
  return requestJson<{ text: string }>("/api/video-studio/describe", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
