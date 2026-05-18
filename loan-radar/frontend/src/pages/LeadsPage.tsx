import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  exportLeadsCsv,
  convertLeadToCrm,
  getLeads,
  updateLeadStatus,
  type Lead,
  type LeadQueryParams,
} from "../api/client";
import { showToast } from "../components/ToastContainer";

const LEAD_LEVEL_OPTIONS = ["", "A", "B", "C", "D"];
const PLATFORM_OPTIONS = ["", "xhs", "douyin", "zhihu"];
const STATUS_OPTIONS = ["", "new", "contacted", "interested", "invalid", "converted"];
const DUPLICATE_FILTER_OPTIONS = [
  { value: "", label: "全部" },
  { value: "false", label: "非重复线索" },
  { value: "true", label: "重复线索" },
];

const PLATFORM_LABELS: Record<string, string> = {
  xhs: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
};

const LEAD_STATUS_LABELS: Record<string, string> = {
  new: "新线索",
  contacted: "已跟进",
  interested: "有意向",
  invalid: "无效",
  converted: "已转化",
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function truncate(text: string | null | undefined, max = 30) {
  if (!text) return "-";
  return text.length > max ? text.slice(0, max) + "..." : text;
}

const DIMENSION_LABELS: Record<string, string> = {
  demand_clarity: "需求明确度",
  urgency: "紧迫程度",
  qualification: "资质条件",
  product_match: "产品匹配",
  weak_intent: "弱意向信号",
  amount: "金额信息",
  authenticity: "真实性",
  risk_penalty: "风险扣分",
};

function highlightKeywords(text: string | null | undefined, keywords: string[]) {
  if (!text || keywords.length === 0) return <>{text || "-"}</>;
  const escaped = keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(pattern);
  return (
    <>
      {parts.map((part, i) =>
        keywords.some((k) => k.toLowerCase() === part.toLowerCase()) ? (
          <mark key={i} className="keyword-highlight">{part}</mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

function getMatchedWords(evidence: Lead["evidence"]): string[] {
  if (!evidence || typeof evidence !== "object") return [];
  const typed = evidence as Record<string, unknown>;
  const words = typed.matched_words;
  return Array.isArray(words) ? words : [];
}

function getAmounts(evidence: Lead["evidence"]): string[] {
  if (!evidence || typeof evidence !== "object") return [];
  const typed = evidence as Record<string, unknown>;
  const amounts = typed.amounts;
  return Array.isArray(amounts) ? amounts : [];
}

function getScoreBreakdown(evidence: Lead["evidence"]): Record<string, number> | null {
  if (!evidence || typeof evidence !== "object") return null;
  const typed = evidence as Record<string, unknown>;
  const sb = typed.score_breakdown;
  return sb && typeof sb === "object" ? (sb as Record<string, number>) : null;
}

function buildEvidenceSections(evidence: Lead["evidence"]) {
  if (!evidence || typeof evidence !== "object") {
    return [] as Array<{ title: string; value: string; type?: string }>;
  }

  const typedEvidence = evidence as Record<string, unknown>;
  const sections: Array<{ title: string; value: string; type?: string }> = [];

  const matchedWords = typedEvidence.matched_words;
  if (matchedWords && Array.isArray(matchedWords) && matchedWords.length > 0) {
    sections.push({ title: "命中关键词", value: matchedWords.join("、"), type: "tags" });
  }

  const amounts = typedEvidence.amounts;
  if (amounts && Array.isArray(amounts) && amounts.length > 0) {
    sections.push({ title: "金额信息", value: amounts.join(", ") });
  }

  const negationDetected = typedEvidence.negation_detected;
  if (negationDetected) {
    const negationWords = typedEvidence.negation_words as string[] | undefined;
    sections.push({
      title: "否定词检测",
      value: negationWords?.length ? `检测到否定词：${negationWords.join("、")}` : "检测到否定表达",
      type: "warning",
    });
  }

  const riskKeywords = typedEvidence.risk_keywords_matched;
  if (riskKeywords && Array.isArray(riskKeywords) && riskKeywords.length > 0) {
    sections.push({ title: "风险关键词", value: riskKeywords.join("、"), type: "danger" });
  }

  const negativeKeywords = typedEvidence.negative_keywords_matched;
  if (negativeKeywords && Array.isArray(negativeKeywords) && negativeKeywords.length > 0) {
    sections.push({ title: "负面关键词", value: negativeKeywords.join("、"), type: "danger" });
  }

  const scoreBreakdown = typedEvidence.score_breakdown;
  if (scoreBreakdown && typeof scoreBreakdown === "object") {
    const breakdown = scoreBreakdown as Record<string, number>;
    const lines = Object.entries(breakdown)
      .map(([key, val]) => `${DIMENSION_LABELS[key] || key}: ${val > 0 ? "+" : ""}${val}`)
      .join("\n");
    sections.push({ title: "评分拆解", value: lines, type: "breakdown" });
  }

  return sections;
}

function ScoreBar({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const level = clamped >= 70 ? "high" : clamped >= 40 ? "mid" : "low";
  return (
    <div className="score-bar-container">
      <div className="score-bar">
        <div className={`score-bar-fill score-${level}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="score-bar-value">{score}</span>
    </div>
  );
}

function platformBadgeClass(platform: string) {
  return `platform-badge platform-${platform}`;
}

function StatusBadge({ status }: { status: string }) {
  const label = LEAD_STATUS_LABELS[status] || status;
  return <span className={`status-pill status-${status}`}>{label}</span>;
}

export default function LeadsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [items, setItems] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);
  const [detailLead, setDetailLead] = useState<Lead | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [statTotals, setStatTotals] = useState<Record<string, number>>({ all: 0, A: 0, B: 0, C: 0, D: 0 });
  const [filters, setFilters] = useState<LeadQueryParams>(() => {
    const sp = searchParams;
    return {
      lead_level: sp.get("lead_level") || "",
      demand_type: sp.get("demand_type") || "",
      platform: sp.get("platform") || "",
      status: sp.get("status") || "",
      source_type: sp.get("source_type") || "",
      keyword: sp.get("keyword") || "",
      source_post_id: sp.get("source_post_id") ? Number(sp.get("source_post_id")) : undefined,
      source_comment_id: sp.get("source_comment_id") ? Number(sp.get("source_comment_id")) : undefined,
      is_duplicate: sp.get("is_duplicate") || "",
    };
  });
  const [draftStatuses, setDraftStatuses] = useState<Record<number, string>>({});
  const [draftNotes, setDraftNotes] = useState<Record<number, string>>({});
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [convertingId, setConvertingId] = useState<number | null>(null);

  const hasItems = useMemo(() => items.length > 0, [items]);

  const activeSourcePostId = filters.source_post_id;
  const activeSourceCommentId = filters.source_comment_id;

  async function loadData(nextPage = page, nextFilters = filters) {
    setLoading(true);
    setError(null);

    try {
      const commonFilters = {
        demand_type: nextFilters.demand_type || undefined,
        platform: nextFilters.platform || undefined,
        status: nextFilters.status || undefined,
        source_type: nextFilters.source_type || undefined,
        keyword: nextFilters.keyword || undefined,
        source_post_id: nextFilters.source_post_id || undefined,
        source_comment_id: nextFilters.source_comment_id || undefined,
        is_duplicate: nextFilters.is_duplicate === "true" ? true : nextFilters.is_duplicate === "false" ? false : undefined,
      };

      const [listResult, allResult, aResult, bResult, cResult, dResult] = await Promise.all([
        getLeads({
          ...commonFilters,
          lead_level: nextFilters.lead_level || undefined,
          page: nextPage,
          page_size: pageSize,
        }),
        getLeads({ ...commonFilters, page: 1, page_size: 1 }),
        getLeads({ ...commonFilters, lead_level: "A", page: 1, page_size: 1 }),
        getLeads({ ...commonFilters, lead_level: "B", page: 1, page_size: 1 }),
        getLeads({ ...commonFilters, lead_level: "C", page: 1, page_size: 1 }),
        getLeads({ ...commonFilters, lead_level: "D", page: 1, page_size: 1 }),
      ]);

      setItems(listResult.items);
      setTotal(listResult.total);
      setPage(listResult.page);
      setStatTotals({
        all: allResult.total,
        A: aResult.total,
        B: bResult.total,
        C: cResult.total,
        D: dResult.total,
      });
      setDraftStatuses((current) => {
        const nextDrafts: Record<number, string> = {};
        listResult.items.forEach((lead) => {
          nextDrafts[lead.id] = current[lead.id] ?? lead.status;
        });
        return nextDrafts;
      });
      setDraftNotes((current) => {
        const nextNotes: Record<number, string> = {};
        listResult.items.forEach((lead) => {
          nextNotes[lead.id] = current[lead.id] ?? (lead.notes || "");
        });
        return nextNotes;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载线索失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(1, filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters() {
    setPage(1);
    await loadData(1, filters);
  }

  async function resetFilters() {
    const nextFilters: LeadQueryParams = {
      lead_level: "",
      demand_type: "",
      platform: "",
      status: "",
      source_type: "",
      keyword: "",
      source_post_id: undefined,
      source_comment_id: undefined,
      is_duplicate: "",
    };
    setFilters(nextFilters);
    setPage(1);
    await loadData(1, nextFilters);
  }

  async function handlePrevPage() {
    const nextPage = Math.max(1, page - 1);
    await loadData(nextPage, filters);
  }

  async function handleNextPage() {
    const nextPage = page + 1;
    await loadData(nextPage, filters);
  }

  async function handleViewEvidence(lead: Lead) {
    setDetailLead(lead);
    setDetailOpen(true);
    setDetailError(null);
    setDetailLoading(false);
  }

  async function handleUpdateStatus(lead: Lead) {
    const nextStatus = draftStatuses[lead.id] ?? lead.status;
    const nextNotes = draftNotes[lead.id] ?? lead.notes ?? "";
    if (nextStatus === lead.status && nextNotes === (lead.notes || "")) {
      return;
    }

    setBusyId(lead.id);
    setError(null);

    try {
      await updateLeadStatus(lead.id, nextStatus, nextNotes || null);
      showToast("success", "状态已更新", `线索 #${lead.id} 已更新为${LEAD_STATUS_LABELS[nextStatus] || nextStatus}`);
      await loadData(page, filters);
      if (detailLead?.id === lead.id) {
        setDetailLead({ ...lead, status: nextStatus, notes: nextNotes });
      }
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "更新线索状态失败");
      showToast("error", "更新失败", updateError instanceof Error ? updateError.message : "未知错误");
    } finally {
      setBusyId(null);
    }
  }

  async function handleExportCsv() {
    setExporting(true);
    setError(null);

    try {
      const blob = await exportLeadsCsv({
        lead_level: filters.lead_level || undefined,
        demand_type: filters.demand_type || undefined,
        platform: filters.platform || undefined,
        status: filters.status || undefined,
        source_type: filters.source_type || undefined,
        keyword: filters.keyword || undefined,
        source_post_id: filters.source_post_id || undefined,
        source_comment_id: filters.source_comment_id || undefined,
        is_duplicate: filters.is_duplicate === "true" ? true : filters.is_duplicate === "false" ? false : undefined,
      });
      downloadBlob(blob, "leads.csv");
      showToast("success", "导出成功", "CSV 文件已下载");
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "导出 CSV 失败");
      showToast("error", "导出失败", exportError instanceof Error ? exportError.message : "未知错误");
    } finally {
      setExporting(false);
    }
  }

  async function handleConvertToCrm(lead: Lead) {
    const ownerName = window.prompt("请输入负责人（可留空为未分配）", "");
    setConvertingId(lead.id);
    setError(null);
    try {
      const result = await convertLeadToCrm(lead.id, {
        owner_name: ownerName?.trim() || null,
      });
      showToast("success", "已转入 CRM", `客户：${result.customer.name}，已生成首跟进任务`);
      await loadData(page, filters);
      setDetailLead((current) =>
        current?.id === lead.id
          ? {
              ...current,
              crm_customer_id: result.customer.id,
              crm_opportunity_id: result.opportunity.id,
              converted_to_crm_at: new Date().toISOString(),
              status: "contacted",
            }
          : current,
      );
    } catch (convertError) {
      const message = convertError instanceof Error ? convertError.message : "转入 CRM 失败";
      setError(message);
      showToast("error", "转入 CRM 失败", message);
    } finally {
      setConvertingId(null);
    }
  }

  function handleGoToPost(lead: Lead) {
    if (lead.source_post_id) {
      navigate(`/posts?highlight=${lead.source_post_id}`);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">线索池</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看 A/B/C/D 级线索，核对证据链，修改状态并导出 CSV。</p>
        </div>
      </header>

      <section className="stats-grid">
        <div className="stat-card"><span>全部线索</span><strong>{statTotals.all}</strong></div>
        <div className="stat-card"><span>A 级线索</span><strong style={{ color: "#dc2626" }}>{statTotals.A}</strong></div>
        <div className="stat-card"><span>B 级线索</span><strong style={{ color: "#2563eb" }}>{statTotals.B}</strong></div>
        <div className="stat-card"><span>C 级线索</span><strong style={{ color: "#ca8a04" }}>{statTotals.C}</strong></div>
        <div className="stat-card"><span>D 级线索</span><strong style={{ color: "#6b7280" }}>{statTotals.D}</strong></div>
      </section>

      {activeSourcePostId ? (
        <div className="active-filter-hint">
          <span>已按来源帖子 ID={activeSourcePostId} 过滤</span>
          <button type="button" onClick={() => { setFilters((f) => ({ ...f, source_post_id: undefined })); void loadData(1, { ...filters, source_post_id: undefined }); }}>清除</button>
        </div>
      ) : null}
      {activeSourceCommentId ? (
        <div className="active-filter-hint">
          <span>已按来源评论 ID={activeSourceCommentId} 过滤</span>
          <button type="button" onClick={() => { setFilters((f) => ({ ...f, source_comment_id: undefined })); void loadData(1, { ...filters, source_comment_id: undefined }); }}>清除</button>
        </div>
      ) : null}

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>筛选条件</h2>
            <p>按线索等级、需求类型、平台和状态筛选。</p>
          </div>
          <div className="action-row">
            <button type="button" className="btn-primary" onClick={() => void applyFilters()} disabled={loading}>查询</button>
            <button type="button" className="btn-secondary" onClick={() => void resetFilters()} disabled={loading}>重置</button>
            <button type="button" className="btn-secondary" onClick={() => void handleExportCsv()} disabled={exporting}>
              {exporting ? "导出中..." : "导出 CSV"}
            </button>
          </div>
        </div>

        <div className="filter-grid">
          <label>
            <span>线索等级</span>
            <select value={filters.lead_level ?? ""} onChange={(event) => setFilters((current) => ({ ...current, lead_level: event.target.value }))}>
              {LEAD_LEVEL_OPTIONS.map((option) => (
                <option key={option || "all"} value={option}>
                  {option || "全部"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>需求类型</span>
            <input value={filters.demand_type ?? ""} onChange={(event) => setFilters((current) => ({ ...current, demand_type: event.target.value }))} placeholder="例如：借款需求" />
          </label>
          <label>
            <span>平台</span>
            <select value={filters.platform ?? ""} onChange={(event) => setFilters((current) => ({ ...current, platform: event.target.value }))}>
              {PLATFORM_OPTIONS.map((option) => (
                <option key={option || "all"} value={option}>
                  {option || "全部"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>状态</span>
            <select value={filters.status ?? ""} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}>
              {STATUS_OPTIONS.map((option) => (
                <option key={option || "all"} value={option}>
                  {LEAD_STATUS_LABELS[option] || "全部"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>重复筛选</span>
            <select value={String(filters.is_duplicate ?? "")} onChange={(event) => setFilters((current) => ({ ...current, is_duplicate: event.target.value }))}>
              {DUPLICATE_FILTER_OPTIONS.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>线索列表</h2>
            <p>当前页共 {items.length} 条，总计 {total} 条。</p>
          </div>
          <div className="action-row">
            <button type="button" className="btn-secondary" onClick={() => void loadData(page, filters)} disabled={loading}>刷新列表</button>
            <button type="button" className="btn-secondary" onClick={() => void handlePrevPage()} disabled={loading || page <= 1}>上一页</button>
            <button type="button" className="btn-secondary" onClick={() => void handleNextPage()} disabled={loading || items.length < pageSize}>下一页</button>
          </div>
        </div>

        {loading ? (
          <div style={{ display: "grid", gap: 8 }}>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton skeleton-card" />
            ))}
          </div>
        ) : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={() => void loadData(page, filters)}>重试</button>
          </div>
        ) : null}
        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty">
            <p>暂无线索。</p>
          </div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>等级</th>
                  <th>评分</th>
                  <th>需求类型</th>
                  <th>评论内容</th>
                  <th>平台</th>
                  <th>来源帖子</th>
                  <th>风险</th>
                  <th>重复</th>
                  <th>状态</th>
                  <th>备注</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((lead) => (
                  <tr key={lead.id}>
                    <td><span className={`lead-level level-${lead.lead_level}`}>{lead.lead_level}</span></td>
                    <td><ScoreBar score={lead.lead_score} /></td>
                    <td>{lead.demand_type ? <span className="tag">{lead.demand_type}</span> : "-"}</td>
                    <td className="cell-break">{truncate(lead.content, 40)}</td>
                    <td><span className={platformBadgeClass(lead.platform)}>{PLATFORM_LABELS[lead.platform] || lead.platform}</span></td>
                    <td>
                      {lead.source_post_title ? (
                        <div className="source-post-cell">
                          <span className="cell-break" title={lead.source_post_title}>{truncate(lead.source_post_title, 20)}</span>
                          <div className="source-post-actions">
                            {lead.source_post_url ? (
                              <a href={lead.source_post_url} target="_blank" rel="noreferrer">原链接</a>
                            ) : null}
                            <button type="button" className="btn-sm" onClick={() => handleGoToPost(lead)}>帖子池</button>
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td>
                      {lead.risk_level === "high" ? (
                        <span className="tag tag-danger">高</span>
                      ) : lead.risk_level === "mid" ? (
                        <span className="tag tag-warning">中</span>
                      ) : lead.risk_level === "low" ? (
                        <span className="tag tag-success">低</span>
                      ) : "-"}
                    </td>
                    <td>
                      {lead.is_duplicate ? (
                        <span className="tag tag-warning" title={lead.duplicate_reason || ""}>重复</span>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="cell-break">{truncate(lead.notes, 20)}</td>
                    <td>
                      <div className="lead-actions">
                        <button type="button" className="btn-primary btn-sm" onClick={() => void handleViewEvidence(lead)}>查看详情</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {detailOpen && detailLead ? (() => {
        const matchedWords = getMatchedWords(detailLead.evidence);
        const amounts = getAmounts(detailLead.evidence);
        const scoreBreakdown = getScoreBreakdown(detailLead.evidence);
        const evidenceSections = buildEvidenceSections(detailLead.evidence);
        const hasEvidence = evidenceSections.length > 0;

        return (
          <div className="modal-backdrop" role="presentation" onClick={() => setDetailOpen(false)}>
            <div className="drawer-card" role="dialog" aria-modal="true" aria-label="线索详情" onClick={(event) => event.stopPropagation()}>
              <div className="drawer-header">
                <div className="drawer-header-left">
                  <h3>线索详情</h3>
                  <p className="drawer-subtitle">
                    <span className={`lead-level level-${detailLead.lead_level}`}>{detailLead.lead_level}</span>
                    <span className="drawer-subtitle-sep">·</span>
                    <span>评分 <strong>{detailLead.lead_score}</strong></span>
                    <span className="drawer-subtitle-sep">·</span>
                    <span className={platformBadgeClass(detailLead.platform)}>{PLATFORM_LABELS[detailLead.platform] || detailLead.platform}</span>
                    <span className="drawer-subtitle-sep">·</span>
                    <span className="text-muted">ID: {detailLead.id}</span>
                  </p>
                </div>
                <button type="button" className="drawer-close-btn" onClick={() => setDetailOpen(false)}>✕</button>
              </div>

              {detailLoading ? <p className="state-text">加载中...</p> : null}
              {detailError ? <p className="inline-error">{detailError}</p> : null}

              {!detailLoading && !detailError ? (
                <div className="drawer-body">
                  <section className="drawer-section">
                    <div className="card-header-row">
                      <div>
                        <h4 className="drawer-section-title">CRM 转化</h4>
                        <p className="text-muted">
                          {detailLead.crm_customer_id ? "该线索已进入 CRM，可继续推进客户和商机。" : "确认有效后可人工转入 CRM，并自动生成客户、商机和首跟进任务。"}
                        </p>
                      </div>
                      {detailLead.crm_customer_id ? (
                        <button type="button" className="btn-secondary btn-sm" onClick={() => navigate("/crm/customers")}>
                          查看 CRM
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          onClick={() => void handleConvertToCrm(detailLead)}
                          disabled={convertingId === detailLead.id}
                        >
                          {convertingId === detailLead.id ? "转入中..." : "转入 CRM"}
                        </button>
                      )}
                    </div>
                  </section>
                  <section className="drawer-section">
                    <h4 className="drawer-section-title">基本信息</h4>
                    <div className="detail-grid compact">
                      <div className="detail-field">
                        <span className="detail-label">用户名</span>
                        <strong className="detail-value">{detailLead.user_name || "-"}</strong>
                      </div>
                      <div className="detail-field">
                        <span className="detail-label">来源平台</span>
                        <strong className="detail-value"><span className={platformBadgeClass(detailLead.platform)}>{PLATFORM_LABELS[detailLead.platform] || detailLead.platform}</span></strong>
                      </div>
                      <div className="detail-field">
                        <span className="detail-label">需求类型</span>
                        <strong className="detail-value">{detailLead.demand_type ? <span className="tag">{detailLead.demand_type}</span> : "-"}</strong>
                      </div>
                      <div className="detail-field">
                        <span className="detail-label">风险等级</span>
                        <strong className="detail-value">
                          {detailLead.risk_level === "high" ? (
                            <span className="tag tag-danger">高风险</span>
                          ) : detailLead.risk_level === "mid" ? (
                            <span className="tag tag-warning">中风险</span>
                          ) : detailLead.risk_level === "low" ? (
                            <span className="tag tag-success">低风险</span>
                          ) : "-"}
                        </strong>
                      </div>
                      <div className="detail-field">
                        <span className="detail-label">重复标记</span>
                        <strong className="detail-value">
                          {detailLead.is_duplicate ? (
                            <span className="tag tag-warning">疑似重复</span>
                          ) : (
                            <span className="tag tag-success">非重复</span>
                          )}
                        </strong>
                      </div>
                    </div>
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">来源帖子</h4>
                    <div className="detail-grid compact">
                      <div className="detail-field">
                        <span className="detail-label">帖子标题</span>
                        <strong className="detail-value">{detailLead.source_post_title || "-"}</strong>
                      </div>
                      <div className="detail-field">
                        <span className="detail-label">帖子链接</span>
                        <strong className="detail-value">
                          {detailLead.source_post_url ? (
                            <a href={detailLead.source_post_url} target="_blank" rel="noreferrer">打开原帖 ↗</a>
                          ) : "-"}
                        </strong>
                      </div>
                    </div>
                    {detailLead.source_post_id ? (
                      <div style={{ marginTop: 8 }}>
                        <button type="button" className="btn-sm" onClick={() => { setDetailOpen(false); handleGoToPost(detailLead); }}>在帖子池中查看</button>
                      </div>
                    ) : null}
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">评论原文</h4>
                    <div className="detail-comment-box">
                      {highlightKeywords(detailLead.content, matchedWords)}
                    </div>
                    {detailLead.is_duplicate && detailLead.duplicate_reason ? (
                      <div className="duplicate-info-box">
                        <span className="tag tag-warning">重复原因</span>
                        <span className="duplicate-reason-text">{detailLead.duplicate_reason}</span>
                        {detailLead.duplicate_group_id ? (
                          <span className="duplicate-group-id">组: {detailLead.duplicate_group_id}</span>
                        ) : null}
                      </div>
                    ) : null}
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">线索评分</h4>
                    <div className="detail-score-area">
                      <div className="detail-score-header">
                        <span className={`lead-level level-${detailLead.lead_level} lead-level-lg`}>{detailLead.lead_level}级</span>
                        <ScoreBar score={detailLead.lead_score} />
                      </div>
                      {scoreBreakdown ? (
                        <div className="score-breakdown-grid">
                          {Object.entries(scoreBreakdown).map(([key, val]) => (
                            <div key={key} className="score-breakdown-item">
                              <span>{DIMENSION_LABELS[key] || key}</span>
                              <span className={val > 0 ? "score-positive" : val < 0 ? "score-negative" : "score-zero"}>
                                {val > 0 ? "+" : ""}{val}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">判断理由</h4>
                    <div className="detail-text-block">
                      {detailLead.reason || "暂无判断理由"}
                    </div>
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">跟进话术</h4>
                    <div className="detail-text-block detail-text-block-accent">
                      {detailLead.follow_up_script || "暂无跟进话术"}
                    </div>
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">证据链</h4>
                    {hasEvidence ? (
                      <div className="evidence-list">
                        {matchedWords.length > 0 ? (
                          <div className="evidence-block">
                            <h4>命中关键词</h4>
                            <div className="evidence-tags">
                              {matchedWords.map((word) => (
                                <span key={word} className="tag tag-keyword">{word}</span>
                              ))}
                            </div>
                          </div>
                        ) : null}
                        {amounts.length > 0 ? (
                          <div className="evidence-block">
                            <h4>金额信息</h4>
                            <div className="evidence-tags">
                              {amounts.map((amt) => (
                                <span key={amt} className="tag tag-amount">{amt}</span>
                              ))}
                            </div>
                          </div>
                        ) : null}
                        {evidenceSections
                          .filter((s) => s.type === "warning")
                          .map((section) => (
                            <div key={section.title} className="evidence-block">
                              <h4>{section.title}</h4>
                              <div className="evidence-warning">{section.value}</div>
                            </div>
                          ))}
                        {evidenceSections
                          .filter((s) => s.type === "danger")
                          .map((section) => (
                            <div key={section.title} className="evidence-block">
                              <h4>{section.title}</h4>
                              <div className="evidence-danger">{section.value}</div>
                            </div>
                          ))}
                      </div>
                    ) : (
                      <div className="state-panel state-empty" style={{ padding: "16px" }}>
                        <p>暂无证据链</p>
                      </div>
                    )}
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">跟进状态</h4>
                    <div className="detail-status-row">
                      <div className="detail-status-select">
                        <label>
                          <span className="detail-label">当前状态</span>
                          <select
                            value={draftStatuses[detailLead.id] ?? detailLead.status}
                            onChange={(event) => setDraftStatuses((current) => ({ ...current, [detailLead.id]: event.target.value }))}
                          >
                            {Object.entries(LEAD_STATUS_LABELS).map(([status, label]) => (
                              <option key={status} value={status}>{label}</option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <div className="detail-status-action">
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          onClick={() => void handleUpdateStatus(detailLead)}
                          disabled={busyId === detailLead.id}
                        >
                          {busyId === detailLead.id ? "保存中..." : "保存状态"}
                        </button>
                      </div>
                    </div>
                  </section>

                  <section className="drawer-section">
                    <h4 className="drawer-section-title">备注</h4>
                    <textarea
                      className="detail-notes-textarea"
                      value={draftNotes[detailLead.id] ?? detailLead.notes ?? ""}
                      onChange={(event) => setDraftNotes((current) => ({ ...current, [detailLead.id]: event.target.value }))}
                      placeholder="添加备注信息..."
                      rows={3}
                    />
                    <div style={{ marginTop: 8 }}>
                      <button
                        type="button"
                        className="btn-primary btn-sm"
                        onClick={() => void handleUpdateStatus(detailLead)}
                        disabled={busyId === detailLead.id}
                      >
                        {busyId === detailLead.id ? "保存中..." : "保存备注"}
                      </button>
                    </div>
                  </section>
                </div>
              ) : null}
            </div>
          </div>
        );
      })() : null}
    </main>
  );
}
