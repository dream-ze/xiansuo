import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  checkXhsLogin,
  createCollectionTask,
  getCollectionTasks,
  getXhsAuthStatus,
  logoutXhs,
  refreshXhsQrcode,
  restartXhsBrowser,
  runCollectionTask,
  startXhsLogin,
  type CrawlTask,
  type CollectionTaskCreatePayload,
  type XhsAuthStatus,
  type XhsLoginResponse,
} from "../api/client";

type SourceType = "keyword" | "account" | "post_url";

type FormState = {
  sourceType: SourceType;
  sourceValue: string;
  limitCount: number;
};

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType; label: string; hint: string }> = [
  { value: "keyword", label: "关键词采集", hint: "输入关键词，例如：征信花了" },
  { value: "account", label: "同行账号采集", hint: "输入小红书账号主页 URL" },
  { value: "post_url", label: "指定帖子采集", hint: "输入小红书笔记 URL" },
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
  const [form, setForm] = useState<FormState>({ sourceType: "keyword", sourceValue: "", limitCount: 5 });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<CrawlTask | null>(null);

  const [authStatus, setAuthStatus] = useState<XhsAuthStatus | null>(null);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginPolling, setLoginPolling] = useState(false);

  const selectedOption = useMemo(
    () => SOURCE_TYPE_OPTIONS.find((option) => option.value === form.sourceType),
    [form.sourceType],
  );

  async function loadAuthStatus() {
    try {
      const status = await getXhsAuthStatus();
      setAuthStatus(status);
    } catch {
      setAuthStatus(null);
    }
  }

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
      setError(loadError instanceof Error ? loadError.message : "加载真实采集任务失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
    void loadAuthStatus();
  }, []);

  useEffect(() => {
    if (!loginPolling) return;
    const interval = setInterval(async () => {
      try {
        const result = await checkXhsLogin();
        if (result.logged_in) {
          setLoginPolling(false);
          setQrCode(null);
          await loadAuthStatus();
        }
      } catch {
        // continue polling
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [loginPolling]);

  async function handleStartLogin() {
    setLoginLoading(true);
    setLoginError(null);
    setQrCode(null);
    try {
      const result: XhsLoginResponse = await startXhsLogin(false);
      if (result.logged_in) {
        await loadAuthStatus();
        return;
      }
      if (result.qr_code) {
        setQrCode(result.qr_code);
        setLoginPolling(true);
      }
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "启动登录失败");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleRefreshQr() {
    setLoginLoading(true);
    setLoginError(null);
    try {
      const result = await refreshXhsQrcode();
      if (result.qr_code) {
        setQrCode(result.qr_code);
      }
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "刷新二维码失败");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleLogout() {
    setLoginLoading(true);
    try {
      await logoutXhs();
      setAuthStatus(null);
      setQrCode(null);
      setLoginPolling(false);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "登出失败");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleRestart() {
    setLoginLoading(true);
    setLoginError(null);
    try {
      const status = await restartXhsBrowser(false);
      setAuthStatus(status);
      setQrCode(null);
      setLoginPolling(false);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "重启浏览器失败");
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);

    const payload: CollectionTaskCreatePayload = {
      platform: "xhs",
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
          <p className="page-description">通过 /api/collection/tasks 创建并执行真实采集任务，覆盖关键词、账号主页、指定笔记链接三种入口。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header">
          <h2>XHS 浏览器登录状态</h2>
          <p>CDP 模式需要先登录小红书，浏览器会自动获取签名参数（x-s, x-t）</p>
        </div>

        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 300px", minWidth: 260 }}>
            {authStatus ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 14 }}>
                <div>
                  <span style={{ color: "#888" }}>浏览器状态：</span>
                  <strong style={{ color: authStatus.started ? "#16a34a" : "#dc2626" }}>
                    {authStatus.started ? "已启动" : "未启动"}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "#888" }}>登录状态：</span>
                  <strong style={{ color: authStatus.logged_in ? "#16a34a" : "#dc2626" }}>
                    {authStatus.logged_in ? "已登录" : "未登录"}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "#888" }}>签名可用：</span>
                  <strong style={{ color: authStatus.sign_available ? "#16a34a" : "#dc2626" }}>
                    {authStatus.sign_available ? "是" : "否"}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "#888" }}>无头模式：</span>
                  <strong>{authStatus.headless ? "是" : "否（有界面）"}</strong>
                </div>
              </div>
            ) : (
              <p style={{ color: "#888" }}>正在获取状态...</p>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
              {!authStatus?.logged_in ? (
                <button type="button" disabled={loginLoading} onClick={() => void handleStartLogin()}>
                  {loginLoading ? "启动中..." : "启动登录（扫码）"}
                </button>
              ) : null}
              {qrCode && !authStatus?.logged_in ? (
                <button type="button" disabled={loginLoading} onClick={() => void handleRefreshQr()}>
                  刷新二维码
                </button>
              ) : null}
              {authStatus?.logged_in ? (
                <button type="button" disabled={loginLoading} onClick={() => void handleLogout()}>
                  退出登录
                </button>
              ) : null}
              <button type="button" disabled={loginLoading} onClick={() => void handleRestart()}>
                重启浏览器
              </button>
            </div>

            {loginPolling && !authStatus?.logged_in ? (
              <p style={{ marginTop: 8, color: "#2563eb", fontSize: 13 }}>等待扫码登录中...</p>
            ) : null}
            {loginError ? (
              <p style={{ marginTop: 8, color: "#dc2626", fontSize: 13 }}>{loginError}</p>
            ) : null}
          </div>

          {qrCode && !authStatus?.logged_in ? (
            <div style={{ flex: "0 0 auto" }}>
              <img
                src={qrCode}
                alt="XHS Login QR Code"
                style={{ width: 200, height: 200, border: "1px solid #e5e7eb", borderRadius: 8 }}
              />
              <p style={{ textAlign: "center", fontSize: 12, color: "#888", marginTop: 4 }}>
                打开小红书 App 扫码登录
              </p>
            </div>
          ) : null}
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>创建并运行采集</h2>
          <p>点击后会顺序调用：POST /api/collection/tasks，然后 POST /api/collection/tasks/{"{task_id}"}/run</p>
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
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
