import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createCollectionTask,
  getCollectionTasks,
  runCollectionTask,
  type CrawlTask,
  type CollectionTaskCreatePayload,
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
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
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

export default function RealCollectionTasksPage() {
  const [form, setForm] = useState<FormState>({
    sourceType: "keyword",
    sourceValue: "",
    platform: "xhs",
    limitCount: 5,
  });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<CrawlTask | null>(null);

  const selectedOption = useMemo(
    () => SOURCE_TYPE_OPTIONS.find((option) => option.value === form.sourceType),
    [form.sourceType],
  );

  async function loadTasks() {
    setLoading(true);
    setError(null);
    try {
      const data = await getCollectionTasks({ page: 1, page_size: 20 });
      setTasks(data.items);
      setSelectedTask((current) => {
        if (!current) {
          return data.items[0] ?? null;
        }
        return data.items.find((task) => task.id === current.id) ?? data.items[0] ?? null;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载采集任务失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);

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
      setSelectedTask(ran);
      setMessage(`任务 #${ran.id} 已创建并运行，当前状态：${statusText(ran.status)}`);
      await loadTasks();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "创建并运行采集任务失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">真实采集入口</p>
          <h1>真实采集任务</h1>
          <p className="page-description">
            通过 MediaCrawler 创建并执行真实采集任务，支持多平台（小红书/抖音/快手/B站/微博/贴吧/知乎），
            覆盖关键词、账号主页、指定帖子链接三种入口。
          </p>
        </div>
      </header>

      <section className="card">
        <div className="card-header">
          <h2>创建并运行采集</h2>
          <p>基于 MediaCrawler 多平台采集，点击后会顺序调用：POST /api/collection/tasks，然后 POST /api/collection/tasks/{"{task_id}"}/run</p>
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            采集平台
            <select
              value={form.platform}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  platform: event.target.value,
                }))
              }
              disabled={submitting}
            >
              {PLATFORM_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            采集类型
            <select
              value={form.sourceType}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  sourceType: event.target.value as SourceType,
                }))
              }
              disabled={submitting}
            >
              {SOURCE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            limit_count
            <input
              type="number"
              min={1}
              max={100}
              value={form.limitCount}
              onChange={(event) => {
                const value = Number.parseInt(event.target.value, 10);
                setForm((current) => ({
                  ...current,
                  limitCount: Number.isNaN(value) ? 1 : Math.max(1, Math.min(100, value)),
                }));
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

        {message ? (
          <div className="state-panel state-empty">
            <p>{message}</p>
          </div>
        ) : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
          </div>
        ) : null}
      </section>

      <section className="card detail-card">
        <div className="card-header card-header-row">
          <div>
            <h2>真实采集任务列表</h2>
            <p>展示 status、collected_posts、collected_comments、post_count、comment_count、lead_count、discovered_competitor_count、error_message。</p>
          </div>
          <button type="button" disabled={loading} onClick={() => void loadTasks()}>
            刷新
          </button>
        </div>

        {loading ? <p className="state-text">加载中...</p> : null}

        {!loading && tasks.length === 0 ? (
          <div className="state-panel state-empty">
            <p>暂无真实采集任务。</p>
          </div>
        ) : null}

        {!loading && tasks.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务 ID</th>
                  <th>platform</th>
                  <th>source_type</th>
                  <th>source_value</th>
                  <th>status</th>
                  <th>collected_posts</th>
                  <th>collected_comments</th>
                  <th>post_count</th>
                  <th>comment_count</th>
                  <th>lead_count</th>
                  <th>discovered_competitor_count</th>
                  <th>error_message</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id} onClick={() => setSelectedTask(task)}>
                    <td>{task.id}</td>
                    <td>{task.platform}</td>
                    <td>{task.source_type}</td>
                    <td className="cell-break">{task.source_value || "-"}</td>
                    <td>
                      <span className={statusClassName(task.status)}>{statusText(task.status)}</span>
                    </td>
                    <td>{task.collected_posts ?? 0}</td>
                    <td>{task.collected_comments ?? 0}</td>
                    <td>{task.post_count}</td>
                    <td>{task.comment_count}</td>
                    <td>{task.lead_count}</td>
                    <td>{task.discovered_competitor_count}</td>
                    <td className="cell-break">{task.error_message || "-"}</td>
                    <td>{formatDateTime(task.started_at)}</td>
                    <td>{formatDateTime(task.finished_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {selectedTask ? (
        <section className="card detail-card">
          <div className="card-header">
            <h2>当前任务详情</h2>
            <p>任务 #{selectedTask.id}</p>
          </div>
          <div className="detail-grid">
            <div>
              <span>platform</span>
              <strong>{selectedTask.platform}</strong>
            </div>
            <div>
              <span>status</span>
              <strong>{selectedTask.status}</strong>
            </div>
            <div>
              <span>collected_posts</span>
              <strong>{selectedTask.collected_posts ?? 0}</strong>
            </div>
            <div>
              <span>collected_comments</span>
              <strong>{selectedTask.collected_comments ?? 0}</strong>
            </div>
            <div>
              <span>post_count</span>
              <strong>{selectedTask.post_count}</strong>
            </div>
            <div>
              <span>comment_count</span>
              <strong>{selectedTask.comment_count}</strong>
            </div>
            <div>
              <span>lead_count</span>
              <strong>{selectedTask.lead_count}</strong>
            </div>
            <div>
              <span>discovered_competitor_count</span>
              <strong>{selectedTask.discovered_competitor_count}</strong>
            </div>
            <div>
              <span>error_message</span>
              <strong>{selectedTask.error_message || "-"}</strong>
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}
