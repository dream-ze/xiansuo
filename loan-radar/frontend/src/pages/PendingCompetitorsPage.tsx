import { useEffect, useMemo, useState } from "react";

import {
  approvePendingCompetitor,
  getPendingCompetitors,
  ignorePendingCompetitor,
  type PendingCompetitor,
  type PendingCompetitorQueryParams,
} from "../api/client";

const PLATFORM_OPTIONS = ["", "xhs", "douyin", "zhihu", "other"];
const STATUS_OPTIONS = ["", "pending", "approved", "ignored"];

function statusText(status: string) {
  const mapping: Record<string, string> = {
    pending: "待审核",
    approved: "已通过",
    ignored: "已忽略",
  };
  return mapping[status] ?? status;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function PendingCompetitorsPage() {
  const [items, setItems] = useState<PendingCompetitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [filters, setFilters] = useState<PendingCompetitorQueryParams>({
    platform: "",
    status: "pending",
  });
  const [minScore, setMinScore] = useState("");

  const hasItems = useMemo(() => items.length > 0, [items]);

  async function loadData(nextFilters = filters, nextMinScore = minScore) {
    setLoading(true);
    setError(null);

    try {
      const result = await getPendingCompetitors({
        platform: nextFilters.platform || undefined,
        status: nextFilters.status || undefined,
        min_score: nextMinScore === "" ? undefined : Number(nextMinScore),
      });
      setItems(result);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载同行发现池失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(filters, minScore);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters() {
    await loadData(filters, minScore);
  }

  async function resetFilters() {
    const nextFilters: PendingCompetitorQueryParams = { platform: "", status: "pending" };
    setFilters(nextFilters);
    setMinScore("");
    await loadData(nextFilters, "");
  }

  async function handleApprove(item: PendingCompetitor) {
    setBusyId(item.id);
    setError(null);
    setActionMessage(null);

    try {
      const result = await approvePendingCompetitor(item.id);
      setActionMessage(`已通过：${result.pending_competitor.account_name}，并新增监控源 ${result.monitor_source.name}`);
      await loadData(filters, minScore);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "审核通过失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handleIgnore(item: PendingCompetitor) {
    setBusyId(item.id);
    setError(null);
    setActionMessage(null);

    try {
      await ignorePendingCompetitor(item.id);
      setActionMessage(`已忽略：${item.account_name}`);
      await loadData(filters, minScore);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "忽略失败");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">同行账号发现池</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看待审核同行账号，支持审核通过加入监控源或忽略。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>筛选条件</h2>
            <p>支持平台、状态、最低评分筛选。</p>
          </div>
          <div className="action-row">
            <button type="button" onClick={() => void applyFilters()} disabled={loading}>查询</button>
            <button type="button" onClick={() => void resetFilters()} disabled={loading}>重置</button>
          </div>
        </div>

        <div className="filter-grid">
          <label>
            平台
            <select
              value={(filters.platform as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, platform: event.target.value }))}
            >
              {PLATFORM_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || "全部"}
                </option>
              ))}
            </select>
          </label>

          <label>
            状态
            <select
              value={(filters.status as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
            >
              {STATUS_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || "全部"}
                </option>
              ))}
            </select>
          </label>

          <label>
            最低评分
            <input
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(event) => setMinScore(event.target.value)}
              placeholder="0-100"
            />
          </label>
        </div>
      </section>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>待审核账号列表</h2>
            <p>当前 {items.length} 条记录。</p>
          </div>
          <button type="button" onClick={() => void loadData(filters, minScore)} disabled={loading}>刷新列表</button>
        </div>

        {actionMessage ? <div className="state-panel state-empty"><p>{actionMessage}</p></div> : null}
        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadData(filters, minScore)}>重试</button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty">
            <p>暂无符合条件的同行账号。</p>
          </div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>账号名</th>
                  <th>来源关键词</th>
                  <th>综合分</th>
                  <th>状态</th>
                  <th>发现原因</th>
                  <th>发现时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const canReview = item.status === "pending";
                  const isBusy = busyId === item.id;
                  return (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td>{item.platform}</td>
                      <td className="cell-break">{item.account_name}</td>
                      <td>{item.source_keyword || "-"}</td>
                      <td>{item.competitor_score.toFixed(2)}</td>
                      <td>
                        <span className={`status-pill pending-status-${item.status}`}>{statusText(item.status)}</span>
                      </td>
                      <td className="cell-break">{item.discover_reason || "-"}</td>
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>
                        <div className="action-row">
                          <button
                            type="button"
                            onClick={() => void handleApprove(item)}
                            disabled={!canReview || isBusy}
                          >
                            {isBusy ? "处理中..." : "审核通过"}
                          </button>
                          <button
                            type="button"
                            className="danger"
                            onClick={() => void handleIgnore(item)}
                            disabled={!canReview || isBusy}
                          >
                            忽略
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
    </main>
  );
}
