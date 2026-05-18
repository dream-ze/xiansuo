import { useEffect, useState } from "react";

import { getCrmReceivablePlans, type CrmReceivablePlan } from "../api/client";

export default function CrmReceivablesPage() {
  const [items, setItems] = useState<CrmReceivablePlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      setItems(await getCrmReceivablePlans());
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载回款计划失败");
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
          <p className="page-eyebrow">CRM Receivables</p>
          <h1>回款管理</h1>
          <p className="page-description">跟踪合同回款计划、已收金额和逾期状态。</p>
        </div>
      </header>
      <section className="card">
        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? <div className="state-panel state-error"><p>{error}</p></div> : null}
        {!loading && !error && items.length === 0 ? <div className="state-panel state-empty"><p>暂无回款计划。</p></div> : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>合同</th>
                  <th>客户</th>
                  <th>计划金额</th>
                  <th>已收金额</th>
                  <th>到期日</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.contract_title || item.contract_id}</td>
                    <td>{item.customer_name || item.customer_id}</td>
                    <td>{item.amount.toLocaleString()}</td>
                    <td>{item.received_amount.toLocaleString()}</td>
                    <td>{new Date(item.due_date).toLocaleDateString()} {item.is_overdue ? <span className="tag tag-danger">逾期</span> : null}</td>
                    <td><span className={`status-pill status-${item.status}`}>{item.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
