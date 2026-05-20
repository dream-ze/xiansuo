import {
  BarChartOutlined,
  CheckCircleOutlined,
  CloudDownloadOutlined,
  CopyOutlined,
  ReloadOutlined,
  TeamOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useState } from "react";

import { exportDailyReport, generateDailyReport, getTodayReport, type DailyReport } from "../api";

const { Title, Text, Paragraph } = Typography;

const PLATFORM_OPTIONS = [
  { value: "", label: "全平台" },
  { value: "xhs", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];
const PLATFORM_LABELS: Record<string, string> = { all: "全平台", xhs: "小红书", douyin: "抖音", zhihu: "知乎" };

type ALeadDetail = { id: number; platform: string; user_name: string; content: string; lead_score: number; demand_type: string; follow_up_script: string; reason: string };
type TypicalEvidence = { lead_id: number; platform: string; content: string; matched_words: string[]; amounts: string[]; lead_level: string };
type DiscoveredCompetitor = { id: number; platform: string; account_name: string; competitor_score: number; status: string; discover_reason: string; suggest_monitor: boolean };
type TomorrowSuggestions = { recommended_keywords: string[]; competitor_directions: string[]; content_topics: string[]; follow_up_hints: string[] };

function parseJsonField<T>(value: unknown): T | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") { try { return JSON.parse(value) as T; } catch { return null; } }
  return value as T;
}

export default function DailyReportsPage() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [platform, setPlatform] = useState("");
  const [copyOk, setCopyOk] = useState(false);
  const [exporting, setExporting] = useState(false);

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

  useEffect(() => { fetchTodayReport(); }, []);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateDailyReport(platform || undefined);
      setReport(data);
      message.success("今日获客报告已生成");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
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
      message.success("报告已下载");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  }

  async function handleCopySummary() {
    if (!report) return;
    const lines: string[] = [];
    lines.push(`【今日获客报告 ${report.report_date} ${PLATFORM_LABELS[report.platform] || report.platform}】`);
    lines.push("");
    lines.push("扫描概况：");
    lines.push(`  监控源 ${report.source_count} | 帖子 ${report.post_count} | 评论 ${report.comment_count} | 线索 ${report.lead_count}（A${report.a_lead_count}/B${report.b_lead_count}/C${report.c_lead_count}/D${report.d_lead_count}）`);
    const aLeads = parseJsonField<ALeadDetail[]>(report.a_lead_details);
    if (aLeads?.length) {
      lines.push("");
      lines.push("A级线索：");
      aLeads.forEach((l, i) => { lines.push(`  ${i + 1}. [${PLATFORM_LABELS[l.platform] || l.platform}] ${l.user_name || "匿名"} - ${l.content.slice(0, 60)}`); });
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopyOk(true);
      setTimeout(() => setCopyOk(false), 2000);
      message.success("已复制摘要");
    } catch {
      message.error("复制失败");
    }
  }

  const aLeadDetails = parseJsonField<ALeadDetail[]>(report?.a_lead_details);
  const typicalEvidence = parseJsonField<TypicalEvidence[]>(report?.typical_evidence);
  const discoveredCompetitors = parseJsonField<DiscoveredCompetitor[]>(report?.discovered_competitors);
  const tomorrowSuggestions = parseJsonField<TomorrowSuggestions>(report?.tomorrow_suggestions);
  const riskWarnings = parseJsonField<string[]>(report?.risk_warnings);

  const totalLeads = report ? report.a_lead_count + report.b_lead_count + report.c_lead_count + report.d_lead_count : 0;

  if (loading) {
    return <div style={{ display: "flex", justifyContent: "center", padding: 120 }}><Spin size="large" /></div>;
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 48px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <Text type="secondary" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}>获客报告</Text>
          <Title level={2} style={{ margin: "4px 0 8px" }}>今日获客报告</Title>
          {report && <Paragraph type="secondary">{report.report_date} · {PLATFORM_LABELS[report.platform] || report.platform}</Paragraph>}
        </div>
        <Space wrap>
          <Select value={platform} onChange={(v) => { setPlatform(v); setReport(null); }} options={PLATFORM_OPTIONS} style={{ width: 120 }} />
          <Button type="primary" onClick={handleGenerate} loading={generating}>生成今日报告</Button>
          <Button icon={<ReloadOutlined />} onClick={fetchTodayReport}>刷新</Button>
          {report && <Button icon={<CopyOutlined />} onClick={handleCopySummary}>{copyOk ? "已复制" : "复制摘要"}</Button>}
          {report && <Button icon={<CloudDownloadOutlined />} onClick={handleExport} loading={exporting}>导出</Button>}
        </Space>
      </div>

      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} closable onClose={() => setError(null)} />}

      {!loading && !report && !error && (
        <Card style={{ textAlign: "center", padding: 40 }}>
          <BarChartOutlined style={{ fontSize: 48, color: "#bfbfbf", marginBottom: 16 }} />
          <Title level={4}>今日尚未生成报告</Title>
          <Paragraph type="secondary">点击「生成今日报告」，系统将基于今日采集数据生成可交付的客户报告。</Paragraph>
          <Button type="primary" size="large" onClick={handleGenerate} loading={generating}>生成今日报告</Button>
        </Card>
      )}

      {report && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card title="📊 今日扫描概况" size="small">
            <Row gutter={[16, 16]}>
              <Col xs={8} sm={4}><Card><Statistic title="监控源" value={report.source_count} /></Card></Col>
              <Col xs={8} sm={4}><Card><Statistic title="帖子" value={report.post_count} /></Card></Col>
              <Col xs={8} sm={4}><Card><Statistic title="评论" value={report.comment_count} /></Card></Col>
              <Col xs={8} sm={4}><Card><Statistic title="线索" value={report.lead_count} /></Card></Col>
              <Col xs={8} sm={4}><Card style={{ background: "#fff7e6", borderColor: "#ffd591" }}><Statistic title="A级线索" value={report.a_lead_count} valueStyle={{ color: "#cf1322" }} /></Card></Col>
              <Col xs={8} sm={4}><Card><Statistic title="B级线索" value={report.b_lead_count} valueStyle={{ color: "#1677ff" }} /></Card></Col>
            </Row>
            {totalLeads > 0 && (
              <div style={{ marginTop: 16 }}>
                <Progress
                  percent={100}
                  success={{ percent: Math.round((report.a_lead_count / totalLeads) * 100), strokeColor: "#cf1322" }}
                  strokeColor="#1677ff"
                  trailColor="#d48806"
                  format={() => `A:${report.a_lead_count} B:${report.b_lead_count} C:${report.c_lead_count} D:${report.d_lead_count}`}
                />
              </div>
            )}
          </Card>

          <Card title="💼 CRM 跟进统计" size="small">
            {!report.crm_stats ? (
              <Empty description="暂无 CRM 数据" />
            ) : (
              <Row gutter={[16, 16]}>
                <Col xs={12} sm={6}>
                  <Card><Statistic title="今日新增客户" value={report.crm_stats.today_new_customers} valueStyle={{ color: "#1677ff" }} prefix={<TeamOutlined />} /></Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card><Statistic title="今日跟进次数" value={report.crm_stats.today_follow_count} valueStyle={{ color: "#722ed1" }} /></Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card><Statistic title="有意向客户" value={report.crm_stats.interested_count} valueStyle={{ color: "#fa8c16" }} /></Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card style={{ background: "#f6ffed", borderColor: "#b7eb8f" }}>
                    <Statistic title="已成交客户" value={report.crm_stats.converted_count} valueStyle={{ color: "#52c41a" }} prefix={<CheckCircleOutlined />} />
                  </Card>
                </Col>
                {report.crm_stats.overdue_follow_remind > 0 && (
                  <Col xs={24}>
                    <Alert
                      type="warning"
                      showIcon
                      icon={<WarningOutlined />}
                      message={`逾期未跟进提醒：当前有 ${report.crm_stats.overdue_follow_remind} 位客户超过下次跟进时间，请尽快处理。`}
                    />
                  </Col>
                )}
              </Row>
            )}
          </Card>

          <Card title="⭐ A级线索 Top 10" size="small">
            {!aLeadDetails || aLeadDetails.length === 0 ? (
              <Empty description="今日暂无A级线索" />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {aLeadDetails.map((lead, i) => (
                  <Card key={lead.id || i} size="small" style={{ background: "#fafafa" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Space size={8} style={{ marginBottom: 4 }}>
                          <Tag color="red">#{i + 1}</Tag>
                          <Tag>{PLATFORM_LABELS[lead.platform] || lead.platform}</Tag>
                          <Text type="secondary">评分 {lead.lead_score}</Text>
                          {lead.demand_type && <Tag color="purple">{lead.demand_type}</Tag>}
                        </Space>
                        <div><Text strong>{lead.user_name || "匿名用户"}</Text></div>
                        <Paragraph ellipsis={{ rows: 2 }} style={{ margin: "4px 0", color: "#4b5563" }}>{lead.content}</Paragraph>
                        {lead.reason && <Text type="secondary" style={{ fontSize: 12 }}>理由：{lead.reason}</Text>}
                        {lead.follow_up_script && (
                          <div style={{ marginTop: 4, background: "#e6f4ff", padding: "6px 10px", borderRadius: 6, border: "1px solid #91caff" }}>
                            <Text style={{ color: "#1677ff", fontSize: 12 }}>💬 {lead.follow_up_script}</Text>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </Card>

          <Card title="🔍 典型需求证据" size="small">
            {(!typicalEvidence || typicalEvidence.length === 0) ? (
              <Empty description="今日暂无需求证据" />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {typicalEvidence.map((ev, i) => (
                  <Card key={ev.lead_id || i} size="small" style={{ background: "#fafafa" }}>
                    <Space size={8} style={{ marginBottom: 4 }}>
                      <Tag color="red">#{i + 1}</Tag>
                      <Tag>{PLATFORM_LABELS[ev.platform] || ev.platform}</Tag>
                      <Tag color={ev.lead_level === "A" ? "red" : "orange"}>{ev.lead_level}级</Tag>
                    </Space>
                    <Paragraph ellipsis={{ rows: 2 }} style={{ margin: "4px 0" }}>{ev.content}</Paragraph>
                    <Space size={[6, 6]} wrap>
                      {ev.matched_words?.map((w, j) => <Tag key={j} color="gold">{w}</Tag>)}
                      {ev.amounts?.map((a, j) => <Tag key={j} color="blue">{a}</Tag>)}
                    </Space>
                  </Card>
                ))}
              </div>
            )}
          </Card>

          <Card title="👥 同行账号发现" size="small">
            {(!discoveredCompetitors || discoveredCompetitors.length === 0) ? (
              <Empty description="今日暂无同行账号发现" />
            ) : (
              <Table
                dataSource={discoveredCompetitors}
                columns={[
                  { title: "账号", dataIndex: "account_name", ellipsis: true },
                  { title: "平台", dataIndex: "platform", width: 90, render: (p: string) => <Tag>{PLATFORM_LABELS[p] || p}</Tag> },
                  { title: "评分", dataIndex: "competitor_score", width: 80, render: (v: number) => <Text strong>{v.toFixed(1)}</Text> },
                  { title: "建议监控", dataIndex: "suggest_monitor", width: 90, render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag> },
                  { title: "原因", dataIndex: "discover_reason", ellipsis: true, render: (v: string) => v || "-" },
                ]}
                rowKey="id"
                size="small"
                scroll={{ x: 600 }}
                pagination={false}
              />
            )}
          </Card>

          {tomorrowSuggestions && (
            <Card title="🚀 明日采集建议" size="small">
              <Row gutter={[16, 12]}>
                {tomorrowSuggestions.recommended_keywords.length > 0 && (
                  <Col xs={24} md={12}>
                    <Text strong>推荐关键词</Text>
                    <div style={{ marginTop: 8 }}><Space size={[6, 6]} wrap>{tomorrowSuggestions.recommended_keywords.map((k, i) => <Tag key={i} color="blue">{k}</Tag>)}</Space></div>
                  </Col>
                )}
                {tomorrowSuggestions.competitor_directions.length > 0 && (
                  <Col xs={24} md={12}>
                    <Text strong>同行方向</Text>
                    <div style={{ marginTop: 8 }}><Space size={[6, 6]} wrap>{tomorrowSuggestions.competitor_directions.map((d, i) => <Tag key={i} color="orange">{d}</Tag>)}</Space></div>
                  </Col>
                )}
                {tomorrowSuggestions.content_topics.length > 0 && (
                  <Col xs={24} md={12}>
                    <Text strong>内容选题</Text>
                    <div style={{ marginTop: 8 }}><Space size={[6, 6]} wrap>{tomorrowSuggestions.content_topics.map((t, i) => <Tag key={i}>{t}</Tag>)}</Space></div>
                  </Col>
                )}
                {tomorrowSuggestions.follow_up_hints.length > 0 && (
                  <Col xs={24} md={12}>
                    <Text strong>跟进提示</Text>
                    <div style={{ marginTop: 8 }}><Space size={[6, 6]} wrap>{tomorrowSuggestions.follow_up_hints.map((h, i) => <Tag key={i} color="green">{h}</Tag>)}</Space></div>
                  </Col>
                )}
              </Row>
            </Card>
          )}

          {riskWarnings && riskWarnings.length > 0 && (
            <Alert
              type="warning"
              message="合规提醒"
              description={
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {riskWarnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              }
              showIcon
              icon={<WarningOutlined />}
            />
          )}
        </div>
      )}
    </div>
  );
}
