import {
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  TeamOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  message,
  Modal,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useCallback, useEffect, useState } from "react";

import {
  createCrmCustomer,
  createCrmFollowRecord,
  getCrmCustomers,
  getCrmDashboard,
  getCrmFollowRecords,
  updateCrmCustomer,
  type CrmCustomer,
  type CrmCustomerManualCreate,
  type CrmFollowRecord,
} from "../api";

const { Title, Text, Paragraph } = Typography;

const CRM_STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: "待跟进", color: "default" },
  contacted: { label: "已联系", color: "processing" },
  interested: { label: "有意向", color: "warning" },
  wechat_added: { label: "已加微信", color: "cyan" },
  applied: { label: "已申请", color: "blue" },
  converted: { label: "已成交", color: "success" },
  invalid: { label: "无效", color: "default" },
};

const FOLLOW_TYPE_MAP: Record<string, string> = {
  phone: "电话",
  wechat: "微信",
  message: "短信",
  visit: "拜访",
  other: "其他",
  manual: "手动",
};

const SOURCE_TYPE_MAP: Record<string, string> = {
  lead_conversion: "AI线索转入",
  manual: "手动录入",
  import: "批量导入",
};

const SOURCE_CHANNEL_OPTIONS = [
  { value: "小红书", label: "小红书" },
  { value: "抖音", label: "抖音" },
  { value: "知乎", label: "知乎" },
  { value: "微信", label: "微信" },
  { value: "电话", label: "电话" },
  { value: "朋友介绍", label: "朋友介绍" },
  { value: "线下", label: "线下" },
  { value: "员工自拓", label: "员工自拓" },
  { value: "其他", label: "其他" },
];

const LEVEL_COLORS: Record<string, string> = {
  A: "red",
  B: "orange",
  C: "blue",
  D: "default",
};

const REMINDER_FILTER_OPTIONS = [
  { value: "overdue", label: "逾期未跟进" },
  { value: "today", label: "今日待跟进" },
  { value: "tomorrow", label: "明日待跟进" },
  { value: "this_week", label: "本周待跟进" },
  { value: "none", label: "暂无跟进时间" },
];

function getReminderTag(customer: CrmCustomer) {
  if (customer.status === "converted" || customer.status === "invalid") {
    return null;
  }
  if (!customer.next_follow_up_at) {
    return <Tag color="default">暂无提醒</Tag>;
  }
  const followTime = dayjs(customer.next_follow_up_at);
  const timeStr = followTime.format("MM-DD HH:mm");
  const now = dayjs();
  const todayStart = now.startOf("day");
  const todayEnd = now.endOf("day");
  const tomorrowStart = todayStart.add(1, "day");
  const tomorrowEnd = tomorrowStart.endOf("day");
  const weekEnd = todayStart.endOf("week");

  if (followTime.isBefore(now)) {
    return <Tag color="error" icon={<ExclamationCircleOutlined />}>已逾期 {timeStr}</Tag>;
  }
  if (followTime.isAfter(todayStart) && followTime.isBefore(todayEnd)) {
    return <Tag color="orange" icon={<ClockCircleOutlined />}>今日跟进 {timeStr}</Tag>;
  }
  if (followTime.isAfter(tomorrowStart) && followTime.isBefore(tomorrowEnd)) {
    return <Tag color="blue">明日跟进 {timeStr}</Tag>;
  }
  if (followTime.isBefore(weekEnd)) {
    return <Tag color="processing">本周跟进 {timeStr}</Tag>;
  }
  return <Tag>{timeStr}</Tag>;
}

export default function CrmFollowUpPage() {
  const [dashboard, setDashboard] = useState<{
    total_customers: number;
    lead_conversion_count: number;
    manual_count: number;
    today_new: number;
    today_manual: number;
    pending_follow: number;
    interested: number;
    converted: number;
    overdue_follow: number;
    today_follow_up_count: number;
    tomorrow_follow_up_count: number;
    this_week_follow_up_count: number;
    status_counts: Record<string, number>;
    level_counts: Record<string, number>;
  } | null>(null);
  const [customers, setCustomers] = useState<CrmCustomer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);

  const [filters, setFilters] = useState<{
    source_type?: string;
    source_channel?: string;
    platform?: string;
    lead_level?: string;
    status?: string;
    owner_name?: string;
    keyword?: string;
    reminder?: string;
  }>({});

  const [selectedCustomer, setSelectedCustomer] = useState<CrmCustomer | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [followRecords, setFollowRecords] = useState<CrmFollowRecord[]>([]);
  const [followLoading, setFollowLoading] = useState(false);

  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [addFollowOpen, setAddFollowOpen] = useState(false);
  const [addFollowLoading, setAddFollowLoading] = useState(false);
  const [followForm] = Form.useForm();
  const [editNextFollowUpOpen, setEditNextFollowUpOpen] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm] = Form.useForm();

  const loadDashboard = useCallback(async () => {
    try {
      const data = await getCrmDashboard();
      setDashboard(data);
    } catch {}
  }, []);

  const loadCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCrmCustomers({
        ...filters,
        page,
        page_size: pageSize,
      });
      setCustomers(data.items);
      setTotal(data.total);
    } catch {
      message.error("加载客户列表失败");
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    void loadCustomers();
  }, [loadCustomers]);

  const loadFollowRecords = useCallback(async (customerId: number) => {
    setFollowLoading(true);
    try {
      const data = await getCrmFollowRecords(customerId, { page_size: 50 });
      setFollowRecords(data.items);
    } catch {
      message.error("加载跟进记录失败");
    } finally {
      setFollowLoading(false);
    }
  }, []);

  function openCustomerDetail(customer: CrmCustomer) {
    setSelectedCustomer(customer);
    setDrawerOpen(true);
    void loadFollowRecords(customer.id);
  }

  function getDisplayName(customer: CrmCustomer) {
    return customer.customer_name || customer.nickname || "未命名";
  }

  function handleReminderCardClick(reminder: string) {
    setFilters((prev) => ({
      ...prev,
      reminder: prev.reminder === reminder ? undefined : reminder,
    }));
    setPage(1);
  }

  async function handleStatusChange(newStatus: string) {
    if (!selectedCustomer) return;
    try {
      await updateCrmCustomer(selectedCustomer.id, { status: newStatus });
      message.success("状态已更新");
      setStatusModalOpen(false);
      setSelectedCustomer({ ...selectedCustomer, status: newStatus });
      void loadCustomers();
      void loadDashboard();
    } catch {
      message.error("更新状态失败");
    }
  }

  async function handleAddFollow() {
    if (!selectedCustomer) return;
    try {
      const values = await followForm.validateFields();
      setAddFollowLoading(true);
      await createCrmFollowRecord(selectedCustomer.id, {
        follow_type: values.follow_type || "manual",
        content: values.content,
        next_follow_up_at: values.next_follow_up_at
          ? values.next_follow_up_at.toISOString()
          : undefined,
      });
      message.success("跟进记录已添加");
      setAddFollowOpen(false);
      followForm.resetFields();
      void loadFollowRecords(selectedCustomer.id);
      void loadCustomers();
      void loadDashboard();
      const refreshed = await getCrmCustomers({ page: 1, page_size: 1 });
      const found = refreshed.items.find((c) => c.id === selectedCustomer.id);
      if (found) setSelectedCustomer(found);
    } catch (err) {
      if (err instanceof Error) message.error(err.message);
    } finally {
      setAddFollowLoading(false);
    }
  }

  async function handleUpdateNextFollowUp(date: dayjs.Dayjs | null) {
    if (!selectedCustomer) return;
    try {
      await updateCrmCustomer(selectedCustomer.id, {
        next_follow_up_at: date ? date.toISOString() : null,
      });
      message.success("下次跟进时间已更新");
      setEditNextFollowUpOpen(false);
      setSelectedCustomer({
        ...selectedCustomer,
        next_follow_up_at: date ? date.toISOString() : null,
      });
      void loadCustomers();
      void loadDashboard();
    } catch {
      message.error("更新失败");
    }
  }

  async function handleCreateCustomer() {
    try {
      const values = await createForm.validateFields();
      setCreateLoading(true);
      const payload: CrmCustomerManualCreate = {
        customer_name: values.customer_name || null,
        nickname: values.nickname || null,
        phone: values.phone || null,
        wechat: values.wechat || null,
        source_channel: values.source_channel || null,
        demand_type: values.demand_type || null,
        demand_description: values.demand_description || null,
        intended_amount: values.intended_amount ?? null,
        city: values.city || null,
        lead_level: values.lead_level || null,
        owner_name: values.owner_name || null,
        entered_by: values.entered_by || null,
        notes: values.notes || null,
        next_follow_up_at: values.next_follow_up_at
          ? values.next_follow_up_at.toISOString()
          : null,
      };
      await createCrmCustomer(payload);
      message.success("客户录入成功");
      setCreateModalOpen(false);
      createForm.resetFields();
      void loadCustomers();
      void loadDashboard();
    } catch (err) {
      if (err instanceof Error) message.error(err.message);
    } finally {
      setCreateLoading(false);
    }
  }

  const columns = [
    {
      title: "姓名/昵称",
      key: "name",
      width: 140,
      render: (_: unknown, record: CrmCustomer) => (
        <a onClick={() => openCustomerDetail(record)}>
          <div>{getDisplayName(record)}</div>
          {record.customer_name && record.nickname && record.customer_name !== record.nickname && (
            <Text type="secondary" style={{ fontSize: 12 }}>({record.nickname})</Text>
          )}
        </a>
      ),
    },
    {
      title: "手机/微信",
      key: "contact",
      width: 140,
      render: (_: unknown, record: CrmCustomer) => (
        <div>
          {record.phone && <div>{record.phone}</div>}
          {record.wechat && <Text type="secondary" style={{ fontSize: 12 }}>微信: {record.wechat}</Text>}
          {!record.phone && !record.wechat && "-"}
        </div>
      ),
    },
    {
      title: "来源",
      key: "source",
      width: 130,
      render: (_: unknown, record: CrmCustomer) => (
        <div>
          <Tag color={record.source_type === "manual" ? "purple" : "blue"} style={{ marginBottom: 2 }}>
            {SOURCE_TYPE_MAP[record.source_type] || record.source_type}
          </Tag>
          {record.source_channel && (
            <div><Text type="secondary" style={{ fontSize: 12 }}>{record.source_channel}</Text></div>
          )}
        </div>
      ),
    },
    {
      title: "需求",
      key: "demand",
      width: 150,
      ellipsis: true,
      render: (_: unknown, record: CrmCustomer) => (
        <div>
          {record.demand_type && <div>{record.demand_type}</div>}
          {record.intended_amount != null && (
            <Text type="secondary" style={{ fontSize: 12 }}>金额: {record.intended_amount}万</Text>
          )}
          {!record.demand_type && record.intended_amount == null && "-"}
        </div>
      ),
    },
    {
      title: "等级",
      dataIndex: "lead_level",
      key: "lead_level",
      width: 60,
      render: (val: string | null) =>
        val ? <Tag color={LEVEL_COLORS[val] || "default"}>{val}</Tag> : "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (val: string) => {
        const info = CRM_STATUS_MAP[val] || { label: val, color: "default" };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: "负责人",
      dataIndex: "owner_name",
      key: "owner_name",
      width: 80,
      render: (val: string | null) => val || "-",
    },
    {
      title: "跟进提醒",
      key: "reminder",
      width: 100,
      render: (_: unknown, record: CrmCustomer) => getReminderTag(record),
    },
    {
      title: "下次跟进",
      dataIndex: "next_follow_up_at",
      key: "next_follow_up_at",
      width: 120,
      render: (val: string | null) => {
        if (!val) return <Text type="secondary">未设置</Text>;
        return dayjs(val).format("MM-DD HH:mm");
      },
    },
    {
      title: "最近跟进",
      dataIndex: "last_follow_up_at",
      key: "last_follow_up_at",
      width: 110,
      render: (val: string | null) =>
        val ? dayjs(val).format("MM-DD HH:mm") : "-",
    },
  ];

  return (
    <div style={{ maxWidth: 1600, margin: "0 auto", padding: "24px 20px 48px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <Text
            type="secondary"
            style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}
          >
            CRM Follow-up Desk
          </Text>
          <Title level={2} style={{ margin: "4px 0 8px" }}>
            CRM 跟进台
          </Title>
          <Paragraph type="secondary">
            管理客户跟进状态、记录跟进内容、设置下次跟进时间。支持 AI 线索转入和手动录入。
          </Paragraph>
        </div>
        <Button
          type="primary"
          icon={<UserAddOutlined />}
          onClick={() => setCreateModalOpen(true)}
          size="large"
        >
          手动录入客户
        </Button>
      </div>

      {dashboard && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card>
                <Statistic
                  title="客户总数"
                  value={dashboard.total_customers}
                  prefix={<TeamOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card>
                <Statistic title="AI线索转入" value={dashboard.lead_conversion_count} valueStyle={{ color: "#1677ff" }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card>
                <Statistic title="手动录入" value={dashboard.manual_count} valueStyle={{ color: "#722ed1" }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card>
                <Statistic title="今日新增" value={dashboard.today_new} valueStyle={{ color: "#13c2c2" }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card>
                <Statistic title="待跟进" value={dashboard.pending_follow} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card>
                <Statistic title="有意向" value={dashboard.interested} valueStyle={{ color: "#fa8c16" }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4} lg={3}>
              <Card style={{ background: "#f6ffed", borderColor: "#b7eb8f" }}>
                <Statistic
                  title="已成交"
                  value={dashboard.converted}
                  valueStyle={{ color: "#52c41a" }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={6} md={6}>
              <Card
                hoverable
                style={
                  filters.reminder === "overdue"
                    ? { background: "#fff1f0", borderColor: "#ffa39e", borderWidth: 2 }
                    : dashboard.overdue_follow > 0
                      ? { background: "#fff2f0", borderColor: "#ffccc7" }
                      : undefined
                }
                onClick={() => handleReminderCardClick("overdue")}
              >
                <Statistic
                  title="逾期未跟进"
                  value={dashboard.overdue_follow}
                  valueStyle={dashboard.overdue_follow > 0 ? { color: "#cf1322" } : undefined}
                  prefix={<ExclamationCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6} md={6}>
              <Card
                hoverable
                style={
                  filters.reminder === "today"
                    ? { background: "#fff7e6", borderColor: "#ffd591", borderWidth: 2 }
                    : dashboard.today_follow_up_count > 0
                      ? { background: "#fffbe6", borderColor: "#ffe58f" }
                      : undefined
                }
                onClick={() => handleReminderCardClick("today")}
              >
                <Statistic
                  title="今日待跟进"
                  value={dashboard.today_follow_up_count}
                  valueStyle={{ color: "#d46b08" }}
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6} md={6}>
              <Card
                hoverable
                style={
                  filters.reminder === "tomorrow"
                    ? { background: "#e6f7ff", borderColor: "#91d5ff", borderWidth: 2 }
                    : undefined
                }
                onClick={() => handleReminderCardClick("tomorrow")}
              >
                <Statistic
                  title="明日待跟进"
                  value={dashboard.tomorrow_follow_up_count}
                  valueStyle={{ color: "#0958d9" }}
                  prefix={<BellOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6} md={6}>
              <Card
                hoverable
                style={
                  filters.reminder === "this_week"
                    ? { background: "#f6ffed", borderColor: "#b7eb8f", borderWidth: 2 }
                    : undefined
                }
                onClick={() => handleReminderCardClick("this_week")}
              >
                <Statistic
                  title="本周待跟进"
                  value={dashboard.this_week_follow_up_count}
                  valueStyle={{ color: "#389e0d" }}
                  prefix={<BellOutlined />}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Select
              placeholder="跟进提醒"
              allowClear
              style={{ width: 140 }}
              value={filters.reminder || undefined}
              onChange={(val) => setFilters({ ...filters, reminder: val })}
              options={REMINDER_FILTER_OPTIONS}
            />
          </Col>
          <Col>
            <Select
              placeholder="来源类型"
              allowClear
              style={{ width: 130 }}
              value={filters.source_type || undefined}
              onChange={(val) => setFilters({ ...filters, source_type: val })}
              options={[
                { value: "lead_conversion", label: "AI线索转入" },
                { value: "manual", label: "手动录入" },
                { value: "import", label: "批量导入" },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="来源渠道"
              allowClear
              style={{ width: 120 }}
              value={filters.source_channel || undefined}
              onChange={(val) => setFilters({ ...filters, source_channel: val })}
              options={SOURCE_CHANNEL_OPTIONS}
            />
          </Col>
          <Col>
            <Select
              placeholder="等级"
              allowClear
              style={{ width: 80 }}
              value={filters.lead_level || undefined}
              onChange={(val) => setFilters({ ...filters, lead_level: val })}
              options={[
                { value: "A", label: "A级" },
                { value: "B", label: "B级" },
                { value: "C", label: "C级" },
                { value: "D", label: "D级" },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="状态"
              allowClear
              style={{ width: 120 }}
              value={filters.status || undefined}
              onChange={(val) => setFilters({ ...filters, status: val })}
              options={Object.entries(CRM_STATUS_MAP).map(([value, { label }]) => ({
                value,
                label,
              }))}
            />
          </Col>
          <Col>
            <Input.Search
              placeholder="搜索姓名/手机"
              allowClear
              style={{ width: 180 }}
              onSearch={(val) => setFilters({ ...filters, keyword: val || undefined })}
            />
          </Col>
          <Col>
            <Button onClick={() => setFilters({})}>重置</Button>
          </Col>
        </Row>
      </Card>

      <Card>
        <Table
          rowKey="id"
          dataSource={customers}
          columns={columns}
          loading={loading}
          scroll={{ x: 1300 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          onRow={(record) => ({
            onClick: () => openCustomerDetail(record),
            style: { cursor: "pointer" },
          })}
        />
      </Card>

      <Drawer
        title={selectedCustomer ? getDisplayName(selectedCustomer) : "客户详情"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={680}
      >
        {selectedCustomer && (
          <div>
            <Descriptions column={2} bordered size="small" style={{ marginBottom: 24 }}>
              <Descriptions.Item label="姓名">{selectedCustomer.customer_name || "-"}</Descriptions.Item>
              <Descriptions.Item label="昵称">{selectedCustomer.nickname || "-"}</Descriptions.Item>
              <Descriptions.Item label="手机">{selectedCustomer.phone || "-"}</Descriptions.Item>
              <Descriptions.Item label="微信">{selectedCustomer.wechat || "-"}</Descriptions.Item>
              <Descriptions.Item label="城市">{selectedCustomer.city || "-"}</Descriptions.Item>
              <Descriptions.Item label="来源类型">
                <Tag color={selectedCustomer.source_type === "manual" ? "purple" : "blue"}>
                  {SOURCE_TYPE_MAP[selectedCustomer.source_type] || selectedCustomer.source_type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="来源渠道">{selectedCustomer.source_channel || "-"}</Descriptions.Item>
              <Descriptions.Item label="需求类型">{selectedCustomer.demand_type || "-"}</Descriptions.Item>
              <Descriptions.Item label="需求描述" span={2}>{selectedCustomer.demand_description || "-"}</Descriptions.Item>
              <Descriptions.Item label="意向金额">
                {selectedCustomer.intended_amount != null ? `${selectedCustomer.intended_amount}万` : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="等级">
                {selectedCustomer.lead_level ? (
                  <Tag color={LEVEL_COLORS[selectedCustomer.lead_level] || "default"}>
                    {selectedCustomer.lead_level}
                  </Tag>
                ) : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={(CRM_STATUS_MAP[selectedCustomer.status] || { color: "default" }).color}>
                  {(CRM_STATUS_MAP[selectedCustomer.status] || { label: selectedCustomer.status }).label}
                </Tag>
                <Button size="small" type="link" onClick={() => setStatusModalOpen(true)}>
                  修改
                </Button>
              </Descriptions.Item>
              <Descriptions.Item label="负责人">{selectedCustomer.owner_name || "-"}</Descriptions.Item>
              <Descriptions.Item label="录入人">{selectedCustomer.entered_by || "-"}</Descriptions.Item>
              <Descriptions.Item label="最近跟进">
                {selectedCustomer.last_follow_up_at
                  ? dayjs(selectedCustomer.last_follow_up_at).format("YYYY-MM-DD HH:mm")
                  : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="下次跟进">
                <Space>
                  {selectedCustomer.next_follow_up_at
                    ? dayjs(selectedCustomer.next_follow_up_at).format("YYYY-MM-DD HH:mm")
                    : "未设置"}
                  <Button size="small" onClick={() => setEditNextFollowUpOpen(true)}>
                    设置
                  </Button>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="跟进提醒" span={2}>
                {getReminderTag(selectedCustomer) || <Text type="secondary">-</Text>}
              </Descriptions.Item>
              {selectedCustomer.source_url && (
                <Descriptions.Item label="来源链接" span={2}>
                  <a href={selectedCustomer.source_url} target="_blank" rel="noopener noreferrer">
                    {selectedCustomer.source_url.slice(0, 60)}
                    {selectedCustomer.source_url.length > 60 ? "..." : ""}
                  </a>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="备注" span={2}>
                {selectedCustomer.notes || "-"}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Title level={5} style={{ margin: 0 }}>
                跟进记录
              </Title>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setAddFollowOpen(true)}
              >
                添加跟进
              </Button>
            </div>

            {followLoading ? (
              <Spin />
            ) : followRecords.length === 0 ? (
              <Empty description="暂无跟进记录" />
            ) : (
              <List
                dataSource={followRecords}
                renderItem={(record) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag>{FOLLOW_TYPE_MAP[record.follow_type] || record.follow_type}</Tag>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {dayjs(record.created_at).format("MM-DD HH:mm")}
                          </Text>
                        </Space>
                      }
                      description={
                        <div>
                          <Paragraph style={{ margin: "4px 0" }}>{record.content}</Paragraph>
                          {record.next_follow_up_at && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              下次跟进: {dayjs(record.next_follow_up_at).format("YYYY-MM-DD HH:mm")}
                            </Text>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </div>
        )}
      </Drawer>

      <Modal
        title="修改客户状态"
        open={statusModalOpen}
        onCancel={() => setStatusModalOpen(false)}
        footer={null}
      >
        <Space wrap>
          {Object.entries(CRM_STATUS_MAP).map(([value, { label, color }]) => (
            <Button
              key={value}
              type={selectedCustomer?.status === value ? "primary" : "default"}
              onClick={() => handleStatusChange(value)}
            >
              <Tag color={color} style={{ marginRight: 0 }}>{label}</Tag>
            </Button>
          ))}
        </Space>
      </Modal>

      <Modal
        title="添加跟进记录"
        open={addFollowOpen}
        onOk={handleAddFollow}
        onCancel={() => {
          setAddFollowOpen(false);
          followForm.resetFields();
        }}
        confirmLoading={addFollowLoading}
      >
        <Form form={followForm} layout="vertical">
          <Form.Item name="follow_type" label="跟进方式" initialValue="manual">
            <Select
              options={Object.entries(FOLLOW_TYPE_MAP).map(([value, label]) => ({
                value,
                label,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="content"
            label="跟进内容"
            rules={[{ required: true, message: "请输入跟进内容" }]}
          >
            <Input.TextArea rows={4} placeholder="记录本次跟进的内容..." />
          </Form.Item>
          <Form.Item name="next_follow_up_at" label="下次跟进时间">
            <DatePicker
              showTime
              style={{ width: "100%" }}
              placeholder="选择下次跟进时间"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="设置下次跟进时间"
        open={editNextFollowUpOpen}
        onCancel={() => setEditNextFollowUpOpen(false)}
        footer={null}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <DatePicker
            showTime
            style={{ width: "100%" }}
            placeholder="选择下次跟进时间"
            onChange={(date) => {
              if (date) {
                void handleUpdateNextFollowUp(date);
              }
            }}
          />
          <Button
            danger
            type="link"
            onClick={() => void handleUpdateNextFollowUp(null)}
          >
            清除跟进时间
          </Button>
        </Space>
      </Modal>

      <Modal
        title="手动录入客户"
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        onOk={handleCreateCustomer}
        confirmLoading={createLoading}
        width={680}
      >
        <Form form={createForm} layout="vertical">
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Form.Item name="customer_name" label="客户姓名">
                <Input placeholder="输入客户真实姓名" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="nickname" label="昵称">
                <Input placeholder="输入客户昵称" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Form.Item name="phone" label="手机号">
                <Input placeholder="输入手机号" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="wechat" label="微信号">
                <Input placeholder="输入微信号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Form.Item name="source_channel" label="来源渠道">
                <Select placeholder="选择来源渠道" allowClear options={SOURCE_CHANNEL_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="city" label="城市">
                <Input placeholder="输入城市" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Form.Item name="demand_type" label="需求类型">
                <Input placeholder="如：房贷、信用贷、经营贷" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="intended_amount" label="意向金额(万)">
                <InputNumber placeholder="输入意向金额" style={{ width: "100%" }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="demand_description" label="需求描述">
            <Input.TextArea rows={2} placeholder="描述客户具体需求..." />
          </Form.Item>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Form.Item name="lead_level" label="客户等级">
                <Select placeholder="选择等级" allowClear options={[
                  { value: "A", label: "A级" },
                  { value: "B", label: "B级" },
                  { value: "C", label: "C级" },
                  { value: "D", label: "D级" },
                ]} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="next_follow_up_at" label="下次跟进时间">
                <DatePicker showTime style={{ width: "100%" }} placeholder="选择时间" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12}>
              <Form.Item name="owner_name" label="负责人">
                <Input placeholder="输入负责人" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="entered_by" label="录入人">
                <Input placeholder="输入录入人" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="备注信息..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
