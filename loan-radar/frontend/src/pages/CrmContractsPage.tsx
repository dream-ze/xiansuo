import { useEffect, useState } from "react";

import { getCrmContracts, type CrmContract } from "../api/client";

export default function CrmContractsPage() {
  const [items, setItems] = useState<CrmContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      setItems(await getCrmContracts());
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载合同失败");
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
          <p className="page-eyebrow">CRM Contracts</p>
          <h1>合同管理</h1>
          <p className="page-description">管理贷款成交合同台账，关联客户、商机和后续回款计划。</p>
        </div>
      </header>
      <section className="card">
        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? <div className="state-panel state-error"><p>{error}</p></div> : null}
        {!loading && !error && items.length === 0 ? <div className="state-panel state-empty"><p>暂无合同。</p></div> : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>合同</th>
                  <th>客户</th>
                  <th>编号</th>
                  <th>金额</th>
                  <th>负责人</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.title}</td>
                    <td>{item.customer_name || item.customer_id}</td>
                    <td>{item.contract_no || "-"}</td>
                    <td>{item.amount.toLocaleString()}</td>
                    <td>{item.owner_name || "未分配"}</td>
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
