import { ReloadOutlined, RestOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Input, Row, Select, Space, Table, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getComments, type Comment } from "../api";

const { Title, Text, Paragraph } = Typography;

const PLATFORM_OPTIONS = [
  { value: "", label: "全部" },
  { value: "xhs", label: "小红书" },
  { value: "douyin", label: "抖音" },
  { value: "zhihu", label: "知乎" },
];
const PLATFORM_LABELS: Record<string, string> = { xhs: "小红书", douyin: "抖音", zhihu: "知乎" };
const DEMAND_OPTIONS = [
  { value: "", label: "全部" },
  { value: "借款需求", label: "借款需求" },
  { value: "资质焦虑", label: "资质焦虑" },
  { value: "产品咨询", label: "产品咨询" },
  { value: "弱意向", label: "弱意向" },
];
const RISK_OPTIONS = [
  { value: "", label: "全部" },
  { value: "low", label: "低" },
  { value: "mid", label: "中" },
  { value: "high", label: "高" },
];
const RISK_COLORS: Record<string, string> = { low: "green", mid: "warning", high: "red" };
const SUSPECTED_OPTIONS = [
  { value: "", label: "全部" },
  { value: "true", label: "是" },
  { value: "false", label: "否" },
];

export default function CommentsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Comment[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);

  const [platform, setPlatform] = useState("");
  const [demandType, setDemandType] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [suspected, setSuspected] = useState("");
  const [postId, setPostId] = useState("");
  const [keyword, setKeyword] = useState("");

  async function loadData(nextPage = page, nextPageSize = pageSize) {
    setLoading(true);
    try {
      const result = await getComments({
        platform: platform || undefined,
        demand_type: demandType || undefined,
        risk_level: riskLevel || undefined,
        post_id: postId || undefined,
        keyword: keyword || undefined,
        is_suspected_demand: suspected === "" ? undefined : suspected === "true",
        page: nextPage,
        page_size: nextPageSize,
      });
      setItems(result.items);
      setTotal(result.total);
      setPage(result.page);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载评论失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData(1);
  }, []);

  async function handleSearch() {
    setPage(1);
    await loadData(1);
  }

  async function handleReset() {
    setPlatform("");
    setDemandType("");
    setRiskLevel("");
    setSuspected("");
    setPostId("");
    setKeyword("");
    setPage(1);
    try {
      setLoading(true);
      const result = await getComments({ page: 1, page_size: pageSize });
      setItems(result.items);
      setTotal(result.total);
      setPage(result.page);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: "平台", dataIndex: "platform", width: 80,
      render: (p: string) => <Tag>{PLATFORM_LABELS[p] || p}</Tag>,
    },
    { title: "用户", dataIndex: "user_name", width: 100, render: (v: string) => v || "-" },
    { title: "帖子ID", dataIndex: "post_id", width: 100, ellipsis: true },
    { title: "内容", dataIndex: "content", ellipsis: true, width: 240 },
    {
      title: "需求类型", dataIndex: "demand_type", width: 100,
      render: (v: string) => v ? <Tag color="purple">{v}</Tag> : "-",
    },
    {
      title: "风险", dataIndex: "risk_level", width: 70,
      render: (v: string) => v ? <Tag color={RISK_COLORS[v] || "default"}>{v}</Tag> : "-",
    },
    {
      title: "疑似需求", dataIndex: "is_suspected_demand", width: 80,
      render: (v: boolean) => v ? <Tag color="orange">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: "线索", dataIndex: "has_lead", width: 70,
      render: (v: boolean, record: Comment) =>
        v ? (
          <Button type="link" size="small" onClick={() => navigate(`/leads?source_comment_id=${record.id}`)}>查看</Button>
        ) : "-",
    },
    { title: "点赞", dataIndex: "like_count", width: 60 },
    {
      title: "发布时间", dataIndex: "publish_time", width: 130,
      render: (v: string) => v ? dayjs(v).format("MM-DD HH:mm") : "-",
    },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 20px 48px" }}>
      <div style={{ marginBottom: 20 }}>
        <Text type="secondary" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}>评论池</Text>
        <Title level={2} style={{ margin: "4px 0 8px" }}>评论池</Title>
        <Paragraph type="secondary">查看评论池并按平台、需求类型、风险等级、疑似需求筛选。</Paragraph>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={12} sm={8} md={4}>
            <Select value={platform} onChange={setPlatform} options={PLATFORM_OPTIONS} style={{ width: "100%" }} placeholder="平台" />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select value={demandType} onChange={setDemandType} options={DEMAND_OPTIONS} style={{ width: "100%" }} placeholder="需求类型" />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select value={riskLevel} onChange={setRiskLevel} options={RISK_OPTIONS} style={{ width: "100%" }} placeholder="风险等级" />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select value={suspected} onChange={setSuspected} options={SUSPECTED_OPTIONS} style={{ width: "100%" }} placeholder="疑似需求" />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Input value={postId} onChange={(e) => setPostId(e.target.value)} placeholder="帖子 ID" allowClear />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="关键词" allowClear onPressEnter={handleSearch} />
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch} loading={loading}>查询</Button>
              <Button icon={<RestOutlined />} onClick={handleReset}>重置</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card
        title={`评论列表（共 ${total} 条）`}
        size="small"
        extra={<Button icon={<ReloadOutlined />} onClick={() => void loadData()}>刷新</Button>}
      >
        <Table
          dataSource={items}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 1100 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
              void loadData(p, ps);
            },
          }}
        />
      </Card>
    </div>
  );
}
