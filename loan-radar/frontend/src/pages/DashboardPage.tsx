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
  A: { bg: "#FFF1F0", border: "#FFCCC7", color: "#CF1322" },
  B: { bg: "#E6F7FF", border: "#91D5FF", color: "#0958D9" },
  C: { bg: "#FFFBE6", border: "#FFE58F", color: "#D48806" },
  D: { bg: "#F5F5F5", border: "#D9D9D9", color: "#8C8C8C" },
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

function StatCard({ title, value, suffix, icon, accent, onClick }: {
  title: string; value: number | undefined; suffix?: string; icon?: React.ReactNode; accent?: string; onClick?: () => void;
}) {
  return (
    <Card
      hoverable={!!onClick}
      onClick={onClick}
      bodyStyle={{ padding: "16px 20px" }}
      style={{
        borderRadius: 8,
        border: accent ? `1px solid ${accent}33` : "1px solid #F0F0F0",
        background: accent ? `${accent}08` : "#fff",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 12, color: "#8C8C8C", marginBottom: 8 }}>{title}</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: accent || "#1F1F1F", lineHeight: 1.2 }}>
            {value ?? "-"}
            {suffix && <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 2 }}>{suffix}</span>}
          </div>
        </div>
        {icon && (
          <div style={{
            width: 40, height: 40, borderRadius: 8,
            background: accent ? `${accent}15` : "#F5F7FA",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: accent || "#8C8C8C", fontSize: 18,
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
    }}>
      {level}
    </span>
  );
}

function TaskStatusBadge({ status }: { status: string }) {
  const info = STATUS_MAP[status] || { label: status, color: "default" };
  return <Tag color={info.color} style={{ margin: 0, fontSize: 12 }}>{info.label}</Tag>;
}

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
    <div style={{ maxWidth: 1360, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: "#1F1F1F" }}>获客驾驶舱</div>
          <div style={{ fontSize: 13, color: "#8C8C8C", marginTop: 2 }}>实时掌握获客数据，快速驱动业务动作</div>
        </div>
        <Space size={8}>
          <Button.Group size="small">
            <Button type={dataMode === "today" ? "primary" : "default"} onClick={() => setDataMode("today")}>今日</Button>
            <Button type={dataMode === "total" ? "primary" : "default"} onClick={() => setDataMode("total")}>累计</Button>
          </Button.Group>
        </Space>
      </div>

      {mcIsDown && (
        <Card style={{ marginBottom: 16, borderRadius: 8, border: "1px solid #FFE58F" }} bodyStyle={{ padding: "12px 20px" }}>
          <Space>
            <WarningOutlined style={{ color: "#FAAD14", fontSize: 18 }} />
            <div>
              <Text strong style={{ fontSize: 13 }}>MediaCrawler 未连接</Text>
              <Text type="secondary" style={{ fontSize: 12, display: "block" }}>采集引擎不可用，实时采集功能受限</Text>
            </div>
            <Link to="/collection"><Button size="small">检查配置</Button></Link>
          </Space>
        </Card>
      )}

      {queueStatus && (
        <Card style={{ marginBottom: 16, borderRadius: 8 }} bodyStyle={{ padding: "10px 20px" }}>
          <Space size={12}>
            {queueStatus.active_task_id ? (
              <>
                <Tag color="processing" style={{ margin: 0 }}>运行中</Tag>
                <Text style={{ fontSize: 13 }}>正在执行任务 #{queueStatus.active_task_id}</Text>
                <SyncOutlined spin style={{ color: "#2F54EB", fontSize: 12 }} />
              </>
            ) : (
              <>
                <Tag style={{ margin: 0 }}>空闲</Tag>
                <Text type="secondary" style={{ fontSize: 13 }}>采集队列空闲</Text>
              </>
            )}
            {queueStatus.queue_size > 0 && <Text type="secondary" style={{ fontSize: 12 }}>· 排队 {queueStatus.queue_size} 个</Text>}
          </Space>
        </Card>
      )}

      {stats && (
        <>
          <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} md={4}>
              <StatCard title="监控源" value={stats.source_count} suffix="个" icon={<RadarChartOutlined />} onClick={() => navigate("/collection")} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <StatCard title="采集任务" value={displayTaskCount} suffix="个" icon={<PlayCircleOutlined />} onClick={() => navigate("/tasks")} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <StatCard title="帖子" value={displayPostCount} suffix="条" icon={<FileSearchOutlined />} onClick={() => navigate("/posts")} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <StatCard title="评论" value={displayCommentCount} suffix="条" onClick={() => navigate("/comments")} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <StatCard title="线索" value={displayLeadCount} suffix="条" icon={<StarOutlined />} accent="#2F54EB" onClick={() => navigate("/leads")} />
            </Col>
            <Col xs={12} sm={8} md={4}>
              <StatCard title="A级线索" value={displayALeadCount} suffix="条" icon={<ExclamationCircleOutlined />} accent="#CF1322" onClick={() => navigate("/leads?lead_level=A")} />
            </Col>
          </Row>

          <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}>
              <StatCard title="今日转入CRM" value={stats.crm_today_new} suffix="个" icon={<TeamOutlined />} accent="#2F54EB" onClick={() => navigate("/crm")} />
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
                accent={stats.crm_overdue_follow > 0 ? "#CF1322" : undefined}
                onClick={() => navigate("/crm?tab=follow-up&filter=overdue")}
              />
            </Col>
            <Col xs={12} sm={6}>
              <StatCard title="已成交客户" value={stats.crm_converted} suffix="个" icon={<CheckCircleOutlined />} accent="#52C41A" onClick={() => navigate("/crm?tab=customers&filter=converted")} />
            </Col>
          </Row>

          <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
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
                <StatCard title="XHS 高级采集" value={undefined} suffix="" icon={<PlayCircleOutlined />} />
              </Link>
            </Col>
          </Row>

          {isSystemEmpty && (
            <Card style={{ textAlign: "center", padding: 40, marginBottom: 16, borderRadius: 8 }}>
              <RadarChartOutlined style={{ fontSize: 48, color: "#BFBFBF", marginBottom: 16 }} />
              <Title level={4} style={{ color: "#595959" }}>尚未开始采集</Title>
              <Paragraph type="secondary">系统暂无数据。创建监控源并启动采集，系统将自动识别线索。</Paragraph>
              <Space>
                <Link to="/collection"><Button type="primary">新建监控源</Button></Link>
                <Link to="/collection"><Button>查看采集任务</Button></Link>
              </Space>
            </Card>
          )}

          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} lg={12}>
              <Card
                title={<span style={{ fontSize: 14, fontWeight: 600 }}>最近A级线索</span>}
                extra={<Link to="/leads?lead_level=A" style={{ fontSize: 12 }}>查看全部</Link>}
                style={{ borderRadius: 8 }}
                bodyStyle={{ padding: "12px 20px" }}
              >
                {stats.recent_a_leads.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "24px 0", color: "#BFBFBF", fontSize: 13 }}>
                    暂无A级线索，启动采集后高分线索将自动出现
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {stats.recent_a_leads.map((lead) => (
                      <Link key={lead.id} to="/leads" style={{ textDecoration: "none", color: "inherit" }}>
                        <div style={{
                          padding: "10px 12px", borderRadius: 6, background: "#FAFAFA",
                          border: "1px solid #F0F0F0", transition: "border-color 0.15s",
                        }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#2F54EB"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#F0F0F0"; }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Space size={6} style={{ marginBottom: 4 }}>
                                <RiskBadge level={lead.lead_level} />
                                <Tag style={{ margin: 0, fontSize: 11 }}>{PLATFORM_LABELS[lead.platform] || lead.platform}</Tag>
                                <Text type="secondary" style={{ fontSize: 12 }}>评分 {lead.lead_score}</Text>
                                {lead.demand_type && <Tag color="purple" style={{ margin: 0, fontSize: 11 }}>{lead.demand_type}</Tag>}
                              </Space>
                              <div><Text strong style={{ fontSize: 13 }}>{lead.user_name || "匿名用户"}</Text></div>
                              <Paragraph ellipsis={{ rows: 1 }} style={{ margin: "2px 0 0", color: "#595959", fontSize: 12 }}>
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
                title={<span style={{ fontSize: 14, fontWeight: 600 }}>采集任务状态</span>}
                extra={<Link to="/collection" style={{ fontSize: 12 }}>查看全部</Link>}
                style={{ borderRadius: 8 }}
                bodyStyle={{ padding: "12px 20px" }}
              >
                {stats.recent_tasks.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "24px 0", color: "#BFBFBF", fontSize: 13 }}>
                    暂无采集任务
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {stats.recent_tasks.map((task) => (
                      <Link key={task.id} to="/collection" style={{ textDecoration: "none", color: "inherit" }}>
                        <div style={{
                          padding: "10px 12px", borderRadius: 6, background: "#FAFAFA",
                          border: "1px solid #F0F0F0", transition: "border-color 0.15s",
                        }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#2F54EB"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#F0F0F0"; }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <Space size={6}>
                                <Text strong style={{ fontSize: 13 }}>#{task.id}</Text>
                                <Tag style={{ margin: 0, fontSize: 11 }}>{PLATFORM_LABELS[task.platform] || task.platform}</Tag>
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
                              {task.status === "success" && (
                                <Text type="secondary" style={{ fontSize: 11 }}>
                                  {task.post_count}帖 {task.comment_count}评 {task.lead_count}线索
                                </Text>
                              )}
                              <TaskStatusBadge status={task.status} />
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
            title={<span style={{ fontSize: 14, fontWeight: 600 }}>快捷操作</span>}
            style={{ borderRadius: 8 }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <Row gutter={[12, 12]}>
              {[
                { icon: <RadarChartOutlined />, title: "新建监控源", desc: "配置关键词或账号监控", action: () => navigate("/collection") },
                { icon: <PlayCircleOutlined />, title: "立即采集", desc: "启动采集任务获取数据", action: () => navigate("/collection") },
                { icon: <StarOutlined />, title: "查看线索池", desc: "浏览和管理所有线索", action: () => navigate("/leads") },
                { icon: <TeamOutlined />, title: "CRM 跟进", desc: "管理客户跟进状态", action: () => navigate("/crm") },
                { icon: <FileSearchOutlined />, title: generatingReport ? "生成中..." : "生成今日报告", desc: "一键生成获客日报", action: handleGenerateReport, loading: generatingReport },
                { icon: <CloudDownloadOutlined />, title: exportingCsv ? "导出中..." : "导出线索 CSV", desc: "下载线索数据表格", action: handleExportCsv, loading: exportingCsv },
              ].map((item, i) => (
                <Col xs={12} sm={8} md={4} key={i}>
                  <div
                    onClick={item.action}
                    style={{
                      padding: "14px 16px", borderRadius: 8, cursor: "pointer",
                      border: "1px solid #F0F0F0", background: "#fff",
                      transition: "all 0.15s", textAlign: "center",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "#2F54EB";
                      e.currentTarget.style.background = "#F5F7FA";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "#F0F0F0";
                      e.currentTarget.style.background = "#fff";
                    }}
                  >
                    <div style={{ fontSize: 22, color: "#2F54EB", marginBottom: 6 }}>{item.icon}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "#1F1F1F" }}>{item.title}</div>
                    <div style={{ fontSize: 11, color: "#8C8C8C", marginTop: 2 }}>{item.desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>

          {mcHealth && mcHealth.status === "healthy" && (
            <div style={{ marginTop: 16, textAlign: "center" }}>
              <Space size={6}>
                <CheckCircleOutlined style={{ color: "#52C41A", fontSize: 12 }} />
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
