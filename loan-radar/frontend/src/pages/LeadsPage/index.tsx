import { CloudDownloadOutlined, TeamOutlined } from "@ant-design/icons";
import { Button, Card, Row, Col, Space, Table, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { convertLeadToCrm, exportLeadsCsv, getLeads, type Lead, type LeadQueryParams } from "../../api";
import LeadDetailDrawer from "./LeadDetailDrawer";
import LeadFilters, { type FilterValues } from "./LeadFilters";

const { Text } = Typography;

const PLATFORM_LABELS: Record<string, string> = { xhs: "小红书", douyin: "抖音", zhihu: "知乎" };
const STATUS_LABELS: Record<string, string> = { new: "新线索", contacted: "已跟进", interested: "有意向", invalid: "无效", converted: "已转化" };
const STATUS_COLORS: Record<string, string> = { new: "blue", contacted: "orange", interested: "green", invalid: "default", converted: "cyan" };

const RISK_CONFIG: Record<string, { bg: string; border: string; color: string }> = {
  A: { bg: "#FFF1F0", border: "#FFCCC7", color: "#CF1322" },
  B: { bg: "#E6F7FF", border: "#91D5FF", color: "#0958D9" },
  C: { bg: "#FFFBE6", border: "#FFE58F", color: "#D48806" },
  D: { bg: "#F5F5F5", border: "#D9D9D9", color: "#8C8C8C" },
};

function RiskBadge({ level }: { level: string }) {
  const cfg = RISK_CONFIG[level] || RISK_CONFIG.D;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      minWidth: 28, height: 22, borderRadius: 4, padding: "0 6px",
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      fontSize: 12, fontWeight: 700, color: cfg.color,
    }}>
      {level}
    </span>
  );
}

function ScoreCell({ score }: { score: number }) {
  const color = score >= 70 ? "#CF1322" : score >= 40 ? "#D48806" : "#595959";
  return (
    <span style={{ fontWeight: 600, color, fontSize: 13 }}>
      {score}
    </span>
  );
}

export default function LeadsPage() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [detailLead, setDetailLead] = useState<Lead | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [statTotals, setStatTotals] = useState<Record<string, number>>({ all: 0, A: 0, B: 0, C: 0, D: 0 });
  const [filters, setFilters] = useState<FilterValues>(() => ({
    lead_level: searchParams.get("lead_level") || "",
    demand_type: searchParams.get("demand_type") || "",
    platform: searchParams.get("platform") || "",
    status: searchParams.get("status") || "",
    source_type: searchParams.get("source_type") || "",
    keyword: searchParams.get("keyword") || "",
    source_post_id: searchParams.get("source_post_id") ? Number(searchParams.get("source_post_id")) : undefined,
    source_comment_id: searchParams.get("source_comment_id") ? Number(searchParams.get("source_comment_id")) : undefined,
    is_duplicate: searchParams.get("is_duplicate") || "",
    created_after: undefined,
    publish_time_days: "",
  }));

  const buildApiParams = useCallback((nextFilters: FilterValues, nextPage = page, nextPageSize = pageSize): LeadQueryParams => {
    let createdAfter = nextFilters.created_after;
    if (nextFilters.publish_time_days) {
      const days = Number(nextFilters.publish_time_days);
      if (days > 0) {
        const date = new Date();
        date.setDate(date.getDate() - days);
        createdAfter = date.toISOString();
      }
    }
    return {
      demand_type: nextFilters.demand_type || undefined,
      platform: nextFilters.platform || undefined,
      status: nextFilters.status || undefined,
      source_type: nextFilters.source_type || undefined,
      keyword: nextFilters.keyword || undefined,
      source_post_id: nextFilters.source_post_id || undefined,
      source_comment_id: nextFilters.source_comment_id || undefined,
      is_duplicate: nextFilters.is_duplicate === "true" ? true : nextFilters.is_duplicate === "false" ? false : undefined,
      created_after: createdAfter,
      lead_level: nextFilters.lead_level || undefined,
      page: nextPage,
      page_size: nextPageSize,
    };
  }, [page, pageSize]);

  async function loadData(nextPage = page, nextPageSize = pageSize, nextFilters = filters) {
    setLoading(true);
    try {
      const apiParams = buildApiParams(nextFilters, nextPage, nextPageSize);
      const commonBase = { ...apiParams, page: undefined, page_size: undefined, lead_level: undefined };

      const [listResult, allResult, aResult, bResult, cResult, dResult] = await Promise.all([
        getLeads(apiParams),
        getLeads({ ...commonBase, page: 1, page_size: 1 }),
        getLeads({ ...commonBase, lead_level: "A", page: 1, page_size: 1 }),
        getLeads({ ...commonBase, lead_level: "B", page: 1, page_size: 1 }),
        getLeads({ ...commonBase, lead_level: "C", page: 1, page_size: 1 }),
        getLeads({ ...commonBase, lead_level: "D", page: 1, page_size: 1 }),
      ]);

      setItems(listResult.items);
      setTotal(listResult.total);
      setPage(listResult.page);
      setStatTotals({ all: allResult.total, A: aResult.total, B: bResult.total, C: cResult.total, D: dResult.total });
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载线索失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(1, pageSize, filters);
  }, []);

  async function handleSearch() {
    setPage(1);
    await loadData(1, pageSize, filters);
  }

  async function handleReset() {
    const resetFilters: FilterValues = {
      lead_level: "", demand_type: "", platform: "", status: "", source_type: "",
      keyword: "", source_post_id: undefined, source_comment_id: undefined,
      is_duplicate: "", created_after: undefined, publish_time_days: "",
    };
    setFilters(resetFilters);
    setPage(1);
    await loadData(1, pageSize, resetFilters);
  }

  async function handleExportCsv() {
    setExporting(true);
    try {
      const apiParams = buildApiParams(filters);
      const blob = await exportLeadsCsv(apiParams);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `leads-${dayjs().format("YYYY-MM-DD")}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success("CSV 已下载");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "导出失败");
    } finally {
      setExporting(false);
    }
  }

  function handleViewDetail(lead: Lead) {
    setDetailLead(lead);
    setDetailOpen(true);
  }

  async function handleConvertToCrm(lead: Lead) {
    try {
      await convertLeadToCrm(lead.id);
      message.success("已转入 CRM");
      void loadData(page, pageSize, filters);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "转入 CRM 失败");
    }
  }

  const columns = [
    {
      title: "等级",
      dataIndex: "lead_level",
      width: 64,
      render: (level: string) => <RiskBadge level={level} />,
    },
    {
      title: "平台",
      dataIndex: "platform",
      width: 80,
      render: (p: string) => <Tag style={{ margin: 0, fontSize: 12 }}>{PLATFORM_LABELS[p] || p}</Tag>,
    },
    {
      title: "用户",
      dataIndex: "user_name",
      width: 110,
      render: (name: string) => <Text style={{ fontSize: 13 }}>{name || "匿名"}</Text>,
    },
    {
      title: "内容",
      dataIndex: "content",
      ellipsis: true,
      render: (content: string) => (
        <Text ellipsis style={{ maxWidth: 320, fontSize: 13, color: "#595959" }}>{content || "-"}</Text>
      ),
    },
    {
      title: "需求类型",
      dataIndex: "demand_type",
      width: 100,
      render: (dt: string) => dt ? <Tag color="purple" style={{ margin: 0, fontSize: 11 }}>{dt}</Tag> : <Text type="secondary" style={{ fontSize: 12 }}>-</Text>,
    },
    {
      title: "评分",
      dataIndex: "lead_score",
      width: 72,
      sorter: (a: Lead, b: Lead) => a.lead_score - b.lead_score,
      render: (score: number) => <ScoreCell score={score} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (status: string) => <Tag color={STATUS_COLORS[status] || "default"} style={{ margin: 0, fontSize: 12 }}>{STATUS_LABELS[status] || status}</Tag>,
    },
    {
      title: "重复",
      dataIndex: "is_duplicate",
      width: 64,
      render: (dup: boolean) => dup ? <Tag color="warning" style={{ margin: 0, fontSize: 11 }}>重复</Tag> : null,
    },
    {
      title: "评论时间",
      dataIndex: "comment_publish_time",
      width: 120,
      sorter: (a: Lead, b: Lead) => {
        const ta = a.comment_publish_time || a.created_at;
        const tb = b.comment_publish_time || b.created_at;
        return new Date(ta).getTime() - new Date(tb).getTime();
      },
      render: (_: unknown, record: Lead) => {
        const v = record.comment_publish_time || record.created_at;
        return <Text type="secondary" style={{ fontSize: 12 }}>{dayjs(v).format("MM-DD HH:mm")}</Text>;
      },
    },
    {
      title: "操作",
      width: 140,
      render: (_: unknown, record: Lead) => (
        <Space size={4}>
          <Button type="link" size="small" style={{ padding: 0, fontSize: 12 }} onClick={() => handleViewDetail(record)}>详情</Button>
          {record.crm_customer_id ? (
            <Text type="secondary" style={{ fontSize: 11 }}>已转CRM</Text>
          ) : (
            <Button type="link" size="small" icon={<TeamOutlined />} style={{ padding: 0, fontSize: 12 }} onClick={() => handleConvertToCrm(record)}>转CRM</Button>
          )}
        </Space>
      ),
    },
  ];

  const statCards = [
    { label: "全部线索", value: statTotals.all, color: undefined },
    { label: "A级", value: statTotals.A, color: "#CF1322" },
    { label: "B级", value: statTotals.B, color: "#0958D9" },
    { label: "C级", value: statTotals.C, color: "#D48806" },
    { label: "D级", value: statTotals.D, color: "#8C8C8C" },
  ];

  return (
    <div style={{ maxWidth: 1440, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: "#1F1F1F" }}>线索池</div>
          <div style={{ fontSize: 13, color: "#8C8C8C", marginTop: 2 }}>查看 A/B/C/D 级线索，核对证据链，修改状态并导出</div>
        </div>
        <Button icon={<CloudDownloadOutlined />} onClick={handleExportCsv} loading={exporting} size="small">导出 CSV</Button>
      </div>

      <Row gutter={[12, 8]} style={{ marginBottom: 16 }}>
        {statCards.map((s) => (
          <Col xs={8} sm={4} key={s.label}>
            <Card
              bodyStyle={{ padding: "12px 16px" }}
              style={{
                borderRadius: 8,
                border: s.color ? `1px solid ${s.color}33` : "1px solid #F0F0F0",
                background: s.color ? `${s.color}06` : "#fff",
              }}
            >
              <div style={{ fontSize: 12, color: "#8C8C8C", marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color || "#1F1F1F", lineHeight: 1.2 }}>{s.value}</div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card style={{ marginBottom: 12, borderRadius: 8 }} bodyStyle={{ padding: "12px 16px" }}>
        <LeadFilters
          filters={filters}
          onChange={setFilters}
          onSearch={handleSearch}
          onReset={handleReset}
          loading={loading}
        />
      </Card>

      <Card style={{ borderRadius: 8 }} bodyStyle={{ padding: 0 }}>
        <Table
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ x: 1100 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => <Text type="secondary" style={{ fontSize: 12 }}>共 {t} 条</Text>,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
              void loadData(p, ps, filters);
            },
          }}
          onRow={(record) => ({
            onClick: () => handleViewDetail(record),
            style: { cursor: "pointer" },
          })}
        />
      </Card>

      <LeadDetailDrawer
        open={detailOpen}
        lead={detailLead}
        onClose={() => { setDetailOpen(false); setDetailLead(null); }}
        onUpdated={() => void loadData(page, pageSize, filters)}
      />
    </div>
  );
}
