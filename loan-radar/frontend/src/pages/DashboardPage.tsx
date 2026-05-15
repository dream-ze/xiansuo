import { useEffect, useState } from "react";

import {
  getLeads,
  getPosts,
  getComments,
} from "../api/client";

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

  useEffect(() => {
    async function loadStats() {
      setLoading(true);
      setError(null);
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
      } finally {
        setLoading(false);
      }
    }

    void loadStats();
  }, []);

  const aRatio = stats.totalLeads > 0 ? ((stats.aLeads / stats.totalLeads) * 100).toFixed(1) : "0.0";

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">仪表板</p>
          <h1>智获客雷达</h1>
          <p className="page-description">全局数据概览，快速掌握线索、帖子和评论动态。</p>
        </div>
      </header>

      {loading ? <p className="state-text">加载中...</p> : null}
      {error ? (
        <div className="state-panel state-error">
          <p>{error}</p>
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <section className="stats-grid">
            <div className="stat-card"><span>总线索数</span><strong>{stats.totalLeads}</strong></div>
            <div className="stat-card"><span>A 级线索</span><strong>{stats.aLeads}</strong></div>
            <div className="stat-card"><span>B 级线索</span><strong>{stats.bLeads}</strong></div>
            <div className="stat-card"><span>A 级占比</span><strong>{aRatio}%</strong></div>
            <div className="stat-card"><span>总帖子数</span><strong>{stats.totalPosts}</strong></div>
          </section>

          <section className="stats-grid" style={{ marginTop: 12 }}>
            <div className="stat-card"><span>总评论数</span><strong>{stats.totalComments}</strong></div>
            <div className="stat-card"><span>新增线索</span><strong>{stats.newLeads}</strong></div>
            <div className="stat-card"><span>已联系</span><strong>{stats.contactedLeads}</strong></div>
            <div className="stat-card"><span>已转化</span><strong>{stats.convertedLeads}</strong></div>
            <div className="stat-card"><span>转化率</span><strong>{stats.totalLeads > 0 ? ((stats.convertedLeads / stats.totalLeads) * 100).toFixed(1) : "0.0"}%</strong></div>
          </section>

          <section className="card" style={{ marginTop: 20 }}>
            <div className="card-header">
              <h2>快捷入口</h2>
              <p>快速跳转到各功能页面。</p>
            </div>
            <div className="dashboard-shortcuts">
              <a href="/leads" className="shortcut-card">
                <strong>线索池</strong>
                <span>查看和管理所有线索</span>
              </a>
              <a href="/posts" className="shortcut-card">
                <strong>帖子池</strong>
                <span>浏览采集到的帖子</span>
              </a>
              <a href="/comments" className="shortcut-card">
                <strong>评论池</strong>
                <span>查看评论和需求标记</span>
              </a>
              <a href="/monitor-sources" className="shortcut-card">
                <strong>监控源</strong>
                <span>管理采集源和任务</span>
              </a>
              <a href="/daily-reports" className="shortcut-card">
                <strong>日报</strong>
                <span>查看每日获客报告</span>
              </a>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
