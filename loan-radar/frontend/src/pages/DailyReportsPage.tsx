import { useEffect, useState, useRef } from "react";
import {
  type DailyReport,
  generateDailyReport,
  getTodayReport,
  exportDailyReport,
} from "../api/client";

const PLATFORM_OPTIONS = [
  { value: "", label: "全平台" },
  { value: "xhs", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];

const PLATFORM_LABELS: Record<string, string> = {
  all: "全平台",
  xhs: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
};

type ALeadDetail = {
  id: number;
  platform: string;
  user_name: string;
  content: string;
  lead_score: number;
  demand_type: string;
  follow_up_script: string;
  reason: string;
};

type TypicalEvidence = {
  lead_id: number;
  platform: string;
  content: string;
  matched_words: string[];
  amounts: string[];
  lead_level: string;
};

type DiscoveredCompetitor = {
  id: number;
  platform: string;
  account_name: string;
  competitor_score: number;
  status: string;
  discover_reason: string;
  suggest_monitor: boolean;
};

type TomorrowSuggestions = {
  recommended_keywords: string[];
  competitor_directions: string[];
  content_topics: string[];
  follow_up_hints: string[];
};

function parseJsonField<T>(value: unknown): T | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as T;
    } catch {
      return null;
    }
  }
  return value as T;
}

function normalizeRankItems(value: unknown): Array<{ name: string; count: number }> {
  const parsed = parseJsonField<unknown[]>(value);
  if (!parsed || !Array.isArray(parsed)) return [];
  return parsed
    .map((item) => {
      if (Array.isArray(item) && item.length >= 2) {
        return { name: String(item[0] ?? ""), count: Number(item[1] ?? 0) };
      }
      if (item && typeof item === "object") {
        const typed = item as Record<string, unknown>;
        const name = typed.demand_type ?? typed.name;
        const count = typed.count;
        if (name !== undefined && count !== undefined) {
          return { name: String(name), count: Number(count) };
        }
      }
      return null;
    })
    .filter((item): item is { name: string; count: number } => item !== null);
}

function normalizeKeywordItems(value: unknown): Array<{ word: string; count: number }> {
  const parsed = parseJsonField<unknown[]>(value);
  if (!parsed || !Array.isArray(parsed)) return [];
  return parsed
    .map((item) => {
      if (Array.isArray(item) && item.length >= 2) {
        return { word: String(item[0] ?? ""), count: Number(item[1] ?? 0) };
      }
      if (item && typeof item === "object") {
        const typed = item as Record<string, unknown>;
        const word = typed.keyword ?? typed.word;
        const count = typed.count;
        if (word !== undefined && count !== undefined) {
          return { word: String(word), count: Number(count) };
        }
      }
      return null;
    })
    .filter((item): item is { word: string; count: number } => item !== null);
}

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <section className="rpt-section">
      <h2 className="rpt-section-title">
        <span className="rpt-section-icon">{icon}</span>
        {title}
      </h2>
      <div className="rpt-section-body">{children}</div>
    </section>
  );
}

function EmptyHint({ text }: { text: string }) {
  return <p className="rpt-empty">{text}</p>;
}

export default function DailyReportsPage() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [platform, setPlatform] = useState("");
  const [copyOk, setCopyOk] = useState(false);
  const [exporting, setExporting] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);

  async function fetchTodayReport() {
    setLoading(true);
    setError(null);
    try {
      const data = await getTodayReport(platform || undefined);
      setReport(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("404") || msg.includes("Not Found") || msg.includes("not found")) {
        setReport(null);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchTodayReport();
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateDailyReport(platform || undefined);
      setReport(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  }

  function handlePlatformChange(value: string) {
    setPlatform(value);
    setReport(null);
  }

  async function handleRefresh() {
    await fetchTodayReport();
  }

  const topDemands = normalizeRankItems(report?.top_demands);
  const topKeywords = normalizeKeywordItems(report?.top_keywords);
  const riskWarnings = parseJsonField<string[]>(report?.risk_warnings);
  const aLeadDetails = parseJsonField<ALeadDetail[]>(report?.a_lead_details);
  const typicalEvidence = parseJsonField<TypicalEvidence[]>(report?.typical_evidence);
  const discoveredCompetitors = parseJsonField<DiscoveredCompetitor[]>(report?.discovered_competitors);
  const tomorrowSuggestions = parseJsonField<TomorrowSuggestions>(report?.tomorrow_suggestions);

  function buildSummaryText(): string {
    if (!report) return "";
    const lines: string[] = [];
    lines.push(`【今日获客报告 ${report.report_date} ${PLATFORM_LABELS[report.platform] || report.platform}】`);
    lines.push("");
    lines.push("一、今日扫描概况");
    lines.push(`  监控源：${report.source_count} 个`);
    lines.push(`  帖子：${report.post_count} 条`);
    lines.push(`  评论：${report.comment_count} 条`);
    lines.push(`  线索：${report.lead_count} 条（A级 ${report.a_lead_count} / B级 ${report.b_lead_count} / C级 ${report.c_lead_count} / D级 ${report.d_lead_count}）`);
    lines.push("");

    if (aLeadDetails && aLeadDetails.length > 0) {
      lines.push("二、A级线索 Top 10");
      aLeadDetails.forEach((lead, i) => {
        lines.push(`  ${i + 1}. [${PLATFORM_LABELS[lead.platform] || lead.platform}] ${lead.user_name || "匿名用户"}`);
        lines.push(`     内容：${lead.content.slice(0, 80)}`);
        lines.push(`     需求：${lead.demand_type} | 评分：${lead.lead_score}`);
        lines.push(`     话术：${lead.follow_up_script}`);
      });
      lines.push("");
    }

    if (typicalEvidence && typicalEvidence.length > 0) {
      lines.push("三、典型需求证据");
      typicalEvidence.forEach((ev, i) => {
        lines.push(`  ${i + 1}. 命中词：${ev.matched_words.join("、")}${ev.amounts.length > 0 ? ` | 金额：${ev.amounts.join("、")}` : ""}`);
      });
      lines.push("");
    }

    if (topDemands.length > 0) {
      lines.push("高频需求：" + topDemands.map((d) => `${d.name}(${d.count})`).join("、"));
      lines.push("");
    }

    if (discoveredCompetitors && discoveredCompetitors.length > 0) {
      lines.push("四、同行账号发现");
      discoveredCompetitors.forEach((c, i) => {
        lines.push(`  ${i + 1}. ${c.account_name}（${PLATFORM_LABELS[c.platform] || c.platform}）- ${c.suggest_monitor ? "建议监控" : "暂不监控"}`);
      });
      lines.push("");
    }

    if (tomorrowSuggestions) {
      lines.push("五、明日采集建议");
      if (tomorrowSuggestions.recommended_keywords.length > 0) {
        lines.push(`  推荐关键词：${tomorrowSuggestions.recommended_keywords.join("、")}`);
      }
      if (tomorrowSuggestions.competitor_directions.length > 0) {
        tomorrowSuggestions.competitor_directions.forEach((d) => lines.push(`  同行方向：${d}`));
      }
      if (tomorrowSuggestions.content_topics.length > 0) {
        tomorrowSuggestions.content_topics.forEach((t) => lines.push(`  内容选题：${t}`));
      }
      lines.push("");
    }

    if (riskWarnings && riskWarnings.length > 0) {
      lines.push("六、合规提醒");
      riskWarnings.forEach((w) => lines.push(`  · ${w}`));
    }

    return lines.join("\n");
  }

  async function handleCopySummary() {
    const text = buildSummaryText();
    try {
      await navigator.clipboard.writeText(text);
      setCopyOk(true);
      setTimeout(() => setCopyOk(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopyOk(true);
      setTimeout(() => setCopyOk(false), 2000);
    }
  }

  async function handleExport() {
    if (!report) return;
    setExporting(true);
    try {
      const blob = await exportDailyReport("markdown", platform || undefined);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `loan-radar-report-${report.report_date}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Daily Report</p>
          <h1>今日获客报告</h1>
          {report && (
            <p className="page-description">
              {report.report_date} · {PLATFORM_LABELS[report.platform] || report.platform}
            </p>
          )}
        </div>
        <div className="rpt-header-actions">
          <label className="rpt-platform-select">
            <span>平台</span>
            <select value={platform} onChange={(e) => handlePlatformChange(e.target.value)}>
              {PLATFORM_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating || loading}>
            {generating ? "生成中..." : "生成今日报告"}
          </button>
          <button className="btn btn-secondary" onClick={handleRefresh} disabled={loading}>
            刷新
          </button>
          {report && (
            <button className="btn btn-secondary" onClick={handleCopySummary}>
              {copyOk ? "已复制" : "复制摘要"}
            </button>
          )}
          {report && (
            <button className="btn btn-secondary" onClick={handleExport} disabled={exporting}>
              {exporting ? "导出中..." : "导出 Markdown"}
            </button>
          )}
        </div>
      </header>

      {error && (
        <div className="state-panel state-error">
          <span>{error}</span>
          <button className="btn-sm" onClick={() => setError(null)} style={{ marginLeft: "auto" }}>关闭</button>
        </div>
      )}

      {loading && <p className="state-text">查询今日报告中...</p>}

      {!loading && !report && !error && (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <p style={{ fontSize: 18, fontWeight: 600, margin: "0 0 8px" }}>今日尚未生成报告</p>
          <p style={{ color: "#6b7280", margin: "0 0 20px" }}>点击「生成今日报告」，系统将基于今日采集数据生成可交付的客户报告。</p>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            {generating ? "生成中..." : "生成今日报告"}
          </button>
        </div>
      )}

      {!loading && report && (
        <div className="rpt-body" ref={reportRef}>
          <Section title="今日扫描概况" icon="📊">
            <div className="rpt-stats-row">
              <div className="rpt-stat">
                <div className="rpt-stat-value">{report.source_count}</div>
                <div className="rpt-stat-label">监控源</div>
              </div>
              <div className="rpt-stat">
                <div className="rpt-stat-value">{report.post_count}</div>
                <div className="rpt-stat-label">帖子</div>
              </div>
              <div className="rpt-stat">
                <div className="rpt-stat-value">{report.comment_count}</div>
                <div className="rpt-stat-label">评论</div>
              </div>
              <div className="rpt-stat">
                <div className="rpt-stat-value">{report.lead_count}</div>
                <div className="rpt-stat-label">线索</div>
              </div>
              <div className="rpt-stat rpt-stat-highlight">
                <div className="rpt-stat-value">{report.a_lead_count}</div>
                <div className="rpt-stat-label">A级线索</div>
              </div>
            </div>
            <div className="rpt-level-bar">
              <div className="rpt-level-item rpt-level-a" style={{ flex: report.a_lead_count || 0 }}>A</div>
              <div className="rpt-level-item rpt-level-b" style={{ flex: report.b_lead_count || 0 }}>B</div>
              <div className="rpt-level-item rpt-level-c" style={{ flex: report.c_lead_count || 0 }}>C</div>
              <div className="rpt-level-item rpt-level-d" style={{ flex: report.d_lead_count || 0 }}>D</div>
            </div>
            <div className="rpt-level-legend">
              <span className="rpt-level-dot rpt-level-a" /> A级 {report.a_lead_count}
              <span className="rpt-level-dot rpt-level-b" /> B级 {report.b_lead_count}
              <span className="rpt-level-dot rpt-level-c" /> C级 {report.c_lead_count}
              <span className="rpt-level-dot rpt-level-d" /> D级 {report.d_lead_count}
            </div>
          </Section>

          <Section title="A级线索 Top 10" icon="⭐">
            {!aLeadDetails || aLeadDetails.length === 0 ? (
              <EmptyHint text="今日暂无A级线索" />
            ) : (
              <div className="rpt-lead-list">
                {aLeadDetails.map((lead, i) => (
                  <div key={lead.id || i} className="rpt-lead-card">
                    <div className="rpt-lead-header">
                      <span className="rpt-lead-rank">#{i + 1}</span>
                      <span className={`platform-badge platform-${lead.platform}`}>
                        {PLATFORM_LABELS[lead.platform] || lead.platform}
                      </span>
                      <span className="rpt-lead-score">评分 {lead.lead_score}</span>
                    </div>
                    <div className="rpt-lead-user">{lead.user_name || "匿名用户"}</div>
                    <div className="rpt-lead-content">{lead.content}</div>
                    <div className="rpt-lead-meta">
                      {lead.demand_type && <span className="tag">{lead.demand_type}</span>}
                    </div>
                    {lead.reason && (
                      <div className="rpt-lead-field">
                        <span className="rpt-field-label">判断理由</span>
                        <span>{lead.reason}</span>
                      </div>
                    )}
                    {lead.follow_up_script && (
                      <div className="rpt-lead-field rpt-lead-script">
                        <span className="rpt-field-label">建议话术</span>
                        <span>{lead.follow_up_script}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="典型需求证据" icon="🔍">
            {(!typicalEvidence || typicalEvidence.length === 0) && topDemands.length === 0 ? (
              <EmptyHint text="今日暂无需求证据" />
            ) : (
              <>
                {typicalEvidence && typicalEvidence.length > 0 && (
                  <div className="rpt-evidence-list">
                    {typicalEvidence.map((ev, i) => (
                      <div key={ev.lead_id || i} className="rpt-evidence-card">
                        <div className="rpt-evidence-header">
                          <span className="rpt-lead-rank">#{i + 1}</span>
                          <span className={`platform-badge platform-${ev.platform}`}>
                            {PLATFORM_LABELS[ev.platform] || ev.platform}
                          </span>
                          <span className={`tag ${ev.lead_level === "A" ? "tag-danger" : "tag-warning"}`}>
                            {ev.lead_level}级
                          </span>
                        </div>
                        <div className="rpt-lead-content">{ev.content}</div>
                        <div className="rpt-evidence-tags">
                          {ev.matched_words && ev.matched_words.length > 0 && (
                            <div className="rpt-evidence-group">
                              <span className="rpt-field-label">命中关键词</span>
                              <div className="rpt-tag-row">
                                {ev.matched_words.map((w, j) => (
                                  <span key={j} className="keyword-tag">{w}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {ev.amounts && ev.amounts.length > 0 && (
                            <div className="rpt-evidence-group">
                              <span className="rpt-field-label">金额信息</span>
                              <div className="rpt-tag-row">
                                {ev.amounts.map((a, j) => (
                                  <span key={j} className="tag tag-warning">{a}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {topDemands.length > 0 && (
                  <div className="rpt-demands-section">
                    <h3 className="rpt-sub-title">高频需求</h3>
                    <div className="rpt-demand-bar-list">
                      {topDemands.map((d, i) => {
                        const maxCount = topDemands[0]?.count || 1;
                        const pct = Math.round((d.count / maxCount) * 100);
                        return (
                          <div key={i} className="rpt-demand-bar-item">
                            <span className="rpt-demand-name">{d.name}</span>
                            <div className="rpt-demand-bar-track">
                              <div className="rpt-demand-bar-fill" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="rpt-demand-count">{d.count}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {topKeywords.length > 0 && (
                  <div className="rpt-demands-section" style={{ marginTop: 16 }}>
                    <h3 className="rpt-sub-title">高频关键词</h3>
                    <div className="keyword-tags">
                      {topKeywords.map((kw, i) => (
                        <span key={i} className="keyword-tag">
                          {kw.word} <em>{kw.count}</em>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </Section>

          <Section title="同行账号发现" icon="👥">
            {!discoveredCompetitors || discoveredCompetitors.length === 0 ? (
              <EmptyHint text="今日暂无同行账号发现" />
            ) : (
              <div className="rpt-competitor-list">
                {discoveredCompetitors.map((comp, i) => (
                  <div key={comp.id || i} className="rpt-competitor-card">
                    <div className="rpt-competitor-header">
                      <span className="rpt-lead-rank">#{i + 1}</span>
                      <span className={`platform-badge platform-${comp.platform}`}>
                        {PLATFORM_LABELS[comp.platform] || comp.platform}
                      </span>
                      <span className="rpt-competitor-score">评分 {comp.competitor_score}</span>
                      {comp.suggest_monitor ? (
                        <span className="tag tag-warning">建议监控</span>
                      ) : (
                        <span className="tag">暂不监控</span>
                      )}
                    </div>
                    <div className="rpt-competitor-name">{comp.account_name}</div>
                    {comp.discover_reason && (
                      <div className="rpt-lead-field">
                        <span className="rpt-field-label">发现原因</span>
                        <span>{comp.discover_reason}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="明日采集建议" icon="📋">
            {!tomorrowSuggestions ? (
              <EmptyHint text="暂无建议" />
            ) : (
              <div className="rpt-tomorrow-grid">
                <div className="rpt-tomorrow-block">
                  <h3 className="rpt-sub-title">推荐关键词</h3>
                  {tomorrowSuggestions.recommended_keywords.length > 0 ? (
                    <div className="keyword-tags">
                      {tomorrowSuggestions.recommended_keywords.map((kw, i) => (
                        <span key={i} className="keyword-tag">{kw}</span>
                      ))}
                    </div>
                  ) : (
                    <EmptyHint text="暂无推荐" />
                  )}
                </div>
                <div className="rpt-tomorrow-block">
                  <h3 className="rpt-sub-title">推荐同行方向</h3>
                  {tomorrowSuggestions.competitor_directions.length > 0 ? (
                    <ul className="rpt-bullet-list">
                      {tomorrowSuggestions.competitor_directions.map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  ) : (
                    <EmptyHint text="暂无推荐" />
                  )}
                </div>
                <div className="rpt-tomorrow-block">
                  <h3 className="rpt-sub-title">推荐内容选题</h3>
                  {tomorrowSuggestions.content_topics.length > 0 ? (
                    <ul className="rpt-bullet-list">
                      {tomorrowSuggestions.content_topics.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  ) : (
                    <EmptyHint text="暂无推荐" />
                  )}
                </div>
                {tomorrowSuggestions.follow_up_hints.length > 0 && (
                  <div className="rpt-tomorrow-block">
                    <h3 className="rpt-sub-title">跟进提示</h3>
                    <ul className="rpt-bullet-list">
                      {tomorrowSuggestions.follow_up_hints.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Section>

          <Section title="合规提醒" icon="🛡️">
            {!riskWarnings || riskWarnings.length === 0 ? (
              <EmptyHint text="暂无提醒" />
            ) : (
              <ul className="rpt-warning-list">
                {riskWarnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      )}
    </main>
  );
}
