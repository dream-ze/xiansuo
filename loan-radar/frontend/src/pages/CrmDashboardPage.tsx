import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getCrmDashboard, type CrmDashboard } from "../api/client";

const STAGE_LABELS: Record<string, string> = {
  new_customer: "新客户",
  contacted: "已联系",
  demand_confirmed: "需求确认",
  qualification_review: "资质评估",
  proposal_sent: "方案报价",
  contract_signed: "合同签约",
  funded_won: "放款成交",
  lost: "流失",
};

export default function CrmDashboardPage() {
  const [data, setData] = useState<CrmDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      setData(await getCrmDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载 CRM 总览失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">CRM Closed Loop</p>
          <h1>CRM 转化闭环</h1>
          <p className="page-description">从线索转客户、首跟进、阶段推进到合同回款，盯住获客转化效率。</p>
        </div>
        <div className="action-row">
          <Link className="btn-secondary" to="/crm/customers">客户档案</Link>
          <Link className="btn-secondary" to="/crm/tasks">任务提醒</Link>
          <Link className="btn-secondary" to="/crm/opportunities">销售漏斗</Link>
        </div>
      </header>

      {loading ? <div className="state-panel"><p>加载中...</p></div> : null}
      {error ? <div className="state-panel state-error"><p>{error}</p><button onClick={() => void loadData()}>重试</button></div> : null}

      {data ? (
        <>
          <section className="stats-grid">
            <div className="stat-card"><span>总线索</span><strong>{data.total_leads}</strong></div>
            <div className="stat-card"><span>已转客户</span><strong>{data.converted_leads}</strong></div>
            <div className="stat-card"><span>转化率</span><strong>{data.conversion_rate}%</strong></div>
            <div className="stat-card"><span>客户数</span><strong>{data.customer_count}</strong></div>
            <div className="stat-card"><span>商机数</span><strong>{data.opportunity_count}</strong></div>
            <div className="stat-card"><span>成交率</span><strong>{data.win_rate}%</strong></div>
            <div className="stat-card"><span>待办任务</span><strong>{data.pending_task_count}</strong></div>
            <div className="stat-card"><span>逾期任务</span><strong style={{ color: "#dc2626" }}>{data.overdue_task_count}</strong></div>
            <div className="stat-card"><span>7天内回款</span><strong>{data.upcoming_receivable_count}</strong></div>
            <div className="stat-card"><span>逾期回款</span><strong style={{ color: "#dc2626" }}>{data.overdue_receivable_count}</strong></div>
          </section>

          <div className="two-column-grid">
            <section className="card">
              <div className="card-header">
                <h2>销售阶段漏斗</h2>
                <p>贷款专用阶段分布，用于观察推进卡点。</p>
              </div>
              <div className="pipeline-list">
                {Object.entries(STAGE_LABELS).map(([stage, label]) => (
                  <div key={stage} className="pipeline-row">
                    <span>{label}</span>
                    <strong>{data.stage_counts[stage] || 0}</strong>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <h2>来源平台转化</h2>
                <p>看哪些平台带来的线索更容易进入 CRM。</p>
              </div>
              <div className="pipeline-list">
                {Object.entries(data.source_counts).length === 0 ? <p className="text-muted">暂无来源数据</p> : null}
                {Object.entries(data.source_counts).map(([source, count]) => (
                  <div key={source} className="pipeline-row">
                    <span>{source}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      ) : null}
    </main>
  );
}
