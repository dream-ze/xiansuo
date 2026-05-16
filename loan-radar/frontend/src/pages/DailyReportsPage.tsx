import { useEffect, useState } from "react";
import {
  type DailyReport,
  generateDailyReport,
  getTodayReport,
} from "../api/client";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="report-section">
      <h2 className="report-section-title">{title}</h2>
      {children}
    </div>
  );
}

function StringList({ items }: { items: string[] }) {
  if (!items || items.length === 0) return <p className="empty-hint">暂无数据</p>;
  return (
    <ul className="report-list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

function DemandList({ items }: { items: Array<{ name: string; count: number }> }) {
  if (!items || items.length === 0) return <p className="empty-hint">暂无数据</p>;
  return (
    <ol className="report-ranked-list">
      {items.map((item, i) => (
        <li key={i}>
          <span className="rank-name">{item.name}</span>
          <span className="rank-count">{item.count} 次</span>
        </li>
      ))}
    </ol>
  );
}

function KeywordList({ items }: { items: Array<{ word: string; count: number }> }) {
  if (!items || items.length === 0) return <p className="empty-hint">暂无数据</p>;
  return (
    <div className="keyword-tags">
      {items.map((item, i) => (
        <span key={i} className="keyword-tag">
          {item.word} <em>{item.count}</em>
        </span>
      ))}
    </div>
  );
}

type HotPost = { title?: string; platform?: string; content?: string; like_count?: number; comment_count?: number };

function HotPostList({ items }: { items: HotPost[] }) {
  if (!items || items.length === 0) return <p className="empty-hint">暂无数据</p>;
  return (
    <div className="hot-post-list">
      {items.map((post, i) => (
        <div key={i} className="hot-post-card">
          <div className="hot-post-header">
            <span className="hot-post-rank">#{i + 1}</span>
            {post.platform && <span className="badge">{post.platform}</span>}
          </div>
          {post.title && <p className="hot-post-title">{post.title}</p>}
          {post.content && <p className="hot-post-content">{post.content}</p>}
          <div className="hot-post-meta">
            {post.like_count != null && <span>👍 {post.like_count}</span>}
            {post.comment_count != null && <span>💬 {post.comment_count}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

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
        return {
          name: String(item[0] ?? ""),
          count: Number(item[1] ?? 0),
        };
      }

      if (item && typeof item === "object") {
        const typed = item as Record<string, unknown>;
        const name = typed.demand_type ?? typed.name;
        const count = typed.count;
        if (name !== undefined && count !== undefined) {
          return {
            name: String(name),
            count: Number(count),
          };
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
        return {
          word: String(item[0] ?? ""),
          count: Number(item[1] ?? 0),
        };
      }

      if (item && typeof item === "object") {
        const typed = item as Record<string, unknown>;
        const word = typed.keyword ?? typed.word;
        const count = typed.count;
        if (word !== undefined && count !== undefined) {
          return {
            word: String(word),
            count: Number(count),
          };
        }
      }

      return null;
    })
    .filter((item): item is { word: string; count: number } => item !== null);
}

export default function DailyReportsPage() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchTodayReport() {
    setLoading(true);
    setError(null);
    try {
      const data = await getTodayReport();
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
      const data = await generateDailyReport();
      setReport(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  }

  const topDemands = normalizeRankItems(report?.top_demands);
  const topKeywords = normalizeKeywordItems(report?.top_keywords);
  const hotPosts = parseJsonField<HotPost[]>(report?.hot_posts);
  const contentSuggestions = parseJsonField<string[]>(report?.content_suggestions);
  const followUpSuggestions = parseJsonField<string[]>(report?.follow_up_suggestions);
  const riskWarnings = parseJsonField<string[]>(report?.risk_warnings);
  const aLeadDetails = parseJsonField<Array<{ id: number; platform: string; user_name: string; content: string; lead_score: number; demand_type: string; follow_up_script: string; reason: string }>>(report?.a_lead_details);
  const typicalEvidence = parseJsonField<Array<{ lead_id: number; platform: string; content: string; matched_words: string[]; amounts: string[]; lead_level: string }>>(report?.typical_evidence);
  const discoveredCompetitors = parseJsonField<Array<{ id: number; platform: string; account_name: string; competitor_score: number; status: string; discover_reason: string }>>(report?.discovered_competitors);
  const tomorrowSuggestions = parseJsonField<string[]>(report?.tomorrow_suggestions);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">今日获客报告</h1>
          {report && (
            <p className="page-subtitle">
              报告日期：{report.report_date} · 平台：{report.platform}
            </p>
          )}
        </div>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating || loading}>
            {generating ? "生成中..." : "生成今日报告"}
          </button>
          <button className="btn btn-secondary" onClick={fetchTodayReport} disabled={loading}>
            {loading ? "查询中..." : "刷新"}
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠ {error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {loading && (
        <div className="loading-state">
          <div className="loading-spinner" />
          <p>查询今日报告中...</p>
        </div>
      )}

      {!loading && !report && !error && (
        <div className="empty-state">
          <p className="empty-title">今日尚未生成报告</p>
          <p className="empty-desc">点击「生成今日报告」按钮，系统将基于今日采集数据生成报告。</p>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            {generating ? "生成中..." : "生成今日报告"}
          </button>
        </div>
      )}

      {!loading && report && (
        <div className="report-body">
          {/* 数据概览 */}
          <Section title="数据概览">
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{report.source_count}</div>
                <div className="stat-label">监控源</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{report.post_count}</div>
                <div className="stat-label">采集帖子</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{report.comment_count}</div>
                <div className="stat-label">采集评论</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{report.lead_count}</div>
                <div className="stat-label">识别线索</div>
              </div>
            </div>
            <div className="stats-grid report-lead-grid">
              <div className="stat-card stat-card-a">
                <div className="stat-value">{report.a_lead_count}</div>
                <div className="stat-label">A 级线索</div>
              </div>
              <div className="stat-card stat-card-b">
                <div className="stat-value">{report.b_lead_count}</div>
                <div className="stat-label">B 级线索</div>
              </div>
              <div className="stat-card stat-card-c">
                <div className="stat-value">{report.c_lead_count}</div>
                <div className="stat-label">C 级线索</div>
              </div>
              <div className="stat-card stat-card-d">
                <div className="stat-value">{report.d_lead_count}</div>
                <div className="stat-label">D 级线索</div>
              </div>
            </div>
          </Section>

          {/* 高频需求榜 */}
          <Section title="高频需求榜">
            <DemandList items={topDemands} />
          </Section>

          {/* 高频关键词 */}
          <Section title="高频关键词">
            <KeywordList items={topKeywords} />
          </Section>

          {/* 爆款帖子 */}
          <Section title="爆款帖子">
            <HotPostList items={hotPosts ?? []} />
          </Section>

          {/* 明日内容建议 */}
          <Section title="明日内容建议">
            <StringList items={contentSuggestions ?? []} />
          </Section>

          {/* 销售跟进建议 */}
          <Section title="销售跟进建议">
            <StringList items={followUpSuggestions ?? []} />
          </Section>

          {/* 合规风险提醒 */}
          <Section title="合规风险提醒">
            <StringList items={riskWarnings ?? []} />
          </Section>

          {/* A级线索详情 */}
          {aLeadDetails && aLeadDetails.length > 0 && (
            <Section title="A级线索详情">
              <div className="hot-post-list">
                {aLeadDetails.map((lead, i) => (
                  <div key={lead.id || i} className="hot-post-card">
                    <div className="hot-post-header">
                      <span className="hot-post-rank">#{i + 1}</span>
                      <span className="badge">{lead.platform}</span>
                      <span className="badge">评分: {lead.lead_score}</span>
                    </div>
                    {lead.user_name && <p className="hot-post-title">用户：{lead.user_name}</p>}
                    <p className="hot-post-content">{lead.content}</p>
                    {lead.demand_type && <p><strong>需求类型：</strong>{lead.demand_type}</p>}
                    {lead.reason && <p><strong>判断理由：</strong>{lead.reason}</p>}
                    {lead.follow_up_script && <p><strong>建议话术：</strong>{lead.follow_up_script}</p>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* 典型证据 */}
          {typicalEvidence && typicalEvidence.length > 0 && (
            <Section title="典型证据">
              <div className="hot-post-list">
                {typicalEvidence.map((ev, i) => (
                  <div key={ev.lead_id || i} className="hot-post-card">
                    <div className="hot-post-header">
                      <span className="hot-post-rank">#{i + 1}</span>
                      <span className="badge">{ev.platform}</span>
                      <span className={`badge ${ev.lead_level === 'A' ? 'badge-danger' : 'badge-warning'}`}>{ev.lead_level}级</span>
                    </div>
                    <p className="hot-post-content">{ev.content}</p>
                    {ev.matched_words && ev.matched_words.length > 0 && (
                      <div className="keyword-tags" style={{ marginTop: 4 }}>
                        {ev.matched_words.map((w, j) => (
                          <span key={j} className="keyword-tag">{w}</span>
                        ))}
                      </div>
                    )}
                    {ev.amounts && ev.amounts.length > 0 && (
                      <p style={{ marginTop: 4, fontSize: 12, color: '#666' }}>金额：{ev.amounts.join(', ')}</p>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* 发现的同行账号 */}
          {discoveredCompetitors && discoveredCompetitors.length > 0 && (
            <Section title="发现的同行账号">
              <div className="hot-post-list">
                {discoveredCompetitors.map((comp, i) => (
                  <div key={comp.id || i} className="hot-post-card">
                    <div className="hot-post-header">
                      <span className="hot-post-rank">#{i + 1}</span>
                      <span className="badge">{comp.platform}</span>
                      <span className="badge">评分: {comp.competitor_score}</span>
                      <span className={`badge ${comp.status === 'approved' ? 'badge-success' : comp.status === 'ignored' ? 'badge-muted' : 'badge-warning'}`}>
                        {comp.status === 'approved' ? '已通过' : comp.status === 'ignored' ? '已忽略' : '待审核'}
                      </span>
                    </div>
                    <p className="hot-post-title">{comp.account_name}</p>
                    {comp.discover_reason && <p className="hot-post-content">{comp.discover_reason}</p>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* 明日建议 */}
          {tomorrowSuggestions && tomorrowSuggestions.length > 0 && (
            <Section title="明日建议">
              <StringList items={tomorrowSuggestions} />
            </Section>
          )}
        </div>
      )}
    </div>
  );
}
