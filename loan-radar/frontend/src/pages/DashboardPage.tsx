import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  type DashboardStats,
  type MediaCrawlerHealth,
  type QueueStatus,
  getDashboardStats,
  getMediaCrawlerHealth,
  getQueueStatus,
  generateDailyReport,
  exportLeadsCsv,
} from "../api/client";
import { showToast } from "../components/ToastContainer";

const PLATFORM_LABELS: Record<string, string> = {
  xhs: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
  all: "全平台",
};

function formatTimeAgo(value: string | null | undefined) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const diff = Date.now() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `${days}天前`;
}

function statusLabel(status: string) {
  const m: Record<string, string> = {
    pending: "排队中",
    running: "运行中",
    success: "成功",
    failed: "失败",
    retrying: "重试中",
  };
  return m[status] ?? status;
}

function statusPillClass(status: string) {
  return `status-pill status-${status}`;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [mcHealth, setMcHealth] = useState<MediaCrawlerHealth | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);
  const navigate = useNavigate();

  const notifiedStatusRef = useRef<Map<number, string>>(new Map());

  const loadAll = useCallback(async () => {
    try {
      const [dashboardData, healthData, queueData] = await Promise.all([
        getDashboardStats(),
        getMediaCrawlerHealth().catch(() => null),
        getQueueStatus().catch(() => null),
      ]);
      setStats(dashboardData);
      setMcHealth(healthData);
      setQueueStatus(queueData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    const interval = setInterval(() => {
      void (async () => {
        try {
          const data = await getDashboardStats();
          setStats(data);

          const notified = notifiedStatusRef.current;
          for (const task of data.recent_tasks) {
            const prevStatus = notified.get(task.id);
            if (prevStatus === task.status) continue;
            if (prevStatus != null) {
              if (task.status === "success") {
                showToast("success", `任务 #${task.id} 采集完成`, `获得 ${task.post_count} 帖子、${task.lead_count} 线索`);
              } else if (task.status === "failed") {
                showToast("error", `任务 #${task.id} 采集失败`, task.error_message?.slice(0, 100) || "未知错误");
              }
            }
            notified.set(task.id, task.status);
          }

          const q = await getQueueStatus().catch(() => null);
          if (q) setQueueStatus(q);
        } catch {}
      })();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  async function handleGenerateReport() {
    setGeneratingReport(true);
    try {
      await generateDailyReport();
      showToast("success", "报告已生成", "今日获客报告已生成，可前往日报页面查看");
    } catch (err) {
      showToast("error", "生成失败", err instanceof Error ? err.message : "未知错误");
    } finally {
      setGeneratingReport(false);
    }
  }

  async function handleExportCsv() {
    setExportingCsv(true);
    try {
      const blob = await exportLeadsCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `loan-radar-leads-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("success", "导出成功", "线索 CSV 已下载");
    } catch (err) {
      showToast("error", "导出失败", err instanceof Error ? err.message : "未知错误");
    } finally {
      setExportingCsv(false);
    }
  }

  const mcIsDown = mcHealth && mcHealth.status !== "healthy";

  const isEmpty = stats && stats.lead_count === 0 && stats.post_count === 0 && stats.comment_count === 0 && stats.task_count === 0;

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Customer Acquisition Cockpit</p>
          <h1>获客驾驶舱</h1>
          <p className="page-description">实时掌握今日获客数据，快速驱动业务动作。</p>
        </div>
      </header>

      {mcIsDown && (
        <div className="cockpit-alert cockpit-alert-warning">
          <span className="cockpit-alert-icon">⚠️</span>
          <div>
            <strong>MediaCrawler 未连接</strong>
            <p>当前采集引擎{mcHealth.mode === "embedded" ? "（内嵌模式）" : "（HTTP 桥接模式）"}不可用，实时采集功能受限。请检查服务状态或使用演示模式。</p>
          </div>
          <Link to="/monitor-sources" className="btn btn-secondary" style={{ marginLeft: "auto", whiteSpace: "nowrap" }}>检查配置</Link>
        </div>
      )}

      {queueStatus && (
        <div className="queue-status-bar">
          <span className={`queue-status-dot${queueStatus.active_task_id ? "" : " idle"}`} />
          <span>
            {queueStatus.active_task_id
              ? `正在执行任务 #${queueStatus.active_task_id}`
              : "采集队列空闲"}
          </span>
          {queueStatus.queue_size > 0 && (
            <span>· 排队中 {queueStatus.queue_size} 个任务</span>
          )}
        </div>
      )}

      {loading && (
        <section className="cockpit-metrics">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="cockpit-metric-card">
              <div className="skeleton skeleton-text" style={{ width: "50%" }} />
              <div className="skeleton skeleton-title" style={{ width: "40%" }} />
            </div>
          ))}
        </section>
      )}

      {error && (
        <div className="state-panel state-error">
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={() => { setError(null); setLoading(true); void loadAll(); }} style={{ marginLeft: "auto" }}>重试</button>
        </div>
      )}

      {!loading && stats && (
        <>
          <section className="cockpit-metrics">
            <div className="cockpit-metric-card">
              <span className="cockpit-metric-label">监控源</span>
              <strong className="cockpit-metric-value">{stats.source_count}</strong>
              <span className="cockpit-metric-unit">个</span>
            </div>
            <div className="cockpit-metric-card">
              <span className="cockpit-metric-label">采集任务</span>
              <strong className="cockpit-metric-value">{stats.task_count}</strong>
              <span className="cockpit-metric-unit">个</span>
            </div>
            <div className="cockpit-metric-card">
              <span className="cockpit-metric-label">帖子</span>
              <strong className="cockpit-metric-value">{stats.post_count}</strong>
              <span className="cockpit-metric-unit">条</span>
            </div>
            <div className="cockpit-metric-card">
              <span className="cockpit-metric-label">评论</span>
              <strong className="cockpit-metric-value">{stats.comment_count}</strong>
              <span className="cockpit-metric-unit">条</span>
            </div>
            <div className="cockpit-metric-card">
              <span className="cockpit-metric-label">线索</span>
              <strong className="cockpit-metric-value">{stats.lead_count}</strong>
              <span className="cockpit-metric-unit">条</span>
            </div>
            <div className="cockpit-metric-card cockpit-metric-highlight">
              <span className="cockpit-metric-label">A级线索</span>
              <strong className="cockpit-metric-value">{stats.a_lead_count}</strong>
              <span className="cockpit-metric-unit">条</span>
            </div>
            <div className="cockpit-metric-card cockpit-metric-warning">
              <span className="cockpit-metric-label">待审核同行</span>
              <strong className="cockpit-metric-value">{stats.pending_competitor_count}</strong>
              <span className="cockpit-metric-unit">个</span>
            </div>
          </section>

          {isEmpty && (
            <div className="cockpit-empty-guide">
              <div className="cockpit-empty-icon">📡</div>
              <h3>尚未开始采集</h3>
              <p>当前没有今日数据。创建监控源并启动采集，系统将自动识别线索。</p>
              <div className="cockpit-empty-actions">
                <Link to="/monitor-sources" className="btn btn-primary">新建监控源</Link>
                <Link to="/crawl-tasks" className="btn btn-secondary">查看采集任务</Link>
              </div>
            </div>
          )}

          <div className="cockpit-grid">
            <section className="cockpit-panel">
              <div className="cockpit-panel-header">
                <h2>⭐ 最近A级线索</h2>
                <Link to="/leads?lead_level=A">查看全部</Link>
              </div>
              {stats.recent_a_leads.length === 0 ? (
                <div className="cockpit-panel-empty">
                  <p>暂无A级线索</p>
                  <span>启动采集后，高分线索将自动出现在这里</span>
                </div>
              ) : (
                <div className="cockpit-lead-list">
                  {stats.recent_a_leads.map((lead) => (
                    <Link key={lead.id} to="/leads" className="cockpit-lead-item" style={{ textDecoration: "none", color: "inherit" }}>
                      <div className="cockpit-lead-main">
                        <div className="cockpit-lead-top">
                          <span className={`platform-badge platform-${lead.platform}`}>
                            {PLATFORM_LABELS[lead.platform] || lead.platform}
                          </span>
                          <span className="cockpit-lead-score">评分 {lead.lead_score}</span>
                          {lead.demand_type && <span className="tag">{lead.demand_type}</span>}
                        </div>
                        <div className="cockpit-lead-user">{lead.user_name || "匿名用户"}</div>
                        <div className="cockpit-lead-content">{lead.content}</div>
                        {lead.follow_up_script && (
                          <div className="cockpit-lead-script">
                            💬 {lead.follow_up_script.slice(0, 60)}{lead.follow_up_script.length > 60 ? "..." : ""}
                          </div>
                        )}
                      </div>
                      <span className="cockpit-lead-time">{formatTimeAgo(lead.created_at)}</span>
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <section className="cockpit-panel">
              <div className="cockpit-panel-header">
                <h2>⚙️ 采集任务状态</h2>
                <Link to="/crawl-tasks">查看全部</Link>
              </div>
              {stats.recent_tasks.length === 0 ? (
                <div className="cockpit-panel-empty">
                  <p>暂无采集任务</p>
                  <span>创建监控源并启动采集</span>
                </div>
              ) : (
                <div className="cockpit-task-list">
                  {stats.recent_tasks.map((task) => (
                    <Link key={task.id} to="/crawl-tasks" className="cockpit-task-item" style={{ textDecoration: "none", color: "inherit" }}>
                      <div className="cockpit-task-info">
                        <span className="cockpit-task-label">
                          #{task.id} · {PLATFORM_LABELS[task.platform] || task.platform} · {task.source_type}
                        </span>
                        <span className="cockpit-task-meta">
                          {task.source_value?.slice(0, 30) || "-"}
                          {task.started_at ? ` · ${formatTimeAgo(task.started_at)}` : ""}
                        </span>
                      </div>
                      <div className="cockpit-task-right">
                        {task.status === "success" && (
                          <span className="cockpit-task-counts">
                            {task.post_count}帖 {task.comment_count}评 {task.lead_count}线索
                          </span>
                        )}
                        <span className={statusPillClass(task.status)}>
                          {statusLabel(task.status)}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </div>

          <section className="cockpit-panel" style={{ marginTop: 20 }}>
            <div className="cockpit-panel-header">
              <h2>🚀 快捷操作</h2>
            </div>
            <div className="cockpit-actions">
              <button className="cockpit-action-btn" onClick={() => navigate("/monitor-sources")}>
                <span className="cockpit-action-icon">📡</span>
                <div>
                  <strong>新建监控源</strong>
                  <span>配置关键词或账号监控</span>
                </div>
              </button>
              <button className="cockpit-action-btn" onClick={() => navigate("/crawl-tasks")}>
                <span className="cockpit-action-icon">▶️</span>
                <div>
                  <strong>立即采集</strong>
                  <span>启动采集任务获取数据</span>
                </div>
              </button>
              <button className="cockpit-action-btn" onClick={() => navigate("/leads")}>
                <span className="cockpit-action-icon">⭐</span>
                <div>
                  <strong>查看线索池</strong>
                  <span>浏览和管理所有线索</span>
                </div>
              </button>
              <button className="cockpit-action-btn" onClick={handleGenerateReport} disabled={generatingReport}>
                <span className="cockpit-action-icon">📊</span>
                <div>
                  <strong>{generatingReport ? "生成中..." : "生成今日报告"}</strong>
                  <span>一键生成获客日报</span>
                </div>
              </button>
              <button className="cockpit-action-btn" onClick={handleExportCsv} disabled={exportingCsv}>
                <span className="cockpit-action-icon">📥</span>
                <div>
                  <strong>{exportingCsv ? "导出中..." : "导出线索 CSV"}</strong>
                  <span>下载线索数据表格</span>
                </div>
              </button>
            </div>
          </section>

          {mcHealth && mcHealth.status === "healthy" && (
            <div className="cockpit-health-bar">
              <span className="cockpit-health-dot" />
              <span>MediaCrawler 正常运行 · {mcHealth.mode === "embedded" ? "内嵌模式" : "HTTP 桥接模式"}</span>
              {mcHealth.supported_platforms.length > 0 && (
                <span className="cockpit-health-platforms">
                  · 支持 {mcHealth.supported_platforms.map((p) => p.label).join("、")}
                </span>
              )}
            </div>
          )}
        </>
      )}
    </main>
  );
}
