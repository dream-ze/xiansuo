import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getComments, type Comment, type CommentQueryParams } from "../api/client";

const PLATFORM_OPTIONS = ["", "xhs", "douyin", "zhihu"];
const DEMAND_OPTIONS = ["", "借款需求", "资质焦虑", "产品咨询", "弱意向"];
const RISK_OPTIONS = ["", "low", "mid", "high"];
const SUSPECTED_OPTIONS = ["", "true", "false"];

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

export default function CommentsPage() {
  const navigate = useNavigate();

  const [items, setItems] = useState<Comment[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<CommentQueryParams>({
    platform: "",
    demand_type: "",
    risk_level: "",
    post_id: "",
    keyword: "",
  });
  const [suspectedFilter, setSuspectedFilter] = useState("");

  const hasItems = useMemo(() => items.length > 0, [items]);

  async function loadData(nextPage = page, nextFilters = filters, nextSuspected = suspectedFilter) {
    setLoading(true);
    setError(null);

    try {
      const result = await getComments({
        platform: nextFilters.platform || undefined,
        demand_type: nextFilters.demand_type || undefined,
        risk_level: nextFilters.risk_level || undefined,
        post_id: nextFilters.post_id || undefined,
        keyword: nextFilters.keyword || undefined,
        is_suspected_demand: nextSuspected === "" ? undefined : nextSuspected === "true",
        page: nextPage,
        page_size: pageSize,
      });
      setItems(result.items);
      setTotal(result.total);
      setPage(result.page);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载评论失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(1, filters, suspectedFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters() {
    setPage(1);
    await loadData(1, filters, suspectedFilter);
  }

  async function resetFilters() {
    const nextFilters: CommentQueryParams = { platform: "", demand_type: "", risk_level: "", post_id: "", keyword: "" };
    setFilters(nextFilters);
    setSuspectedFilter("");
    setPage(1);
    await loadData(1, nextFilters, "");
  }

  async function handlePrevPage() {
    const nextPage = Math.max(1, page - 1);
    await loadData(nextPage, filters, suspectedFilter);
  }

  async function handleNextPage() {
    await loadData(page + 1, filters, suspectedFilter);
  }

  function handleViewLeads(commentId: number) {
    navigate(`/leads?source_comment_id=${commentId}`);
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">评论池</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看评论池并按平台、需求类型、风险等级、疑似需求筛选。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>筛选条件</h2>
            <p>支持基础筛选：平台、需求类型、风险等级、疑似需求、关键词。</p>
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
            需求类型
            <select
              value={(filters.demand_type as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, demand_type: event.target.value }))}
            >
              {DEMAND_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || "全部"}
                </option>
              ))}
            </select>
          </label>

          <label>
            风险等级
            <select
              value={(filters.risk_level as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, risk_level: event.target.value }))}
            >
              {RISK_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || "全部"}
                </option>
              ))}
            </select>
          </label>

          <label>
            疑似需求
            <select value={suspectedFilter} onChange={(event) => setSuspectedFilter(event.target.value)}>
              {SUSPECTED_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value === "" ? "全部" : value === "true" ? "是" : "否"}
                </option>
              ))}
            </select>
          </label>

          <label>
            帖子 ID
            <input
              value={(filters.post_id as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, post_id: event.target.value }))}
              placeholder="平台原始 post_id"
            />
          </label>

          <label>
            关键词
            <input
              value={(filters.keyword as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, keyword: event.target.value }))}
              placeholder="评论内容/用户"
            />
          </label>
        </div>
      </section>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>评论列表</h2>
            <p>共 {total} 条，当前第 {page} 页。</p>
          </div>
          <button type="button" onClick={() => void loadData(page, filters, suspectedFilter)} disabled={loading}>刷新列表</button>
        </div>

        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadData(page, filters, suspectedFilter)}>重试</button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty">
            <p>暂无评论数据。</p>
          </div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>用户</th>
                  <th>帖子 ID</th>
                  <th>内容</th>
                  <th>需求类型</th>
                  <th>风险等级</th>
                  <th>疑似需求</th>
                  <th>关联线索</th>
                  <th>点赞</th>
                  <th>发布时间</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{item.platform}</td>
                    <td>{item.user_name || "-"}</td>
                    <td className="cell-break">{item.post_id}</td>
                    <td className="cell-break">{item.content || "-"}</td>
                    <td>{item.demand_type || "-"}</td>
                    <td>{item.risk_level || "-"}</td>
                    <td>{item.is_suspected_demand ? "是" : "否"}</td>
                    <td>
                      {item.has_lead ? (
                        <button type="button" className="btn-sm lead-count-btn" onClick={() => handleViewLeads(item.id)}>查看</button>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td>{item.like_count}</td>
                    <td>{formatDateTime(item.publish_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="action-row" style={{ marginTop: 12 }}>
          <button type="button" onClick={() => void handlePrevPage()} disabled={loading || page <= 1}>上一页</button>
          <button type="button" onClick={() => void handleNextPage()} disabled={loading || items.length < pageSize}>下一页</button>
        </div>
      </section>
    </main>
  );
}
