import { useEffect, useState } from "react";

import { getCrmOpportunities, updateCrmOpportunity, type CrmOpportunity } from "../api/client";
import { showToast } from "../components/ToastContainer";

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

const STAGES = Object.keys(STAGE_LABELS);

export default function CrmOpportunitiesPage() {
  const [items, setItems] = useState<CrmOpportunity[]>([]);
  const [stage, setStage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const result = await getCrmOpportunities({ stage: stage || undefined, page: 1, page_size: 100 });
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载商机失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleStageChange(item: CrmOpportunity, nextStage: string) {
    setBusyId(item.id);
    try {
      await updateCrmOpportunity(item.id, { stage: nextStage });
      showToast("success", "阶段已更新", `${item.name} 已推进到 ${STAGE_LABELS[nextStage] || nextStage}`);
      await loadData();
    } catch (err) {
      showToast("error", "更新失败", err instanceof Error ? err.message : "未知错误");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">CRM Pipeline</p>
          <h1>销售漏斗</h1>
          <p className="page-description">按贷款专用阶段推进商机，阶段变化会沉淀为跟进记录。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>阶段筛选</h2>
            <p>聚焦卡住的销售阶段。</p>
          </div>
          <div className="action-row">
            <select value={stage} onChange={(e) => setStage(e.target.value)}>
              <option value="">全部阶段</option>
              {STAGES.map((item) => <option key={item} value={item}>{STAGE_LABELS[item]}</option>)}
            </select>
            <button className="btn-primary" onClick={() => void loadData()} disabled={loading}>查询</button>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>商机列表</h2>
        </div>
        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? <div className="state-panel state-error"><p>{error}</p></div> : null}
        {!loading && !error && items.length === 0 ? <div className="state-panel state-empty"><p>暂无商机。</p></div> : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>商机</th>
                  <th>客户</th>
                  <th>金额</th>
                  <th>负责人</th>
                  <th>阶段</th>
                  <th>下一步</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.customer_name || item.customer_id}</td>
                    <td>{item.estimated_amount ? item.estimated_amount.toLocaleString() : "-"}</td>
                    <td>{item.owner_name || "未分配"}</td>
                    <td>
                      <select
                        value={item.stage}
                        disabled={busyId === item.id}
                        onChange={(e) => void handleStageChange(item, e.target.value)}
                      >
                        {STAGES.map((stageValue) => <option key={stageValue} value={stageValue}>{STAGE_LABELS[stageValue]}</option>)}
                      </select>
                    </td>
                    <td className="cell-break">{item.next_step || "-"}</td>
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
