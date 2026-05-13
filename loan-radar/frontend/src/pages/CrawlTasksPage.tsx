import { useEffect, useMemo, useState } from "react";

import {
  getCrawlTask,
  getCrawlTasks,
  getMonitorSources,
  rerunCrawlTask,
  type CrawlTask,
  type MonitorSource,
} from "../api/client";

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

type CrawlTaskView = CrawlTask & {
  source_name: string;
};

export default function CrawlTasksPage() {
  const [tasks, setTasks] = useState<CrawlTaskView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [selectedTask, setSelectedTask] = useState<CrawlTaskView | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

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
            task.source_id == null ? "collection_tasks_api" : sourceNameMap.get(task.source_id)?.name ?? `监控源 #${task.source_id}`,
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

  async function handleViewTask(taskId: number) {
    setDetailLoading(true);
    setDetailError(null);

    try {
      const task = await getCrawlTask(taskId);
      const sourceName =
        tasks.find((item) => item.id === taskId)?.source_name ??
        (task.source_id == null ? "collection_tasks_api" : `监控源 #${task.source_id}`);
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
          <p className="page-eyebrow">采集任务中心</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看采集任务状态、结果统计和失败原因，支持对失败任务直接重跑。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>采集任务列表</h2>
            <p>展示任务状态、帖子数、评论数、线索数和同行发现数。</p>
          </div>
          <button type="button" onClick={() => void loadTasks()} disabled={loading}>
            刷新列表
          </button>
        </div>

        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadTasks()}>
              重试
            </button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty">
            <p>暂无采集任务。</p>
          </div>
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
                  <th>发现同行数</th>
                  <th>失败原因</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => {
                  const rerunDisabled = task.status !== "failed" || busyId === task.id;
                  const sourceName = task.source_name;

                  return (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.source_type}</td>
                      <td className="cell-break">{sourceName}</td>
                      <td>{task.platform}</td>
                      <td>
                        <span className={statusClassName(task.status)}>{statusText(task.status)}</span>
                      </td>
                      <td>{task.post_count}</td>
                      <td>{task.comment_count}</td>
                      <td>{task.lead_count}</td>
                      <td>{task.discovered_competitor_count}</td>
                      <td className="cell-break">{task.error_message || "-"}</td>
                      <td>{formatDateTime(task.started_at)}</td>
                      <td>{formatDateTime(task.finished_at)}</td>
                      <td>
                        <div className="action-row">
                          <button type="button" onClick={() => void handleViewTask(task.id)}>
                            查看
                          </button>
                          <button type="button" onClick={() => void handleRerun(task)} disabled={rerunDisabled}>
                            {busyId === task.id ? "重跑中..." : "重跑失败任务"}
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
          <p>点击“查看”后展示当前任务状态与统计。</p>
        </div>

        {detailLoading ? <p className="state-text">详情加载中...</p> : null}
        {detailError ? <p className="inline-error">{detailError}</p> : null}
        {!detailLoading && !detailError && selectedTask ? (
          <div className="detail-grid">
            <div>
              <span>任务 ID</span>
              <strong>{selectedTask.id}</strong>
            </div>
            <div>
              <span>来源名称</span>
              <strong>{selectedTask.source_name}</strong>
            </div>
            <div>
              <span>状态</span>
              <strong>{statusText(selectedTask.status)}</strong>
            </div>
            <div>
              <span>失败原因</span>
              <strong>{selectedTask.error_message || "-"}</strong>
            </div>
            <div>
              <span>帖子数</span>
              <strong>{selectedTask.post_count}</strong>
            </div>
            <div>
              <span>评论数</span>
              <strong>{selectedTask.comment_count}</strong>
            </div>
            <div>
              <span>线索数</span>
              <strong>{selectedTask.lead_count}</strong>
            </div>
            <div>
              <span>发现同行数</span>
              <strong>{selectedTask.discovered_competitor_count}</strong>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
