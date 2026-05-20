import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  createCollectionTask,
  generateDailyReport,
  getCrawlTask,
  getCrawlTasks,
  getFailureTypesMeta,
  getMonitorSources,
  getQueueStatus,
  rerunCrawlTask,
  runCollectionTask,
  type CrawlTask,
  type CollectionTaskCreatePayload,
  type FailureTypesMetaResponse,
  type MonitorSource,
  type QueueStatus,
} from "../api/index";
import { showToast } from "../components/ToastContainer";

type SourceType = "keyword" | "account" | "post_url";

type FormState = {
  sourceType: SourceType;
  sourceValue: string;
  platform: string;
  limitCount: number;
};

const PLATFORM_OPTIONS = [
  { label: "小红书", value: "xhs" },
  { label: "抖音", value: "douyin" },
  { label: "知乎", value: "zhihu" },
];

const PLATFORM_LABELS: Record<string, string> = {
  xhs: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  keyword: "关键词",
  account: "同行账号",
  post_url: "指定帖子",
};

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType; label: string; hint: string }> = [
  { value: "keyword", label: "关键词采集", hint: "输入关键词，例如：征信花了" },
  { value: "account", label: "同行账号采集", hint: "输入账号主页 URL" },
  { value: "post_url", label: "指定帖子采集", hint: "输入帖子 URL" },
];

const PROGRESS_LABELS: Record<string, string> = {
  queued: "排队中",
  collecting: "采集中",
  saving_posts: "保存帖子",
  scoring_leads: "线索评分",
  done: "完成",
  failed: "失败",
  retry_1: "重试第1次",
  retry_2: "重试第2次",
  retry_3: "重试第3次",
};

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function statusText(status: string) {
  const mapping: Record<string, string> = {
    pending: "待处理",
    running: "运行中",
    success: "成功",
    failed: "失败",
    retrying: "重试中",
  };
  return mapping[status] ?? status;
}

function progressText(progress: string | null | undefined) {
  if (!progress) return "-";
  return PROGRESS_LABELS[progress] ?? progress;
}

function statusClassName(status: string) {
  return `status-pill status-${status}`;
}

function platformBadgeClass(platform: string) {
  return `platform-badge platform-${platform}`;
}

type CrawlTaskView = CrawlTask & {
  source_name: string;
};

export default function CrawlTasksPage({ embedded = false }: { embedded?: boolean } = {}) {
  const navigate = useNavigate();

  const [form, setForm] = useState<FormState>({
    sourceType: "keyword",
    sourceValue: "",
    platform: "xhs",
    limitCount: 5,
  });
  const [submitting, setSubmitting] = useState(false);
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const [tasks, setTasks] = useState<CrawlTaskView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [selectedTask, setSelectedTask] = useState<CrawlTaskView | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [failureTypesMeta, setFailureTypesMeta] = useState<FailureTypesMetaResponse | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeTaskIdsRef = useRef<Set<number>>(new Set());
  const prevStatusRef = useRef<Map<number, string>>(new Map());

  const selectedOption = useMemo(
    () => SOURCE_TYPE_OPTIONS.find((option) => option.value === form.sourceType),
    [form.sourceType],
  );

  const hasActiveTasks = useMemo(
    () => tasks.some((t) => t.status === "pending" || t.status === "running" || t.status === "retrying"),
    [tasks],
  );

  async function loadTasks() {
    setLoading(true);
    setError(null);

    try {
      const [taskResult, sources] = await Promise.all([getCrawlTasks(), getMonitorSources()]);
      const sourceNameMap = new Map<number, MonitorSource>(sources.map((source) => [source.id, source]));
      const taskViews = taskResult.items.map((task) => ({
        ...task,
        source_name:
          task.source_id == null ? "手动创建" : sourceNameMap.get(task.source_id)?.name ?? `监控源 #${task.source_id}`,
      }));
      setTasks(taskViews);

      const activeIds = new Set<number>();
      for (const t of taskViews) {
        if (t.status === "pending" || t.status === "running" || t.status === "retrying") {
          activeIds.add(t.id);
        }
      }
      activeTaskIdsRef.current = activeIds;
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载采集任务失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadQueueStatus() {
    try {
      const status = await getQueueStatus();
      setQueueStatus(status);
    } catch {
      // silent
    }
  }

  async function loadFailureTypesMeta() {
    try {
      const meta = await getFailureTypesMeta();
      setFailureTypesMeta(meta);
    } catch {
      // silent
    }
  }

  const pollActiveTasks = useCallback(async () => {
    const activeIds = activeTaskIdsRef.current;
    if (activeIds.size === 0) return;

    try {
      const updates = await Promise.all(
        Array.from(activeIds).map((id) => getCrawlTask(id).catch(() => null)),
      );

      setTasks((prev) =>
        prev.map((task) => {
          const updated = updates.find((u) => u && u.id === task.id);
          if (!updated) return task;

          const prevStatus = prevStatusRef.current.get(task.id);
          if (prevStatus && prevStatus !== updated.status) {
            if (updated.status === "success") {
              showToast("success", `任务 #${task.id} 采集完成`, `获得 ${updated.post_count} 帖子、${updated.lead_count} 线索`);
            } else if (updated.status === "failed") {
              showToast("error", `任务 #${task.id} 采集失败`, updated.error_message?.slice(0, 80) || "未知错误");
            } else if (updated.status === "retrying") {
              showToast("warning", `任务 #${task.id} 正在重试`, `第 ${updated.retry_count} 次重试`);
            }
          }
          prevStatusRef.current.set(task.id, updated.status);

          if (updated.status === "success" || updated.status === "failed") {
            activeTaskIdsRef.current.delete(updated.id);
          }
          return { ...task, ...updated };
        }),
      );
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    void Promise.all([loadTasks(), loadQueueStatus(), loadFailureTypesMeta()]);
  }, []);

  useEffect(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (hasActiveTasks) {
      pollingRef.current = setInterval(() => {
        void Promise.all([pollActiveTasks(), loadQueueStatus()]);
      }, 3000);
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [hasActiveTasks, pollActiveTasks]);

  const hasItems = useMemo(() => tasks.length > 0, [tasks]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFormMessage(null);
    setFormError(null);

    const payload: CollectionTaskCreatePayload = {
      platform: form.platform,
      source_type: form.sourceType,
      source_value: form.sourceValue.trim(),
      limit_count: form.limitCount,
    };

    try {
      if (!payload.source_value) {
        throw new Error("请输入采集目标");
      }
      const created = await createCollectionTask(payload);
      await runCollectionTask(created.id);
      setFormMessage(`任务 #${created.id} 已创建并加入队列，当前状态：排队中`);
      showToast("info", `任务 #${created.id} 已创建`, "已加入采集队列，请等待执行");
      setForm((current) => ({ ...current, sourceValue: "" }));
      activeTaskIdsRef.current.add(created.id);
      prevStatusRef.current.set(created.id, "pending");
      await loadTasks();
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : "创建采集任务失败");
      showToast("error", "创建任务失败", submitError instanceof Error ? submitError.message : "未知错误");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleViewTask(taskId: number) {
    setDetailLoading(true);
    setDetailError(null);

    try {
      const task = await getCrawlTask(taskId);
      const sourceName =
        tasks.find((item) => item.id === taskId)?.source_name ??
        (task.source_id == null ? "手动创建" : `监控源 #${task.source_id}`);
      setSelectedTask({ ...task, source_name: sourceName });
    } catch (viewError) {
      setDetailError(viewError instanceof Error ? viewError.message : "加载任务详情失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleRerun(task: CrawlTaskView) {
    setBusyId(task.id);
    setDetailError(null);

    try {
      await rerunCrawlTask(task.id);
      showToast("info", `任务 #${task.id} 已重新启动`, "正在重新采集");
      activeTaskIdsRef.current.add(task.id);
      prevStatusRef.current.set(task.id, "pending");
      await loadTasks();
      if (selectedTask?.id === task.id) {
        await handleViewTask(task.id);
      }
    } catch (rerunError) {
      setDetailError(rerunError instanceof Error ? rerunError.message : "重跑失败任务失败");
      showToast("error", "重跑失败", rerunError instanceof Error ? rerunError.message : "未知错误");
    } finally {
      setBusyId(null);
    }
  }

  async function handleGenerateReport() {
    setGeneratingReport(true);
    try {
      await generateDailyReport();
      showToast("success", "日报已生成", "可前往今日报告页面查看");
      navigate("/daily-reports");
    } catch (err) {
      showToast("error", "生成日报失败", err instanceof Error ? err.message : "未知错误");
    } finally {
      setGeneratingReport(false);
    }
  }

  function closeDetail() {
    setSelectedTask(null);
    setDetailError(null);
  }

  const failureMeta = selectedTask?.failure_type && failureTypesMeta?.[selectedTask.failure_type]
    ? failureTypesMeta[selectedTask.failure_type]
    : null;

  const pageContent = (
    <>
      <header className="page-header">
        <div>
          <p className="page-eyebrow">采集任务</p>
          <h1>智获客雷达</h1>
          <p className="page-description">创建采集任务、查看任务状态与统计、重跑失败任务。</p>
        </div>
      </header>

      {queueStatus && (
        <div className="queue-status-bar">
          <span className={`queue-status-dot${queueStatus.active_task_id ? "" : " idle"}`} />
          <span>
            {queueStatus.active_task_id
              ? `正在执行任务 #${queueStatus.active_task_id}`
              : "队列空闲"}
          </span>
          {queueStatus.queue_size > 0 && (
            <span>· 排队中 {queueStatus.queue_size} 个任务</span>
          )}
        </div>
      )}

      <section className="card">
        <div className="card-header">
          <h2>创建采集任务</h2>
          <p>通过 MediaCrawler 多平台采集，支持关键词、账号主页、指定帖子链接三种入口。</p>
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            采集平台
            <select
              value={form.platform}
              onChange={(event) => setForm((current) => ({ ...current, platform: event.target.value }))}
              disabled={submitting}
            >
              {PLATFORM_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label>
            采集类型
            <select
              value={form.sourceType}
              onChange={(event) => setForm((current) => ({ ...current, sourceType: event.target.value as SourceType }))}
              disabled={submitting}
            >
              {SOURCE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label>
            采集数量
            <input
              type="number"
              min={1}
              max={100}
              value={form.limitCount}
              onChange={(event) => {
                const value = Number.parseInt(event.target.value, 10);
                setForm((current) => ({ ...current, limitCount: Number.isNaN(value) ? 1 : Math.max(1, Math.min(100, value)) }));
              }}
              disabled={submitting}
            />
          </label>

          <label className="form-grid-span-2">
            采集目标
            <textarea
              className="text-area"
              value={form.sourceValue}
              onChange={(event) => setForm((current) => ({ ...current, sourceValue: event.target.value }))}
              placeholder={selectedOption?.hint ?? "请输入采集目标"}
              disabled={submitting}
            />
            <span className="field-hint">{selectedOption?.hint}</span>
          </label>

          <div className="form-actions form-grid-span-2">
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "提交中..." : "创建并运行采集"}
            </button>
          </div>
        </form>

        {formMessage ? (
          <div className="state-panel state-empty"><p>{formMessage}</p></div>
        ) : null}
        {formError ? (
          <div className="state-panel state-error"><p>{formError}</p></div>
        ) : null}
      </section>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>任务列表</h2>
            <p>展示任务状态、进度、采集结果{hasActiveTasks ? "（自动刷新中）" : ""}。</p>
          </div>
          <button type="button" className="btn-secondary" onClick={() => void loadTasks()} disabled={loading}>刷新列表</button>
        </div>

        {loading ? (
          <div style={{ display: "grid", gap: 8 }}>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton skeleton-card" />
            ))}
          </div>
        ) : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadTasks()}>重试</button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty"><p>暂无采集任务。请在上方创建第一个采集任务。</p></div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table className="task-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>来源类型</th>
                  <th>来源值</th>
                  <th>状态</th>
                  <th>帖子</th>
                  <th>评论</th>
                  <th>线索</th>
                  <th>同行</th>
                  <th>失败类型</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => {
                  const rerunDisabled = (task.status !== "failed" && task.status !== "success" && task.status !== "retrying") || busyId === task.id;
                  const isActive = task.status === "pending" || task.status === "running" || task.status === "retrying";
                  const failureLabel = task.failure_type && failureTypesMeta?.[task.failure_type]
                    ? failureTypesMeta[task.failure_type].label
                    : task.last_error_type ?? "-";
                  return (
                    <tr key={task.id} className={isActive ? "row-active" : ""}>
                      <td className="cell-mono">{task.id}</td>
                      <td><span className={platformBadgeClass(task.platform)}>{PLATFORM_LABELS[task.platform] || task.platform}</span></td>
                      <td>{SOURCE_TYPE_LABELS[task.source_type] || task.source_type}</td>
                      <td className="cell-break" title={task.source_value ?? ""}>{task.source_value ? (task.source_value.length > 20 ? task.source_value.slice(0, 20) + "…" : task.source_value) : "-"}</td>
                      <td>
                        <span className={statusClassName(task.status)}>
                          {statusText(task.status)}
                        </span>
                        {isActive && <span className="task-spinner" />}
                      </td>
                      <td>{task.post_count}</td>
                      <td>{task.comment_count}</td>
                      <td><strong>{task.lead_count}</strong></td>
                      <td>{task.discovered_competitor_count || "-"}</td>
                      <td>
                        {task.failure_type ? (
                          <span className="tag tag-danger" title={failureTypesMeta?.[task.failure_type]?.description}>{failureLabel}</span>
                        ) : "-"}
                      </td>
                      <td className="cell-time">{formatDateTime(task.started_at)}</td>
                      <td className="cell-time">{formatDateTime(task.finished_at)}</td>
                      <td>
                        <div className="action-row">
                          <button type="button" className="btn-sm" onClick={() => void handleViewTask(task.id)}>详情</button>
                          {task.status === "failed" && (
                            <button type="button" className="btn-sm btn-sm-danger" onClick={() => void handleRerun(task)} disabled={rerunDisabled}>
                              {busyId === task.id ? "重试中..." : "重试"}
                            </button>
                          )}
                          {task.status === "success" && (
                            <Link className="btn-sm btn-sm-success" to={`/leads?source_type=${task.source_type}`}>线索</Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {selectedTask && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal-content modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>任务 #{selectedTask.id} 详情</h2>
              <button type="button" className="modal-close" onClick={closeDetail}>✕</button>
            </div>

            {detailLoading ? (
              <div className="modal-body"><p className="state-text">加载中...</p></div>
            ) : detailError ? (
              <div className="modal-body"><p className="inline-error">{detailError}</p></div>
            ) : (
              <div className="modal-body">
                <div className="task-detail-section">
                  <h3 className="task-detail-section-title">基础信息</h3>
                  <div className="detail-grid compact">
                    <div><span>任务 ID</span><strong className="cell-mono">{selectedTask.id}</strong></div>
                    <div><span>来源名称</span><strong>{selectedTask.source_name}</strong></div>
                    <div><span>平台</span><strong><span className={platformBadgeClass(selectedTask.platform)}>{PLATFORM_LABELS[selectedTask.platform] || selectedTask.platform}</span></strong></div>
                    <div><span>状态</span><strong><span className={statusClassName(selectedTask.status)}>{statusText(selectedTask.status)}</span>{(selectedTask.status === "pending" || selectedTask.status === "running" || selectedTask.status === "retrying") && <span className="task-spinner" />}</strong></div>
                    <div><span>进度</span><strong>{progressText(selectedTask.progress)}</strong></div>
                    <div><span>重试次数</span><strong>{selectedTask.retry_count && selectedTask.retry_count > 0 ? <span className="tag tag-warning">{selectedTask.retry_count}/{selectedTask.max_retries ?? 3}</span> : "0"}</strong></div>
                    <div><span>开始时间</span><strong>{formatDateTime(selectedTask.started_at)}</strong></div>
                    <div><span>结束时间</span><strong>{formatDateTime(selectedTask.finished_at)}</strong></div>
                  </div>
                </div>

                <div className="task-detail-section">
                  <h3 className="task-detail-section-title">采集配置</h3>
                  <div className="detail-grid compact">
                    <div><span>来源类型</span><strong>{SOURCE_TYPE_LABELS[selectedTask.source_type] || selectedTask.source_type}</strong></div>
                    <div><span>来源值</span><strong className="cell-break">{selectedTask.source_value || "-"}</strong></div>
                    <div><span>采集数量</span><strong>{selectedTask.limit_count ?? "-"}</strong></div>
                    <div><span>来源 ID</span><strong>{selectedTask.source_id ?? "手动创建"}</strong></div>
                  </div>
                </div>

                <div className="task-detail-section">
                  <h3 className="task-detail-section-title">采集结果统计</h3>
                  <div className="task-result-stats">
                    <div className="task-result-stat">
                      <span className="task-result-stat-value">{selectedTask.post_count}</span>
                      <span className="task-result-stat-label">帖子</span>
                    </div>
                    <div className="task-result-stat">
                      <span className="task-result-stat-value">{selectedTask.comment_count}</span>
                      <span className="task-result-stat-label">评论</span>
                    </div>
                    <div className="task-result-stat task-result-stat-highlight">
                      <span className="task-result-stat-value">{selectedTask.lead_count}</span>
                      <span className="task-result-stat-label">线索</span>
                    </div>
                    <div className="task-result-stat">
                      <span className="task-result-stat-value">{selectedTask.discovered_competitor_count}</span>
                      <span className="task-result-stat-label">同行发现</span>
                    </div>
                    <div className="task-result-stat">
                      <span className="task-result-stat-value">{selectedTask.duplicate_post_count}</span>
                      <span className="task-result-stat-label">重复帖子</span>
                    </div>
                    <div className="task-result-stat">
                      <span className="task-result-stat-value">{selectedTask.duplicate_comment_count}</span>
                      <span className="task-result-stat-label">重复评论</span>
                    </div>
                  </div>
                </div>

                {selectedTask.status === "failed" && (
                  <div className="task-detail-section">
                    <h3 className="task-detail-section-title">错误信息与修复建议</h3>
                    <div className="task-error-box">
                      {selectedTask.failure_type && (
                        <div className="task-error-type">
                          <span className="tag tag-danger">{failureMeta?.label ?? selectedTask.failure_type}</span>
                        </div>
                      )}
                      {selectedTask.error_message && (
                        <div className="task-error-message">
                          <strong>错误详情：</strong>
                          <p>{selectedTask.error_message}</p>
                        </div>
                      )}
                      {failureMeta && (
                        <div className="task-error-suggestion">
                          <div className="task-error-suggestion-desc">
                            <strong>原因分析：</strong>{failureMeta.description}
                          </div>
                          <div className="task-error-suggestion-action">
                            💡 <strong>建议处理：</strong>{failureMeta.suggestion}
                          </div>
                        </div>
                      )}
                      <div className="task-error-actions">
                        <button
                          type="button"
                          className="btn-primary"
                          disabled={busyId === selectedTask.id}
                          onClick={() => void handleRerun(selectedTask)}
                        >
                          {busyId === selectedTask.id ? "重试中..." : "🔄 重试采集"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {selectedTask.status === "success" && (
                  <div className="task-detail-section">
                    <h3 className="task-detail-section-title">快捷操作</h3>
                    <div className="task-quick-actions">
                      <Link className="task-quick-action-btn" to={`/posts?source_type=${selectedTask.source_type}`}>
                        <span className="task-quick-action-icon">📄</span>
                        <strong>查看帖子</strong>
                        <span>{selectedTask.post_count} 条帖子</span>
                      </Link>
                      <Link className="task-quick-action-btn" to={`/comments?platform=${selectedTask.platform}`}>
                        <span className="task-quick-action-icon">💬</span>
                        <strong>查看评论</strong>
                        <span>{selectedTask.comment_count} 条评论</span>
                      </Link>
                      <Link className="task-quick-action-btn" to={`/leads?source_type=${selectedTask.source_type}`}>
                        <span className="task-quick-action-icon">🎯</span>
                        <strong>查看线索</strong>
                        <span>{selectedTask.lead_count} 条线索</span>
                      </Link>
                      <button
                        type="button"
                        className="task-quick-action-btn"
                        disabled={generatingReport}
                        onClick={() => void handleGenerateReport()}
                      >
                        <span className="task-quick-action-icon">📊</span>
                        <strong>{generatingReport ? "生成中..." : "生成日报"}</strong>
                        <span>今日获客报告</span>
                      </button>
                    </div>
                  </div>
                )}

                {(selectedTask.status === "pending" || selectedTask.status === "running" || selectedTask.status === "retrying") && (
                  <div className="task-detail-section">
                    <h3 className="task-detail-section-title">执行状态</h3>
                    <div className="task-running-status">
                      <div className="task-running-spinner" />
                      <div>
                        <strong>
                          {selectedTask.status === "pending" && "任务排队中，等待执行..."}
                          {selectedTask.status === "running" && `任务运行中 — ${progressText(selectedTask.progress)}`}
                          {selectedTask.status === "retrying" && `正在重试（第 ${selectedTask.retry_count} 次）...`}
                        </strong>
                        <p>页面将自动刷新状态，任务完成后会弹出通知。</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );

  if (embedded) return pageContent;
  return <main className="page-shell">{pageContent}</main>;
}
