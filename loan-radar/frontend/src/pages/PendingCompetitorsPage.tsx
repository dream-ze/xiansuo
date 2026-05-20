import { CheckOutlined, CloseOutlined, ReloadOutlined, RestOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Input, Row, Select, Space, Table, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";

import {
  approvePendingCompetitor,
  getPendingCompetitors,
  ignorePendingCompetitor,
  type PendingCompetitor,
} from "../api";

const { Title, Text, Paragraph } = Typography;

const PLATFORM_OPTIONS = [
  { value: "", label: "全部" },
  { value: "xhs", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
  { value: "other", label: "其他" },
];
const PLATFORM_LABELS: Record<string, string> = { xhs: "小红书", douyin: "抖音", zhihu: "知乎" };
const STATUS_OPTIONS = [
  { value: "", label: "全部" },
  { value: "pending", label: "待审核" },
  { value: "approved", label: "已通过" },
  { value: "ignored", label: "已忽略" },
];
const STATUS_COLORS: Record<string, string> = { pending: "warning", approved: "success", ignored: "default" };
const STATUS_LABELS: Record<string, string> = { pending: "待审核", approved: "已通过", ignored: "已忽略" };

export default function PendingCompetitorsPage() {
  const [items, setItems] = useState<PendingCompetitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("pending");
  const [minScore, setMinScore] = useState("");

  async function loadData() {
    setLoading(true);
    try {
      const result = await getPendingCompetitors({
        platform: platform || undefined,
        status: status || undefined,
        min_score: minScore === "" ? undefined : Number(minScore),
      });
      setItems(result);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载同行发现池失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleApprove(item: PendingCompetitor) {
    setBusyId(item.id);
    try {
      const result = await approvePendingCompetitor(item.id);
      message.success(`已通过：${result.pending_competitor.account_name}，新增监控源 ${result.monitor_source.name}`);
      await loadData();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "审核通过失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handleIgnore(item: PendingCompetitor) {
    setBusyId(item.id);
    try {
      await ignorePendingCompetitor(item.id);
      message.success(`已忽略：${item.account_name}`);
      await loadData();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "忽略失败");
    } finally {
      setBusyId(null);
    }
  }

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: "平台", dataIndex: "platform", width: 90,
      render: (p: string) => <Tag>{PLATFORM_LABELS[p] || p}</Tag>,
    },
    { title: "账号名", dataIndex: "account_name", ellipsis: true, width: 160 },
    { title: "来源关键词", dataIndex: "source_keyword", width: 120, render: (v: string) => v || "-" },
    {
      title: "综合分", dataIndex: "competitor_score", width: 90,
      render: (v: number) => <Text strong>{v.toFixed(1)}</Text>,
    },
    {
      title: "状态", dataIndex: "status", width: 90,
      render: (s: string) => <Tag color={STATUS_COLORS[s] || "default"}>{STATUS_LABELS[s] || s}</Tag>,
    },
    { title: "发现原因", dataIndex: "discover_reason", ellipsis: true, render: (v: string) => v || "-" },
    {
      title: "发现时间", dataIndex: "created_at", width: 130,
      render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
    },
    {
      title: "操作", width: 140,
      render: (_: unknown, record: PendingCompetitor) => {
        const canReview = record.status === "pending";
        return (
          <Space size={4}>
            <Button
              size="small"
              type="primary"
              icon={<CheckOutlined />}
              onClick={() => handleApprove(record)}
              disabled={!canReview || busyId === record.id}
              loading={busyId === record.id}
            >
              通过
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseOutlined />}
              onClick={() => handleIgnore(record)}
              disabled={!canReview || busyId === record.id}
            >
              忽略
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 20px 48px" }}>
      <div style={{ marginBottom: 20 }}>
        <Text type="secondary" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}>同行发现</Text>
        <Title level={2} style={{ margin: "4px 0 8px" }}>同行账号发现池</Title>
        <Paragraph type="secondary">查看待审核同行账号，审核通过后自动加入监控源。</Paragraph>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={8} sm={6} md={4}>
            <Select value={platform} onChange={setPlatform} options={PLATFORM_OPTIONS} style={{ width: "100%" }} placeholder="平台" />
          </Col>
          <Col xs={8} sm={6} md={4}>
            <Select value={status} onChange={setStatus} options={STATUS_OPTIONS} style={{ width: "100%" }} placeholder="状态" />
          </Col>
          <Col xs={8} sm={6} md={4}>
            <Input
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              placeholder="最低评分"
              allowClear
            />
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={loadData} loading={loading}>查询</Button>
              <Button icon={<RestOutlined />} onClick={() => { setPlatform(""); setStatus("pending"); setMinScore(""); }}>重置</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card
        title={`同行账号列表（${items.length} 条）`}
        size="small"
        extra={<Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>}
      >
        <Table
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 1000 }}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
        />
      </Card>
    </div>
  );
}
