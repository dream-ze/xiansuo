import { useEffect, useState } from "react";

import { getCrmTasks, updateCrmTask, type CrmTask } from "../api/client";
import { showToast } from "../components/ToastContainer";

function formatDateTime(value: string | null) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function CrmTasksPage() {
  const [items, setItems] = useState<CrmTask[]>([]);
  const [ownerName, setOwnerName] = useState("");
  const [status, setStatus] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const result = await getCrmTasks({
        owner_name: ownerName || undefined,
        status: status || undefined,
        page: 1,
        page_size: 100,
      });
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载任务失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function completeTask(task: CrmTask) {
    setBusyId(task.id);
    try {
      await updateCrmTask(task.id, { status: "done" });
      showToast("success", "任务已完成", task.title);
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
          <p className="page-eyebrow">CRM Tasks</p>
          <h1>任务提醒</h1>
          <p className="page-description">首跟进、资料补充、方案确认、合同签约和回款提醒都在这里承接。</p>
        </div>
      </header>

      <section className="card">
        <div className="filter-grid">
          <label><span>负责人</span><input value={ownerName} onChange={(e) => setOwnerName(e.target.value)} placeholder="销售A" /></label>
          <label>
            <span>状态</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">全部</option>
              <option value="pending">待办</option>
              <option value="done">已完成</option>
              <option value="canceled">已取消</option>
            </select>
          </label>
          <label>
            <span>&nbsp;</span>
            <button className="btn-primary" onClick={() => void loadData()} disabled={loading}>查询</button>
          </label>
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>任务列表</h2>
        </div>
        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? <div className="state-panel state-error"><p>{error}</p></div> : null}
        {!loading && !error && items.length === 0 ? <div className="state-panel state-empty"><p>暂无任务。</p></div> : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务</th>
                  <th>客户</th>
                  <th>类型</th>
                  <th>负责人</th>
                  <th>截止时间</th>
                  <th>状态</th>
                  <th>建议</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.title}</td>
                    <td>{item.customer_name || "-"}</td>
                    <td>{item.task_type}</td>
                    <td>{item.owner_name || "未分配"}</td>
                    <td>{formatDateTime(item.due_at)} {item.is_overdue ? <span className="tag tag-danger">逾期</span> : null}</td>
                    <td><span className={`status-pill status-${item.status}`}>{item.status}</span></td>
                    <td className="cell-break">{item.suggestion || "-"}</td>
                    <td>
                      {item.status === "pending" ? (
                        <button className="btn-sm btn-primary" disabled={busyId === item.id} onClick={() => void completeTask(item)}>完成</button>
                      ) : "-"}
                    </td>
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
