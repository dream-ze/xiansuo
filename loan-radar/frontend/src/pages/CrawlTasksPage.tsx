import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createCollectionTask,
  getCrawlTask,
  getCrawlTasks,
  getMonitorSources,
  rerunCrawlTask,
  runCollectionTask,
  type CrawlTask,
  type CollectionTaskCreatePayload,
  type MonitorSource,
} from "../api/client";

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
  { label: "快手", value: "kuaishou" },
  { label: "B站", value: "bilibili" },
  { label: "微博", value: "weibo" },
  { label: "贴吧", value: "tieba" },
  { label: "知乎", value: "zhihu" },
];

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType; label: string; hint: string }> = [
  { value: "keyword", label: "关键词采集", hint: "输入关键词，例如：征信花了" },
  { value: "account", label: "同行账号采集", hint: "输入账号主页 URL" },
  { value: "post_url", label: "指定帖子采集", hint: "输入帖子 URL" },
];

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
  };
  return mapping[status] ?? status;
}

function statusClassName(status: string) {
  return `status-pill status-${status}`;
}

type CrawlTaskView = CrawlTask & {
  source_name: string;
};

export default function CrawlTasksPage() {
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

  const selectedOption = useMemo(
    () => SOURCE_TYPE_OPTIONS.find((option) => option.value === form.sourceType),
    [form.sourceType],
  );

  async function loadTasks() {
    setLoading(true);
    setError(null);

    try {
      const [taskResult, sources] = await Promise.all([getCrawlTasks(), getMonitorSources()]);
      const sourceNameMap = new Map<number, MonitorSource>(sources.map((source) => [source.id, source]));
      setTasks(
        taskResult.items.map((task) => ({
          ...task,
          source_name:
            task.source_id == null ? "手动创建" : sourceNameMap.get(task.source_id)?.name ?? `监控源 #${task.source_id}`,
        })),
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载采集任务失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
  }, []);

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
      const ran = await runCollectionTask(created.id);
      setFormMessage(`任务 #${ran.id} 已创建并运行，当前状态：${statusText(ran.status)}`);
      setForm((current) => ({ ...current, sourceValue: "" }));
      await loadTasks();
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : "创建采集任务失败");
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
      await loadTasks();
      if (selectedTask?.id === task.id) {
        await handleViewTask(task.id);
      }
    } catch (rerunError) {
      setDetailError(rerunError instanceof Error ? rerunError.message : "重跑失败任务失败");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">采集任务</p>
          <h1>智获客雷达</h1>
          <p className="page-description">创建采集任务、查看任务状态与统计、重跑失败任务。</p>
        </div>
      </header>

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
            <button type="submit" disabled={submitting}>
              {submitting ? "运行中..." : "创建并运行采集"}
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
            <p>展示任务状态、帖子数、评论数、线索数和同行发现数。</p>
          </div>
          <button type="button" onClick={() => void loadTasks()} disabled={loading}>刷新列表</button>
        </div>

        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadTasks()}>重试</button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty"><p>暂无采集任务。</p></div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务 ID</th>
                  <th>来源类型</th>
                  <th>来源名称</th>
                  <th>平台</th>
                  <th>状态</th>
                  <th>帖子数</th>
                  <th>评论数</th>
                  <th>线索数</th>
                  <th>发现同行</th>
                  <th>失败原因</th>
                  <th>开始时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => {
                  const rerunDisabled = task.status !== "failed" || busyId === task.id;
                  return (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.source_type}</td>
                      <td className="cell-break">{task.source_name}</td>
                      <td>{task.platform}</td>
                      <td><span className={statusClassName(task.status)}>{statusText(task.status)}</span></td>
                      <td>{task.post_count}</td>
                      <td>{task.comment_count}</td>
                      <td>{task.lead_count}</td>
                      <td>{task.discovered_competitor_count}</td>
                      <td className="cell-break">{task.error_message || "-"}</td>
                      <td>{formatDateTime(task.started_at)}</td>
                      <td>
                        <div className="action-row">
                          <button type="button" onClick={() => void handleViewTask(task.id)}>查看</button>
                          <button type="button" onClick={() => void handleRerun(task)} disabled={rerunDisabled}>
                            {busyId === task.id ? "重跑中..." : "重跑"}
                          </button>
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

      <section className="card detail-card">
        <div className="card-header">
          <h2>任务详情</h2>
          <p>点击"查看"后展示当前任务状态与统计。</p>
        </div>

        {detailLoading ? <p className="state-text">详情加载中...</p> : null}
        {detailError ? <p className="inline-error">{detailError}</p> : null}
        {!detailLoading && !detailError && selectedTask ? (
          <div className="detail-grid">
            <div><span>任务 ID</span><strong>{selectedTask.id}</strong></div>
            <div><span>来源名称</span><strong>{selectedTask.source_name}</strong></div>
            <div><span>状态</span><strong>{statusText(selectedTask.status)}</strong></div>
            <div><span>失败原因</span><strong>{selectedTask.error_message || "-"}</strong></div>
            <div><span>帖子数</span><strong>{selectedTask.post_count}</strong></div>
            <div><span>评论数</span><strong>{selectedTask.comment_count}</strong></div>
            <div><span>线索数</span><strong>{selectedTask.lead_count}</strong></div>
            <div><span>发现同行数</span><strong>{selectedTask.discovered_competitor_count}</strong></div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
