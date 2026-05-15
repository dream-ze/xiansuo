import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  getCrawlTasks,
  getLeads,
  getPosts,
  getComments,
  getQueueStatus,
  type CrawlTask,
  type QueueStatus,
} from "../api/client";
import { showToast } from "../components/ToastContainer";

type DashboardStats = {
  totalLeads: number;
  aLeads: number;
  bLeads: number;
  totalPosts: number;
  totalComments: number;
  newLeads: number;
  contactedLeads: number;
  convertedLeads: number;
};

const PLATFORM_LABELS: Record<string, string> = {
  xhs: "小红书",
  douyin: "抖音",
  kuaishou: "快手",
  bilibili: "B站",
  weibo: "微博",
  tieba: "贴吧",
  zhihu: "知乎",
  other: "其他",
};

function formatTimeAgo(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const diff = Date.now() - date.getTime();
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
  const [stats, setStats] = useState<DashboardStats>({
    totalLeads: 0,
    aLeads: 0,
    bLeads: 0,
    totalPosts: 0,
    totalComments: 0,
    newLeads: 0,
    contactedLeads: 0,
    convertedLeads: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentTasks, setRecentTasks] = useState<CrawlTask[]>([]);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);

  const prevTaskIdsRef = useRef<Set<number>>(new Set());

  const loadStats = useCallback(async () => {
    try {
      const [leadsAll, leadsA, leadsB, leadsNew, leadsContacted, leadsConverted, postsAll, commentsAll] = await Promise.all([
        getLeads({ page: 1, page_size: 1 }),
        getLeads({ lead_level: "A", page: 1, page_size: 1 }),
        getLeads({ lead_level: "B", page: 1, page_size: 1 }),
        getLeads({ status: "new", page: 1, page_size: 1 }),
        getLeads({ status: "contacted", page: 1, page_size: 1 }),
        getLeads({ status: "converted", page: 1, page_size: 1 }),
        getPosts({ page: 1, page_size: 1 }),
        getComments({ page: 1, page_size: 1 }),
      ]);

      setStats({
        totalLeads: leadsAll.total,
        aLeads: leadsA.total,
        bLeads: leadsB.total,
        totalPosts: postsAll.total,
        totalComments: commentsAll.total,
        newLeads: leadsNew.total,
        contactedLeads: leadsContacted.total,
        convertedLeads: leadsConverted.total,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载统计失败");
    }
  }, []);

  const loadRecentTasks = useCallback(async () => {
    try {
      const result = await getCrawlTasks();
      const tasks = result.items.slice(0, 8);
      setRecentTasks(tasks);

      const prevIds = prevTaskIdsRef.current;
      const currentIds = new Set(tasks.map((t) => t.id));

      for (const task of tasks) {
        if (prevIds.has(task.id) && !currentIds.has(task.id)) continue;
        if (prevIds.has(task.id)) {
          const prev = prevIds;
          if (task.status === "success" && !prev.has(-task.id)) {
            showToast("success", `任务 #${task.id} 采集完成`, `获得 ${task.post_count} 帖子、${task.lead_count} 线索`);
            prevIds.add(-task.id);
          } else if (task.status === "failed" && !prevIds.has(-task.id - 100000)) {
            showToast("error", `任务 #${task.id} 采集失败`, task.error_message?.slice(0, 100) || "未知错误");
            prevIds.add(-task.id - 100000);
          }
        }
      }

      prevTaskIdsRef.current = currentIds;
    } catch {
      // silent
    }
  }, []);

  const loadQueueStatus = useCallback(async () => {
    try {
      const status = await getQueueStatus();
      setQueueStatus(status);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    async function initialLoad() {
      setLoading(true);
      await Promise.all([loadStats(), loadRecentTasks(), loadQueueStatus()]);
      setLoading(false);
    }
    void initialLoad();
  }, [loadStats, loadRecentTasks, loadQueueStatus]);

  useEffect(() => {
    const interval = setInterval(() => {
      void Promise.all([loadRecentTasks(), loadQueueStatus()]);
    }, 5000);
    return () => clearInterval(interval);
  }, [loadRecentTasks, loadQueueStatus]);

  const aRatio = stats.totalLeads > 0 ? ((stats.aLeads / stats.totalLeads) * 100).toFixed(1) : "0.0";
  const conversionRate = stats.totalLeads > 0 ? ((stats.convertedLeads / stats.totalLeads) * 100).toFixed(1) : "0.0";

  const hasActiveTasks = recentTasks.some(
    (t) => t.status === "pending" || t.status === "running" || t.status === "retrying",
  );

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">仪表板</p>
          <h1>智获客雷达</h1>
          <p className="page-description">全局数据概览，快速掌握线索、帖子和评论动态。</p>
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

      {loading ? (
        <>
          <section className="stats-grid">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="stat-card">
                <div className="skeleton skeleton-text" style={{ width: "40%" }} />
                <div className="skeleton skeleton-title" style={{ width: "60%" }} />
              </div>
            ))}
          </section>
          <section className="stats-grid" style={{ marginTop: 12 }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="stat-card">
                <div className="skeleton skeleton-text" style={{ width: "40%" }} />
                <div className="skeleton skeleton-title" style={{ width: "60%" }} />
              </div>
            ))}
          </section>
        </>
      ) : null}

      {error ? (
        <div className="state-panel state-error">
          <p>{error}</p>
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <section className="stats-grid">
            <div className="stat-card"><span>总线索数</span><strong>{stats.totalLeads}</strong></div>
            <div className="stat-card"><span>A 级线索</span><strong style={{ color: "#dc2626" }}>{stats.aLeads}</strong></div>
            <div className="stat-card"><span>B 级线索</span><strong style={{ color: "#2563eb" }}>{stats.bLeads}</strong></div>
            <div className="stat-card"><span>A 级占比</span><strong>{aRatio}%</strong></div>
            <div className="stat-card"><span>总帖子数</span><strong>{stats.totalPosts}</strong></div>
          </section>

          <section className="stats-grid" style={{ marginTop: 12 }}>
            <div className="stat-card"><span>总评论数</span><strong>{stats.totalComments}</strong></div>
            <div className="stat-card"><span>新增线索</span><strong style={{ color: "#16a34a" }}>{stats.newLeads}</strong></div>
            <div className="stat-card"><span>已联系</span><strong>{stats.contactedLeads}</strong></div>
            <div className="stat-card"><span>已转化</span><strong style={{ color: "#16a34a" }}>{stats.convertedLeads}</strong></div>
            <div className="stat-card"><span>转化率</span><strong>{conversionRate}%</strong></div>
          </section>
        </>
      ) : null}

      <section className="card" style={{ marginTop: 20 }}>
        <div className="card-header card-header-row">
          <div>
            <h2>最近采集任务</h2>
            <p>最近 8 条采集任务的状态概览{hasActiveTasks ? "（自动刷新中）" : ""}。</p>
          </div>
          <Link to="/crawl-tasks">
            <button type="button" className="btn-secondary">查看全部</button>
          </Link>
        </div>

        {recentTasks.length === 0 ? (
          <div className="state-panel state-empty"><p>暂无采集任务。</p></div>
        ) : (
          <div className="recent-tasks-list">
            {recentTasks.map((task) => (
              <Link
                key={task.id}
                to="/crawl-tasks"
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <div className="recent-task-item">
                  <div className="recent-task-info">
                    <span className="recent-task-label">
                      #{task.id} · {PLATFORM_LABELS[task.platform] || task.platform} · {task.source_type}
                    </span>
                    <span className="recent-task-meta">
                      {task.source_value?.slice(0, 40) || "-"}
                      {task.started_at ? ` · ${formatTimeAgo(task.started_at)}` : ""}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {task.status === "success" && (
                      <span style={{ fontSize: 12, color: "#6b7280" }}>
                        {task.post_count}帖 {task.comment_count}评 {task.lead_count}线索
                      </span>
                    )}
                    {task.retry_count > 0 && (
                      <span className="tag tag-warning">重试{task.retry_count}次</span>
                    )}
                    <span className={statusPillClass(task.status)}>
                      {statusLabel(task.status)}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <h2>快捷入口</h2>
          <p>快速跳转到各功能页面。</p>
        </div>
        <div className="dashboard-shortcuts">
          <a href="/leads" className="shortcut-card">
            <strong>线索池</strong>
            <span>查看和管理所有线索</span>
          </a>
          <a href="/crawl-tasks" className="shortcut-card">
            <strong>采集任务</strong>
            <span>创建和管理采集任务</span>
          </a>
          <a href="/monitor-sources" className="shortcut-card">
            <strong>监控源</strong>
            <span>管理采集源和调度</span>
          </a>
          <a href="/scoring-rules" className="shortcut-card">
            <strong>评分规则</strong>
            <span>配置和测试评分策略</span>
          </a>
          <a href="/daily-reports" className="shortcut-card">
            <strong>日报</strong>
            <span>查看每日获客报告</span>
          </a>
        </div>
      </section>
    </main>
  );
}
