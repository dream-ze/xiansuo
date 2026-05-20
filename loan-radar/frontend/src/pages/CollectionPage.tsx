import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Table, Tag, Tabs, Typography, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  createCollectionTask,
  createMonitorSource,
  crawlMonitorSource,
  deleteMonitorSource,
  generateDemoData,
  getCollectorsCapabilities,
  getCrawlTasks,
  getFailureTypesMeta,
  getMonitorSources,
  getQueueStatus,
  rerunCrawlTask,
  runCollectionTask,
  toggleMonitorSource,
  type CollectorCapability,
  type CrawlTask,
  type MonitorSource,
  type MonitorSourceCreatePayload,
  type QueueStatus,
  type FailureTypesMetaResponse,
} from "../api";

const { Title, Text, Paragraph } = Typography;

const PLATFORM_OPTIONS = [
  { label: "小红书", value: "xhs" },
  { label: "抖音", value: "douyin" },
  { label: "知乎", value: "zhihu" },
];
const PLATFORM_LABELS: Record<string, string> = { xhs: "小红书", douyin: "抖音", zhihu: "知乎" };
const SOURCE_TYPE_OPTIONS = [
  { label: "关键词", value: "keyword" },
  { label: "同行账号", value: "competitor_account" },
  { label: "指定帖子链接", value: "manual_post" },
  { label: "爆款规则", value: "hot_post_rule" },
];
const COLLECTOR_TYPE_OPTIONS = [
  { label: "media_crawler：多平台采集", value: "media_crawler" },
];
const TASK_SOURCE_TYPE_OPTIONS = [
  { label: "关键词采集", value: "keyword" },
  { label: "同行账号采集", value: "account" },
  { label: "指定帖子采集", value: "post_url" },
];
const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: "排队中", color: "warning" },
  running: { label: "运行中", color: "processing" },
  success: { label: "成功", color: "success" },
  failed: { label: "失败", color: "error" },
  retrying: { label: "重试中", color: "warning" },
};

function MonitorSourcesTab() {
  const [items, setItems] = useState<MonitorSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [capabilities, setCapabilities] = useState<Record<string, CollectorCapability>>({});
  const [demoLoading, setDemoLoading] = useState(false);
  const [form] = Form.useForm();

  async function loadSources() {
    setLoading(true);
    try {
      setItems(await getMonitorSources());
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadCapabilities() {
    try {
      const result = await getCollectorsCapabilities();
      setCapabilities(result.collectors || {});
    } catch {
      setCapabilities({});
    }
  }

  useEffect(() => {
    void loadSources();
    void loadCapabilities();
  }, []);

  async function handleCreate(values: Record<string, unknown>) {
    try {
      const config: Record<string, unknown> = {
        collector_type: values.collector_type,
        max_posts: Number(values.max_posts) || 10,
        max_comments_per_post: Number(values.max_comments_per_post) || 10,
      };
      if (values.collector_type === "media_crawler") {
        config.login_type = values.login_type || "qrcode";
        config.enable_comments = values.enable_comments !== false;
        if (values.cookies) config.cookies = values.cookies;
      }
      if (values.time_range) {
        config.time_range = values.time_range;
      }
      const payload: MonitorSourceCreatePayload = {
        source_type: values.source_type as string,
        platform: values.platform as string,
        name: (values.name as string).trim(),
        value: (values.value as string).trim(),
        config,
        enabled: values.enabled !== false,
        schedule_enabled: values.schedule_enabled === true,
        schedule_cron: values.schedule_enabled ? (values.schedule_cron as string || "0 */2 * * *") : null,
      };
      await createMonitorSource(payload);
      message.success("监控源已创建");
      form.resetFields();
      await loadSources();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "创建失败");
    }
  }

  async function handleToggle(item: MonitorSource) {
    try {
      await toggleMonitorSource(item.id, !item.enabled);
      message.success(`${item.name} 已${item.enabled ? "停用" : "启用"}`);
      await loadSources();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "操作失败");
    }
  }

  async function handleDelete(item: MonitorSource) {
    try {
      await deleteMonitorSource(item.id);
      message.success(`${item.name} 已删除`);
      await loadSources();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "删除失败");
    }
  }

  async function handleCrawl(item: MonitorSource) {
    try {
      const result = await crawlMonitorSource(item.id);
      message.success(`${item.name} 已加入采集队列，任务 #${result.id}`);
      await loadSources();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "触发采集失败");
    }
  }

  async function handleGenerateDemo() {
    setDemoLoading(true);
    try {
      await generateDemoData();
      message.success("演示数据生成中，请稍后查看");
      await loadSources();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "生成演示数据失败");
    } finally {
      setDemoLoading(false);
    }
  }

  const columns = [
    { title: "名称", dataIndex: "name", ellipsis: true },
    { title: "平台", dataIndex: "platform", width: 90, render: (p: string) => PLATFORM_LABELS[p] || p },
    { title: "类型", dataIndex: "source_type", width: 100 },
    { title: "值", dataIndex: "value", ellipsis: true, width: 160 },
    {
      title: "时间范围", width: 90,
      render: (_: unknown, record: MonitorSource) => {
        const cfg = record.config as Record<string, unknown> | undefined;
        const tr = cfg?.time_range;
        if (!tr) return <Tag>不限</Tag>;
        const labels: Record<string, string> = { "7d": "7天", "15d": "15天", "30d": "30天", "90d": "90天" };
        return <Tag color="blue">{labels[String(tr)] || String(tr)}</Tag>;
      },
    },
    {
      title: "状态", dataIndex: "enabled", width: 80,
      render: (enabled: boolean) => <Tag color={enabled ? "success" : "default"}>{enabled ? "启用" : "停用"}</Tag>,
    },
    {
      title: "定时", dataIndex: "schedule_enabled", width: 80,
      render: (enabled: boolean) => enabled ? <Tag color="blue">已开启</Tag> : <Tag>关闭</Tag>,
    },
    {
      title: "最近采集", dataIndex: "last_crawled_at", width: 140,
      render: (v: string) => v ? dayjs(v).format("MM-DD HH:mm") : "-",
    },
    {
      title: "操作", width: 200,
      render: (_: unknown, record: MonitorSource) => (
        <Space size={4}>
          <Button size="small" type="primary" onClick={() => handleCrawl(record)}>采集</Button>
          <Button size="small" onClick={() => handleToggle(record)}>{record.enabled ? "停用" : "启用"}</Button>
          <Button size="small" danger onClick={() => handleDelete(record)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card size="small">
        <Space>
          <Button type="primary" onClick={handleGenerateDemo} loading={demoLoading}>🎭 一键生成演示数据</Button>
          <Text type="secondary">自动创建演示监控源并触发采集</Text>
        </Space>
      </Card>

      <Card title="新增监控源" size="small">
        <Form form={form} layout="vertical" onFinish={handleCreate} initialValues={{
          source_type: "keyword", platform: "xhs", name: "关键词 - 征信花了", value: "征信花了",
          collector_type: "media_crawler", max_posts: 10, max_comments_per_post: 10,
          enabled: true, schedule_enabled: false, schedule_cron: "0 */2 * * *",
          login_type: "qrcode", enable_comments: true, time_range: "",
        }}>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12} md={8}><Form.Item name="source_type" label="来源类型"><Select options={SOURCE_TYPE_OPTIONS} /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="platform" label="平台"><Select options={PLATFORM_OPTIONS} /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="collector_type" label="采集器"><Select options={COLLECTOR_TYPE_OPTIONS} /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="value" label="值" rules={[{ required: true }]}><Input placeholder="关键词/链接/规则" /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="max_posts" label="最大帖子数"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="max_comments_per_post" label="每帖评论数"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="login_type" label="登录方式"><Select options={[{ value: "qrcode", label: "扫码登录" }, { value: "cookie", label: "Cookie" }, { value: "phone", label: "手机号" }]} /></Form.Item></Col>
            <Col xs={24} md={16}><Form.Item name="cookies" label="Cookies（可选）"><Input.TextArea rows={1} placeholder="sessionid=...; userid=..." /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="enable_comments" label="采集评论" valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="time_range" label="时间范围"><Select options={[
              { value: "", label: "不限" },
              { value: "7d", label: "最近7天" },
              { value: "15d", label: "最近15天" },
              { value: "30d", label: "最近30天" },
              { value: "90d", label: "最近90天" },
            ]} /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="schedule_enabled" label="定时采集" valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="schedule_cron" label="Cron 表达式"><Input placeholder="0 */2 * * *" /></Form.Item></Col>
          </Row>
          <Form.Item><Button type="primary" htmlType="submit" icon={<PlusOutlined />}>创建监控源</Button></Form.Item>
        </Form>
      </Card>

      <Card title="监控源列表" size="small" extra={<Button icon={<ReloadOutlined />} onClick={loadSources}>刷新</Button>}>
        <Table dataSource={items} columns={columns} rowKey="id" loading={loading} size="small" scroll={{ x: 900 }} />
      </Card>

      {Object.keys(capabilities).length > 0 && (
        <Card title="采集器能力" size="small">
          <Table
            dataSource={Object.entries(capabilities).map(([key, cap]) => ({ key, ...cap }))}
            columns={[
              { title: "采集器", dataIndex: "name", key: "name" },
              { title: "状态", dataIndex: "status", key: "status", render: (s: string) => <Tag>{s}</Tag> },
              { title: "支持类型", dataIndex: "supports", key: "supports", render: (s: string[]) => s?.join(" / ") || "-" },
              { title: "说明", dataIndex: "description", key: "description", ellipsis: true },
            ]}
            size="small"
            scroll={{ x: 500 }}
            pagination={false}
          />
        </Card>
      )}
    </div>
  );
}

function CrawlTasksTab() {
  const [tasks, setTasks] = useState<(CrawlTask & { source_name?: string })[]>([]);
  const [loading, setLoading] = useState(true);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [failureMeta, setFailureMeta] = useState<FailureTypesMetaResponse | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const hasActiveTasks = useMemo(
    () => tasks.some((t) => t.status === "pending" || t.status === "running" || t.status === "retrying"),
    [tasks],
  );

  async function loadTasks() {
    setLoading(true);
    try {
      const [taskResult, sources] = await Promise.all([getCrawlTasks(), getMonitorSources()]);
      const sourceMap = new Map(sources.map((s) => [s.id, s]));
      setTasks(taskResult.items.map((t) => ({
        ...t,
        source_name: t.source_id == null ? "手动创建" : sourceMap.get(t.source_id)?.name ?? `监控源 #${t.source_id}`,
      })));
    } catch (err) {
      message.error(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
    void getQueueStatus().then(setQueueStatus).catch(() => {});
    void getFailureTypesMeta().then(setFailureMeta).catch(() => {});
  }, []);

  useEffect(() => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    if (hasActiveTasks) {
      pollingRef.current = setInterval(() => {
        void (async () => {
          try {
            const [taskResult, sources] = await Promise.all([getCrawlTasks(), getMonitorSources()]);
            const sourceMap = new Map(sources.map((s) => [s.id, s]));
            setTasks(taskResult.items.map((t) => ({
              ...t,
              source_name: t.source_id == null ? "手动创建" : sourceMap.get(t.source_id)?.name ?? `监控源 #${t.source_id}`,
            })));
            const q = await getQueueStatus().catch(() => null);
            if (q) setQueueStatus(q);
          } catch {}
        })();
      }, 3000);
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [hasActiveTasks]);

  async function handleSubmit(values: Record<string, unknown>) {
    setSubmitting(true);
    try {
      const created = await createCollectionTask({
        platform: values.platform as string,
        source_type: values.source_type as "keyword" | "account" | "post_url",
        source_value: (values.source_value as string).trim(),
        limit_count: Number(values.limit_count) || 5,
      });
      await runCollectionTask(created.id);
      message.success(`任务 #${created.id} 已创建并加入队列`);
      form.resetFields();
      await loadTasks();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRerun(task: CrawlTask) {
    setBusyId(task.id);
    try {
      await rerunCrawlTask(task.id);
      message.info(`任务 #${task.id} 已重新启动`);
      await loadTasks();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "重跑失败");
    } finally {
      setBusyId(null);
    }
  }

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "平台", dataIndex: "platform", width: 80, render: (p: string) => PLATFORM_LABELS[p] || p },
    { title: "来源", dataIndex: "source_name", ellipsis: true, width: 140 },
    {
      title: "状态", dataIndex: "status", width: 90,
      render: (s: string) => {
        const info = STATUS_MAP[s] || { label: s, color: "default" };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    { title: "帖子", dataIndex: "post_count", width: 60 },
    { title: "评论", dataIndex: "comment_count", width: 60 },
    { title: "线索", dataIndex: "lead_count", width: 60, render: (v: number) => <Text strong>{v}</Text> },
    {
      title: "失败类型", dataIndex: "failure_type", width: 100,
      render: (ft: string) => ft ? (failureMeta?.[ft]?.label || ft) : "-",
    },
    { title: "开始时间", dataIndex: "started_at", width: 130, render: (v: string) => v ? dayjs(v).format("MM-DD HH:mm") : "-" },
    {
      title: "操作", width: 120,
      render: (_: unknown, record: CrawlTask) => (
        <Space size={4}>
          {record.status === "failed" && (
            <Button size="small" onClick={() => handleRerun(record)} loading={busyId === record.id}>重试</Button>
          )}
          {record.status === "success" && (
            <Link to={`/leads?source_type=${record.source_type}`}><Button size="small" type="link">线索</Button></Link>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {queueStatus && (
        <Card size="small">
          <Space>
            {queueStatus.active_task_id ? (
              <><Tag color="processing">运行中</Tag><Text>正在执行任务 #{queueStatus.active_task_id}</Text></>
            ) : (
              <><Tag>空闲</Tag><Text>队列空闲</Text></>
            )}
            {queueStatus.queue_size > 0 && <Text type="secondary">· 排队 {queueStatus.queue_size} 个</Text>}
          </Space>
        </Card>
      )}

      <Card title="创建采集任务" size="small">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
          platform: "xhs", source_type: "keyword", limit_count: 5,
        }}>
          <Row gutter={[16, 12]}>
            <Col xs={24} sm={12} md={6}><Form.Item name="platform" label="平台"><Select options={PLATFORM_OPTIONS} /></Form.Item></Col>
            <Col xs={24} sm={12} md={6}><Form.Item name="source_type" label="类型"><Select options={TASK_SOURCE_TYPE_OPTIONS} /></Form.Item></Col>
            <Col xs={12} sm={8} md={4}><Form.Item name="limit_count" label="数量"><InputNumber min={1} max={100} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} sm={12} md={8}><Form.Item name="source_value" label="采集目标" rules={[{ required: true }]}><Input placeholder="关键词/链接/URL" /></Form.Item></Col>
          </Row>
          <Form.Item><Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={submitting}>创建并运行</Button></Form.Item>
        </Form>
      </Card>

      <Card title="任务列表" size="small" extra={<Button icon={<ReloadOutlined />} onClick={loadTasks}>刷新</Button>}>
        <Table dataSource={tasks} columns={columns} rowKey="id" loading={loading} size="small" scroll={{ x: 1000 }} />
      </Card>
    </div>
  );
}

export default function CollectionPage() {
  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 20px 48px" }}>
      <div style={{ marginBottom: 20 }}>
        <Text type="secondary" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}>采集管理</Text>
        <Title level={2} style={{ margin: "4px 0 8px" }}>采集中心</Title>
        <Paragraph type="secondary">管理监听源和采集任务，一站式配置数据采集。 <Link to="/xhs/crawler" style={{ fontSize: 13 }}>XHS 高级采集 →</Link></Paragraph>
      </div>
      <Tabs
        defaultActiveKey="sources"
        items={[
          { key: "sources", label: "监听源", children: <MonitorSourcesTab /> },
          { key: "tasks", label: "采集任务", children: <CrawlTasksTab /> },
        ]}
      />
    </div>
  );
}
