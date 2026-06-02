import {
  CheckCircleOutlined,
  CloudDownloadOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  PlayCircleOutlined,
  RadarChartOutlined,
  RiseOutlined,
  StarOutlined,
  SyncOutlined,
  TeamOutlined,
  WarningOutlined,
  BookOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import { Button, Card, Col, Row, Space, Spin, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  exportLeadsCsv,
  generateDailyReport,
  getDashboardStats,
  getMediaCrawlerHealth,
  getQueueStatus,
  type DashboardStats,
  type MediaCrawlerHealth,
  type QueueStatus,
} from "../api";

const { Title, Text, Paragraph } = Typography;

const PLATFORM_LABELS: Record<string, string> = {
  xhs: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
  all: "全平台",
};

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: "排队中", color: "warning" },
  running: { label: "运行中", color: "processing" },
  success: { label: "成功", color: "success" },
  failed: { label: "失败", color: "error" },
  retrying: { label: "重试中", color: "warning" },
};

const RISK_CONFIG: Record<string, { bg: string; border: string; color: string }> = {
  A: { bg: "rgba(255,69,96,0.15)", border: "rgba(255,69,96,0.3)", color: "#ff4560" },
  B: { bg: "rgba(0,212,255,0.12)", border: "rgba(0,212,255,0.3)", color: "#00d4ff" },
  C: { bg: "rgba(255,176,32,0.12)", border: "rgba(255,176,32,0.3)", color: "#ffb020" },
  D: { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.45)" },
};

function formatTimeAgo(value: string | null | undefined) {
  if (!value) return "";
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  return `${Math.floor(hours / 24)}天前`;
}

type DataMode = "today" | "total";

const CYAN = "#00d4ff";
const GREEN = "#00e396";
const RED = "#ff4560";
const AMBER = "#ffb020";

function StatCard({ title, value, suffix, icon, accent, onClick }: {
  title: string; value: number | undefined; suffix?: string; icon?: React.ReactNode; accent?: string; onClick?: () => void;
}) {
  return (
    <Card
      hoverable={!!onClick}
      onClick={onClick}
      bodyStyle={{ padding: "14px 16px" }}
      style={{
        borderRadius: 8,
        border: accent ? `1px solid ${accent}33` : "1px solid rgba(0,212,255,0.1)",
        background: accent ? `${accent}0a` : "rgba(17,24,39,0.75)",
        backdropFilter: "blur(8px)",
        boxShadow: accent ? `0 0 12px ${accent}15` : "0 0 8px rgba(0,212,255,0.05)",
        transition: "all 0.2s",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 6, letterSpacing: "0.05em" }}>{title}</div>
          <div style={{ fontSize: 26, fontWeight: 700, color: accent || "#fff", lineHeight: 1.2, textShadow: accent ? `0 0 12px ${accent}40` : "0 0 12px rgba(0,212,255,0.15)" }}>
            {value ?? "-"}
            {suffix && <span style={{ fontSize: 12, fontWeight: 400, marginLeft: 2, color: "rgba(255,255,255,0.45)" }}>{suffix}</span>}
          </div>
        </div>
        {icon && (
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: accent ? `${accent}12` : "rgba(0,212,255,0.08)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: accent || CYAN, fontSize: 16,
            boxShadow: accent ? `0 0 8px ${accent}20` : "none",
          }}>
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

function RiskBadge({ level }: { level: string }) {
  const cfg = RISK_CONFIG[level] || RISK_CONFIG.D;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: 28, height: 20, borderRadius: 4,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      fontSize: 12, fontWeight: 700, color: cfg.color,
      boxShadow: `0 0 6px ${cfg.border}`,
    }}>
      {level}
    </span>
  );
}

function TaskStatusBadge({ status }: { status: string }) {
  const info = STATUS_MAP[status] || { label: status, color: "default" };
  return <Tag color={info.color} style={{ margin: 0, fontSize: 12 }}>{info.label}</Tag>;
}

const techPanelStyle: React.CSSProperties = {
  borderRadius: 8,
  border: "1px solid rgba(0,212,255,0.1)",
  background: "rgba(17,24,39,0.75)",
  backdropFilter: "blur(8px)",
  boxShadow: "0 0 12px rgba(0,212,255,0.05)",
};

const techPanelTitleStyle: React.CSSProperties = {
  fontSize: 13, fontWeight: 600, color: CYAN, letterSpacing: "0.03em",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [mcHealth, setMcHealth] = useState<MediaCrawlerHealth | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dataMode, setDataMode] = useState<DataMode>("today");
  const [generatingReport, setGeneratingReport] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);
  const navigate = useNavigate();
  const notifiedRef = useRef<Map<number, string>>(new Map());

  const loadAll = useCallback(async () => {
    try {
      const [dashboardData, healthData, queueData] = await Promise.all([
        getDashboardStats(),
        getMediaCrawlerHealth().catch(() => null),
        getQueueStatus().catch(() => null),
      ]);
      setStats(dashboardData);
      setMcHealth(healthData);
      setQueueStatus(queueData);
    } catch {
      message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    const interval = setInterval(() => {
      void (async () => {
        try {
          const data = await getDashboardStats();
          setStats(data);
          const notified = notifiedRef.current;
          for (const task of data.recent_tasks) {
            const prev = notified.get(task.id);
            if (prev && prev !== task.status) {
              if (task.status === "success") {
                const collected = task.collected_posts ?? task.post_count;
                const isAllDup = collected > 0 && task.post_count === 0;
                const msg = isAllDup
                  ? `任务 #${task.id} 采集完成：采集到 ${collected} 帖子（均为已存在数据）`
                  : `任务 #${task.id} 采集完成：新增 ${task.post_count} 帖子、${task.lead_count} 线索`;
                message.success(msg);
              } else if (task.status === "failed") {
                message.error(`任务 #${task.id} 采集失败`);
              }
            }
            notified.set(task.id, task.status);
          }
          const q = await getQueueStatus().catch(() => null);
          if (q) setQueueStatus(q);
        } catch {}
      })();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  async function handleGenerateReport() {
    setGeneratingReport(true);
    try {
      await generateDailyReport();
      message.success("今日获客报告已生成，可前往日报页面查看");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "生成失败");
    } finally {
      setGeneratingReport(false);
    }
  }

  async function handleExportCsv() {
    setExportingCsv(true);
    try {
      const blob = await exportLeadsCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `loan-radar-leads-${dayjs().format("YYYY-MM-DD")}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success("线索 CSV 已下载");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "导出失败");
    } finally {
      setExportingCsv(false);
    }
  }

  const mcIsDown = mcHealth && mcHealth.status !== "healthy";
  const isSystemEmpty = stats && stats.total_lead_count === 0 && stats.total_post_count === 0 && stats.total_comment_count === 0 && stats.total_task_count === 0;

  const displayTaskCount = dataMode === "today" ? stats?.today_task_count : stats?.total_task_count;
  const displayPostCount = dataMode === "today" ? stats?.today_post_count : stats?.total_post_count;
  const displayCommentCount = dataMode === "today" ? stats?.today_comment_count : stats?.total_comment_count;
  const displayLeadCount = dataMode === "today" ? stats?.today_lead_count : stats?.total_lead_count;
  const displayALeadCount = dataMode === "today" ? stats?.today_a_lead_count : stats?.total_a_lead_count;

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1440, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: "rgba(255,255,255,0.88)", textShadow: "0 0 16px rgba(0,212,255,0.2)" }}>
            <RadarChartOutlined style={{ marginRight: 8, color: CYAN, filter: "drop-shadow(0 0 4px rgba(0,212,255,0.5))" }} />
            获客驾驶舱
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", marginTop: 2, letterSpacing: "0.05em" }}>REAL-TIME LEAD INTELLIGENCE DASHBOARD</div>
        </div>
        <Space size={8}>
          <Space.Compact size="small">
            <Button type={dataMode === "today" ? "primary" : "default"} onClick={() => setDataMode("today")}>今日</Button>
            <Button type={dataMode === "total" ? "primary" : "default"} onClick={() => setDataMode("total")}>累计</Button>
          </Space.Compact>
        </Space>
      </div>

      {mcIsDown && (
        <Card style={{ marginBottom: 12, borderRadius: 8, border: "1px solid rgba(255,176,32,0.3)", background: "rgba(255,176,32,0.06)" }} bodyStyle={{ padding: "10px 16px" }}>
          <Space>
            <WarningOutlined style={{ color: AMBER, fontSize: 16 }} />
            <div>
              <Text strong style={{ fontSize: 13, color: AMBER }}>MediaCrawler 未连接</Text>
              <Text type="secondary" style={{ fontSize: 12, display: "block" }}>采集引擎不可用，实时采集功能受限</Text>
            </div>
            <Link to="/collection"><Button size="small">检查配置</Button></Link>
          </Space>
        </Card>
      )}

      {queueStatus && (
        <Card style={{ marginBottom: 12, ...techPanelStyle }} bodyStyle={{ padding: "8px 16px" }}>
          <Space size={12}>
            {queueStatus.active_task_id ? (
              <>
                <Tag color="processing" style={{ margin: 0 }}>运行中</Tag>
                <Text style={{ fontSize: 13, color: "rgba(255,255,255,0.75)" }}>正在执行任务 #{queueStatus.active_task_id}</Text>
                <SyncOutlined spin style={{ color: CYAN, fontSize: 12 }} />
              </>
            ) : (
              <>
                <Tag style={{ margin: 0, background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.15)", color: CYAN }}>空闲</Tag>
                <Text type="secondary" style={{ fontSize: 13 }}>采集队列空闲</Text>
              </>
            )}
            {queueStatus.queue_size > 0 && <Text type="secondary" style={{ fontSize: 12 }}>· 排队 {queueStatus.queue_size} 个</Text>}
          </Space>
        </Card>
      )}

      {stats && (
        <>
          <Card
            title={<span style={techPanelTitleStyle}>◈ 线索雷达</span>}
            style={{ marginBottom: 12, ...techPanelStyle }}
            bodyStyle={{ padding: "12px 16px" }}
          >
            <Row gutter={[10, 8]}>
              <Col xs={8} sm={4}>
                <StatCard title="监控源" value={stats.source_count} suffix="个" icon={<RadarChartOutlined />} onClick={() => navigate("/collection")} />
              </Col>
              <Col xs={8} sm={4}>
                <StatCard title="采集任务" value={displayTaskCount} suffix="个" icon={<PlayCircleOutlined />} onClick={() => navigate("/tasks")} />
              </Col>
              <Col xs={8} sm={4}>
                <StatCard title="帖子" value={displayPostCount} suffix="条" icon={<FileSearchOutlined />} onClick={() => navigate("/posts")} />
              </Col>
              <Col xs={8} sm={4}>
                <StatCard title="评论" value={displayCommentCount} suffix="条" onClick={() => navigate("/comments")} />
              </Col>
              <Col xs={8} sm={4}>
                <StatCard title="线索" value={displayLeadCount} suffix="条" icon={<StarOutlined />} accent={CYAN} onClick={() => navigate("/leads")} />
              </Col>
              <Col xs={8} sm={4}>
                <StatCard title="A级线索" value={displayALeadCount} suffix="条" icon={<ExclamationCircleOutlined />} accent={RED} onClick={() => navigate("/leads?lead_level=A")} />
              </Col>
            </Row>
          </Card>

          <Card
            title={<span style={techPanelTitleStyle}>◈ CRM 跟进台</span>}
            style={{ marginBottom: 12, ...techPanelStyle }}
            bodyStyle={{ padding: "12px 16px" }}
          >
            <Row gutter={[10, 8]}>
              <Col xs={12} sm={6}>
                <StatCard title="今日转入CRM" value={stats.crm_today_new} suffix="个" icon={<TeamOutlined />} accent={CYAN} onClick={() => navigate("/crm")} />
              </Col>
              <Col xs={12} sm={6}>
                <StatCard title="今日待跟进" value={stats.crm_pending_follow} suffix="个" icon={<ClockCircleOutlined />} onClick={() => navigate("/crm?tab=follow-up&filter=today")} />
              </Col>
              <Col xs={12} sm={6}>
                <StatCard
                  title="逾期未跟进"
                  value={stats.crm_overdue_follow}
                  suffix="个"
                  icon={<WarningOutlined />}
                  accent={stats.crm_overdue_follow > 0 ? RED : undefined}
                  onClick={() => navigate("/crm?tab=follow-up&filter=overdue")}
                />
              </Col>
              <Col xs={12} sm={6}>
                <StatCard title="已成交客户" value={stats.crm_converted} suffix="个" icon={<CheckCircleOutlined />} accent={GREEN} onClick={() => navigate("/crm?tab=customers&filter=converted")} />
              </Col>
            </Row>
          </Card>

          <Card
            title={<span style={techPanelTitleStyle}>◈ 小红书运营</span>}
            style={{ marginBottom: 12, ...techPanelStyle }}
            bodyStyle={{ padding: "12px 16px" }}
          >
            <Row gutter={[10, 8]}>
              <Col xs={12} sm={6}>
                <Link to="/xhs/library" style={{ textDecoration: "none" }}>
                  <StatCard title="XHS 内容库" value={stats.xhs_notes_count} suffix="篇" icon={<BookOutlined />} accent="#FF2442" />
                </Link>
              </Col>
              <Col xs={12} sm={6}>
                <Link to="/xhs/library" style={{ textDecoration: "none" }}>
                  <StatCard title="今日入库笔记" value={stats.xhs_notes_today} suffix="篇" icon={<RiseOutlined />} />
                </Link>
              </Col>
              <Col xs={12} sm={6}>
                <Link to="/xhs/dashboard" style={{ textDecoration: "none" }}>
                  <StatCard title="XHS 运营台" value={undefined} suffix="" icon={<RocketOutlined />} accent="#FF2442" />
                </Link>
              </Col>
              <Col xs={12} sm={6}>
                <Link to="/xhs/crawler" style={{ textDecoration: "none" }}>
                  <StatCard title="XHS 高级采集" value={undefined} suffix="" icon={<DatabaseOutlined />} />
                </Link>
              </Col>
            </Row>
          </Card>

          {isSystemEmpty && (
            <Card style={{ textAlign: "center", padding: 40, marginBottom: 12, borderRadius: 8, ...techPanelStyle }}>
              <RadarChartOutlined style={{ fontSize: 48, color: "rgba(0,212,255,0.3)", marginBottom: 16, filter: "drop-shadow(0 0 8px rgba(0,212,255,0.2))" }} />
              <Title level={4} style={{ color: "rgba(255,255,255,0.55)" }}>尚未开始采集</Title>
              <Paragraph type="secondary">系统暂无数据。创建监控源并启动采集，系统将自动识别线索。</Paragraph>
              <Space>
                <Link to="/collection"><Button type="primary">新建监控源</Button></Link>
                <Link to="/collection"><Button>查看采集任务</Button></Link>
              </Space>
            </Card>
          )}

          <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
            <Col xs={24} lg={12}>
              <Card
                title={<span style={techPanelTitleStyle}>◈ 最近A级线索</span>}
                extra={<Link to="/leads?lead_level=A" style={{ fontSize: 12, color: CYAN }}>查看全部 →</Link>}
                style={techPanelStyle}
                bodyStyle={{ padding: "10px 16px" }}
              >
                {stats.recent_a_leads.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "24px 0", color: "rgba(255,255,255,0.25)", fontSize: 13 }}>
                    暂无A级线索，启动采集后高分线索将自动出现
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {stats.recent_a_leads.map((lead) => (
                      <Link key={lead.id} to="/leads" style={{ textDecoration: "none", color: "inherit" }}>
                        <div style={{
                          padding: "8px 10px", borderRadius: 6, background: "rgba(0,212,255,0.03)",
                          border: "1px solid rgba(0,212,255,0.06)", transition: "all 0.15s",
                        }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = `${CYAN}40`; e.currentTarget.style.boxShadow = `0 0 8px ${CYAN}15`; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.06)"; e.currentTarget.style.boxShadow = "none"; }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Space size={6} style={{ marginBottom: 2 }}>
                                <RiskBadge level={lead.lead_level} />
                                <Tag style={{ margin: 0, fontSize: 11, background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.15)", color: CYAN }}>{PLATFORM_LABELS[lead.platform] || lead.platform}</Tag>
                                <Text type="secondary" style={{ fontSize: 11 }}>评分 {lead.lead_score}</Text>
                                {lead.demand_type && <Tag color="purple" style={{ margin: 0, fontSize: 11 }}>{lead.demand_type}</Tag>}
                              </Space>
                              <div><Text strong style={{ fontSize: 13, color: "rgba(255,255,255,0.85)" }}>{lead.user_name || "匿名用户"}</Text></div>
                              <Paragraph ellipsis={{ rows: 1 }} style={{ margin: "2px 0 0", color: "rgba(255,255,255,0.45)", fontSize: 12 }}>
                                {lead.content}
                              </Paragraph>
                            </div>
                            <Text type="secondary" style={{ fontSize: 11, flexShrink: 0, marginLeft: 8 }}>
                              {formatTimeAgo(lead.created_at)}
                            </Text>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card
                title={<span style={techPanelTitleStyle}>◈ 采集任务状态</span>}
                extra={<Link to="/collection" style={{ fontSize: 12, color: CYAN }}>查看全部 →</Link>}
                style={techPanelStyle}
                bodyStyle={{ padding: "10px 16px" }}
              >
                {stats.recent_tasks.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "24px 0", color: "rgba(255,255,255,0.25)", fontSize: 13 }}>
                    暂无采集任务
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {stats.recent_tasks.map((task) => (
                      <Link key={task.id} to="/collection" style={{ textDecoration: "none", color: "inherit" }}>
                        <div style={{
                          padding: "8px 10px", borderRadius: 6, background: "rgba(0,212,255,0.03)",
                          border: "1px solid rgba(0,212,255,0.06)", transition: "all 0.15s",
                        }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = `${CYAN}40`; e.currentTarget.style.boxShadow = `0 0 8px ${CYAN}15`; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(0,212,255,0.06)"; e.currentTarget.style.boxShadow = "none"; }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Space size={6}>
                                <Text strong style={{ fontSize: 13, color: "rgba(255,255,255,0.85)" }}>#{task.id}</Text>
                                <Tag style={{ margin: 0, fontSize: 11, background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.15)", color: CYAN }}>{PLATFORM_LABELS[task.platform] || task.platform}</Tag>
                                <Text type="secondary" style={{ fontSize: 12 }}>{task.source_type}</Text>
                              </Space>
                              <div style={{ marginTop: 2 }}>
                                <Text type="secondary" style={{ fontSize: 11 }}>
                                  {task.source_value?.slice(0, 30) || "-"}
                                  {task.started_at ? ` · ${formatTimeAgo(task.started_at)}` : ""}
                                </Text>
                              </div>
                            </div>
                            <Space size={8}>
                              <TaskStatusBadge status={task.status} />
                              {task.status === "success" && (
                                <Text style={{ fontSize: 12, color: GREEN }}>
                                  +{task.post_count}帖 / +{task.lead_count}线索
                                </Text>
                              )}
                            </Space>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </Card>
            </Col>
          </Row>

          <Card
            title={<span style={techPanelTitleStyle}>◈ 快捷操作</span>}
            style={techPanelStyle}
            bodyStyle={{ padding: "12px 16px" }}
          >
            <Row gutter={[10, 10]}>
              {[
                { icon: <RadarChartOutlined />, title: "新建监控源", desc: "配置关键词或账号监控", action: () => navigate("/collection"), accent: CYAN },
                { icon: <PlayCircleOutlined />, title: "立即采集", desc: "启动采集任务获取数据", action: () => navigate("/collection"), accent: GREEN },
                { icon: <StarOutlined />, title: "查看线索池", desc: "浏览和管理所有线索", action: () => navigate("/leads"), accent: AMBER },
                { icon: <TeamOutlined />, title: "CRM 跟进", desc: "管理客户跟进状态", action: () => navigate("/crm"), accent: CYAN },
                { icon: <ThunderboltOutlined />, title: generatingReport ? "生成中..." : "生成今日报告", desc: "一键生成获客日报", action: handleGenerateReport, loading: generatingReport, accent: AMBER },
                { icon: <CloudDownloadOutlined />, title: exportingCsv ? "导出中..." : "导出线索 CSV", desc: "下载线索数据表格", action: handleExportCsv, loading: exportingCsv, accent: GREEN },
              ].map((item, i) => (
                <Col xs={8} sm={8} md={4} key={i}>
                  <div
                    onClick={item.action}
                    style={{
                      padding: "12px 14px", borderRadius: 8, cursor: "pointer",
                      border: "1px solid rgba(0,212,255,0.08)", background: "rgba(0,212,255,0.03)",
                      transition: "all 0.2s", textAlign: "center",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = `${item.accent}40`;
                      e.currentTarget.style.background = `${item.accent}08`;
                      e.currentTarget.style.boxShadow = `0 0 12px ${item.accent}15`;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "rgba(0,212,255,0.08)";
                      e.currentTarget.style.background = "rgba(0,212,255,0.03)";
                      e.currentTarget.style.boxShadow = "none";
                    }}
                  >
                    <div style={{ fontSize: 20, color: item.accent, marginBottom: 4, filter: `drop-shadow(0 0 4px ${item.accent}40)` }}>{item.icon}</div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "rgba(255,255,255,0.85)" }}>{item.title}</div>
                    <div style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", marginTop: 2 }}>{item.desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>

          {mcHealth && mcHealth.status === "healthy" && (
            <div style={{ marginTop: 12, textAlign: "center" }}>
              <Space size={6}>
                <CheckCircleOutlined style={{ color: GREEN, fontSize: 12 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  MediaCrawler 正常运行 · {mcHealth.mode === "embedded" ? "内嵌模式" : "HTTP 桥接模式"}
                  {mcHealth.supported_platforms.length > 0 && (
                    <> · 支持 {mcHealth.supported_platforms.map((p) => p.label).join("、")}</>
                  )}
                </Text>
              </Space>
            </div>
          )}
        </>
      )}
    </div>
  );
}
