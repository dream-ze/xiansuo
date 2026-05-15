import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { getPosts, type Post, type PostQueryParams } from "../api/client";

const PLATFORM_OPTIONS = ["", "xhs", "douyin", "zhihu", "other"];
const SOURCE_TYPE_OPTIONS = ["", "keyword", "competitor_account", "manual_post", "hot_post_rule"];
const HOT_OPTIONS = ["", "true", "false"];

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

export default function PostsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight");

  const [items, setItems] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<PostQueryParams>({
    platform: "",
    source_type: "",
    keyword: "",
  });
  const [hotFilter, setHotFilter] = useState("");

  const hasItems = useMemo(() => items.length > 0, [items]);

  async function loadData(nextPage = page, nextFilters = filters, nextHot = hotFilter) {
    setLoading(true);
    setError(null);

    try {
      const result = await getPosts({
        platform: nextFilters.platform || undefined,
        source_type: nextFilters.source_type || undefined,
        keyword: nextFilters.keyword || undefined,
        is_hot: nextHot === "" ? undefined : nextHot === "true",
        page: nextPage,
        page_size: pageSize,
      });
      setItems(result.items);
      setTotal(result.total);
      setPage(result.page);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载帖子失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(1, filters, hotFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters() {
    setPage(1);
    await loadData(1, filters, hotFilter);
  }

  async function resetFilters() {
    const nextFilters: PostQueryParams = { platform: "", source_type: "", keyword: "" };
    setFilters(nextFilters);
    setHotFilter("");
    setPage(1);
    await loadData(1, nextFilters, "");
  }

  async function handlePrevPage() {
    const nextPage = Math.max(1, page - 1);
    await loadData(nextPage, filters, hotFilter);
  }

  async function handleNextPage() {
    await loadData(page + 1, filters, hotFilter);
  }

  function handleViewLeads(postId: number) {
    navigate(`/leads?source_post_id=${postId}`);
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">帖子池</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看采集到的帖子内容并按平台、来源、是否爆款进行筛选。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>筛选条件</h2>
            <p>支持基础筛选：平台、来源类型、爆款状态、关键词。</p>
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
            来源类型
            <select
              value={(filters.source_type as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, source_type: event.target.value }))}
            >
              {SOURCE_TYPE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value || "全部"}
                </option>
              ))}
            </select>
          </label>

          <label>
            是否爆款
            <select value={hotFilter} onChange={(event) => setHotFilter(event.target.value)}>
              {HOT_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value === "" ? "全部" : value === "true" ? "是" : "否"}
                </option>
              ))}
            </select>
          </label>

          <label>
            关键词
            <input
              value={(filters.keyword as string) ?? ""}
              onChange={(event) => setFilters((prev) => ({ ...prev, keyword: event.target.value }))}
              placeholder="标题/内容/作者"
            />
          </label>
        </div>
      </section>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>帖子列表</h2>
            <p>共 {total} 条，当前第 {page} 页。</p>
          </div>
          <button type="button" onClick={() => void loadData(page, filters, hotFilter)} disabled={loading}>刷新列表</button>
        </div>

        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadData(page, filters, hotFilter)}>重试</button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty">
            <p>暂无帖子数据。</p>
          </div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>来源类型</th>
                  <th>标题</th>
                  <th>原链接</th>
                  <th>作者</th>
                  <th>点赞</th>
                  <th>评论</th>
                  <th>收藏</th>
                  <th>爆款</th>
                  <th>线索数</th>
                  <th>发布时间</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className={highlightId && Number(highlightId) === item.id ? "row-highlight" : ""}>
                    <td>{item.id}</td>
                    <td>{item.platform}</td>
                    <td>{item.source_type}</td>
                    <td className="cell-break">{item.title || item.content || "-"}</td>
                    <td className="cell-break">
                      {item.post_url ? (
                        <a href={item.post_url} target="_blank" rel="noreferrer">打开</a>
                      ) : "-"}
                    </td>
                    <td>{item.author_name || "-"}</td>
                    <td>{item.like_count}</td>
                    <td>{item.comment_count}</td>
                    <td>{item.collect_count}</td>
                    <td>{item.is_hot ? "是" : "否"}</td>
                    <td>
                      {item.lead_count > 0 ? (
                        <button type="button" className="btn-sm lead-count-btn" onClick={() => handleViewLeads(item.id)}>
                          {item.lead_count}
                        </button>
                      ) : (
                        <span className="text-muted">0</span>
                      )}
                    </td>
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
