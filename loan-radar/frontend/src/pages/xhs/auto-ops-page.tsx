import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";

import { PageHeader } from "../../components/AppShell";
import {
  createAutoTask,
  deleteAutoTask,
  fetchAccounts,
  fetchAutoTasks,
  runAutoTask,
  updateAutoTask,
} from "../../api/xhs-api";
import { formatShanghaiTime } from "../../lib/time";
import type { AutoTask, AutoTaskRunResult, PlatformAccount } from "../../api/xhs-types";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const CYAN = "#00d4ff";
const GREEN = "#00e396";
const RED = "#ff4560";
const AMBER = "#ffb020";

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  active: { color: "green", label: "运行中" },
  paused: { color: "default", label: "已暂停" },
  completed: { color: "blue", label: "已完成" },
};

function getStatusTag(s: string) {
  const cfg = STATUS_CONFIG[s] ?? { color: "default", label: s };
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
}

const techPanelStyle: React.CSSProperties = {
  background: "rgba(17,24,39,0.75)",
  borderRadius: 8,
  border: "1px solid rgba(0,212,255,0.1)",
  backdropFilter: "blur(8px)",
  boxShadow: "0 0 12px rgba(0,212,255,0.05)",
};

const techPanelHeaderStyle: React.CSSProperties = {
  borderBottom: "1px solid rgba(0,212,255,0.08)",
  color: CYAN,
};

const cardBodyStyle: React.CSSProperties = {
  padding: 16,
};

const formItemStyle: React.CSSProperties = {
  marginBottom: 14,
};

const inputStyle: React.CSSProperties = {
  background: "rgba(0,212,255,0.04)",
  border: "1px solid rgba(0,212,255,0.12)",
  borderRadius: 6,
};

export function AutoOpsPage() {
  const [tasks, setTasks] = useState<AutoTask[]>([]);
  const [pcAccounts, setPcAccounts] = useState<PlatformAccount[]>([]);
  const [creatorAccounts, setCreatorAccounts] = useState<PlatformAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createKeywords, setCreateKeywords] = useState("");
  const [createPcAccountId, setCreatePcAccountId] = useState<number | null>(null);
  const [createCreatorAccountId, setCreateCreatorAccountId] = useState<number | null>(null);
  const [createInstruction, setCreateInstruction] = useState("");
  const [createScheduleType, setCreateScheduleType] = useState<string>("manual");
  const [createScheduleTime, setCreateScheduleTime] = useState<string>("09:00");
  const [createScheduleDays, setCreateScheduleDays] = useState<string>("");
  const [createIntervalHours, setCreateIntervalHours] = useState<number>(24);
  const [isCreating, setIsCreating] = useState(false);

  const [editTask, setEditTask] = useState<AutoTask | null>(null);
  const [editName, setEditName] = useState("");
  const [editKeywords, setEditKeywords] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [editScheduleType, setEditScheduleType] = useState("manual");
  const [editScheduleTime, setEditScheduleTime] = useState("09:00");
  const [editScheduleDays, setEditScheduleDays] = useState("");
  const [editIntervalHours, setEditIntervalHours] = useState(24);
  const [isSaving, setIsSaving] = useState(false);

  const [runningTaskId, setRunningTaskId] = useState<number | null>(null);
  const [lastRunResult, setLastRunResult] = useState<AutoTaskRunResult | null>(null);

  function parseKeywords(text: string): string[] {
    return text
      .split("\n")
      .map((k) => k.trim())
      .filter(Boolean);
  }

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const [tasksRes, accountsRes] = await Promise.all([
        fetchAutoTasks(),
        fetchAccounts("xhs"),
      ]);
      setTasks(tasksRes.items);
      setPcAccounts(accountsRes.filter((a) => a.sub_type === "pc"));
      setCreatorAccounts(accountsRes.filter((a) => a.sub_type === "creator"));
    } catch {
      setError("加载自动运营任务失败。");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleCreate() {
    const keywords = parseKeywords(createKeywords);
    if (!createName.trim() || keywords.length === 0 || !createPcAccountId || !createCreatorAccountId) {
      setError("请填写任务名称、至少一个关键词，并选择 PC 和 Creator 账号。");
      return;
    }
    setIsCreating(true);
    setError(null);
    setMessage(null);
    try {
      const created = await createAutoTask({
        name: createName.trim(),
        keywords,
        pc_account_id: createPcAccountId,
        creator_account_id: createCreatorAccountId,
        ai_instruction: createInstruction,
        schedule_type: createScheduleType as "manual" | "daily" | "weekly" | "interval",
        schedule_time: createScheduleTime,
        schedule_days: createScheduleDays,
        schedule_interval_hours: createIntervalHours,
      });
      setTasks((prev) => [created, ...prev]);
      setShowCreate(false);
      setCreateName("");
      setCreateKeywords("");
      setCreatePcAccountId(null);
      setCreateCreatorAccountId(null);
      setCreateInstruction("");
      setCreateScheduleType("manual");
      setCreateScheduleTime("09:00");
      setCreateScheduleDays("");
      setCreateIntervalHours(24);
      setMessage(`自动任务"${created.name}"已创建。`);
    } catch {
      setError("创建自动任务失败。");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleToggleStatus(task: AutoTask) {
    const newStatus = task.status === "active" ? "paused" : "active";
    setError(null);
    setMessage(null);
    try {
      const updated = await updateAutoTask(task.id, { status: newStatus });
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setMessage(`任务"${updated.name}"已${newStatus === "active" ? "恢复" : "暂停"}。`);
    } catch {
      setError("更新任务状态失败。");
    }
  }

  async function handleDelete(taskId: number) {
    setError(null);
    setMessage(null);
    try {
      await deleteAutoTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setMessage("自动任务已删除。");
    } catch {
      setError("删除自动任务失败。");
    }
  }

  async function handleRun(task: AutoTask) {
    setRunningTaskId(task.id);
    setError(null);
    setMessage(null);
    setLastRunResult(null);
    try {
      const result = await runAutoTask(task.id);
      setLastRunResult(result);
      setTasks((prev) => prev.map((t) => (t.id === result.auto_task.id ? result.auto_task : t)));
      const draftInfo = result.draft?.id
        ? `草稿 #${result.draft.id}「${result.draft.title}」已创建`
        : "未生成草稿";
      const publishInfo = result.publish_job?.id
        ? `，发布任务 #${result.publish_job.id} 待确认`
        : "";
      const sourceInfo = result.source_note?.id
        ? `来源笔记 #${result.source_note.id}`
        : "无匹配来源笔记";
      setMessage(
        `任务"${task.name}"执行完成 — ${sourceInfo}，关键词: ${result.keyword}，${draftInfo}${publishInfo}。`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "请检查账号和模型配置。";
      setError(`执行失败：${msg}`);
    } finally {
      setRunningTaskId(null);
    }
  }

  function openEdit(task: AutoTask) {
    setEditTask(task);
    setEditName(task.name);
    setEditKeywords((task.keywords || []).join("\n"));
    setEditInstruction(task.ai_instruction);
    setEditScheduleType(task.schedule_type || "manual");
    setEditScheduleTime(task.schedule_time || "09:00");
    setEditScheduleDays(task.schedule_days || "");
    setEditIntervalHours(task.schedule_interval_hours || 24);
  }

  async function handleSaveEdit() {
    if (!editTask) return;
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const keywords = parseKeywords(editKeywords);
      const updated = await updateAutoTask(editTask.id, {
        name: editName.trim() || undefined,
        keywords: keywords.length > 0 ? keywords : undefined,
        ai_instruction: editInstruction,
        schedule_type: editScheduleType as "manual" | "daily" | "weekly" | "interval",
        schedule_time: editScheduleTime,
        schedule_days: editScheduleDays,
        schedule_interval_hours: editIntervalHours,
      });
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setEditTask(null);
      setMessage(`任务"${updated.name}"已更新。`);
    } catch {
      setError("更新任务失败。");
    } finally {
      setIsSaving(false);
    }
  }

  function scheduleDesc(task: AutoTask): string {
    if (task.schedule_type === "daily") return `每日 ${task.schedule_time}`;
    if (task.schedule_type === "weekly") {
      const dayMap: Record<string, string> = {"1":"一","2":"二","3":"三","4":"四","5":"五","6":"六","7":"日"};
      const days = (task.schedule_days || "").split(",").map(d => dayMap[d] || d).join("、");
      return `每周${days} ${task.schedule_time}`;
    }
    if (task.schedule_type === "interval") return `每 ${task.schedule_interval_hours} 小时`;
    return "手动触发";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <PageHeader
        eyebrow="XHS Auto Operations"
        title="自动运营"
        description="设置关键词、自动抓取热门笔记、AI 改写后自动创建发布任务，实现全自动内容生产管线。"
        action={
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={isLoading}>
            刷新
          </Button>
        }
      />

      {error && (
        <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />
      )}
      {message && (
        <Alert type="success" message={message} showIcon closable onClose={() => setMessage(null)} />
      )}

      {isLoading ? (
        <Card style={techPanelStyle} styles={{ body: cardBodyStyle }}>
          <div style={{ textAlign: "center", padding: 48 }}>
            <Spin size="large" />
            <Paragraph style={{ color: "rgba(255,255,255,0.35)", marginTop: 16 }}>正在加载自动运营任务...</Paragraph>
          </div>
        </Card>
      ) : tasks.length === 0 && !showCreate ? (
        <Card style={techPanelStyle} styles={{ body: cardBodyStyle }}>
          <Empty
            image={<ThunderboltOutlined style={{ fontSize: 48, color: "rgba(0,212,255,0.3)", filter: "drop-shadow(0 0 8px rgba(0,212,255,0.2))" }} />}
            imageStyle={{ height: 64 }}
            description={
              <div>
                <Text strong style={{ fontSize: 16, color: "rgba(255,255,255,0.55)" }}>
                  暂无自动运营任务
                </Text>
                <br />
                <Text type="secondary">点击"新建任务"开始配置关键词自动抓取、AI 改写和发布管线。</Text>
              </div>
            }
          />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {tasks.map((task) => (
            <Col xs={24} md={12} xl={8} key={task.id}>
              <Card
                style={techPanelStyle}
                styles={{ body: cardBodyStyle, header: techPanelHeaderStyle }}
                title={
                  <Space>
                    <ThunderboltOutlined style={{ color: task.status === "active" ? GREEN : "rgba(255,255,255,0.3)", filter: task.status === "active" ? "drop-shadow(0 0 4px rgba(0,227,150,0.5))" : "none" }} />
                    <Text ellipsis style={{ maxWidth: 180, color: "rgba(255,255,255,0.85)" }}>
                      {task.name}
                    </Text>
                  </Space>
                }
                extra={getStatusTag(task.status)}
              >
                <div style={{ marginBottom: 12 }}>
                  <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 4 }}>
                    关键词
                  </Text>
                  <Space size={4} wrap>
                    {(task.keywords || []).map((kw) => (
                      <Tag key={kw} style={{
                        margin: 0,
                        background: "rgba(0,212,255,0.08)",
                        border: "1px solid rgba(0,212,255,0.2)",
                        color: CYAN,
                        fontSize: 11,
                      }}>
                        {kw}
                      </Tag>
                    ))}
                  </Space>
                </div>

                <Row gutter={16} style={{ marginBottom: 12 }}>
                  <Col xs={24} sm={8}>
                    <Statistic
                      title="已发布"
                      value={task.total_published}
                      valueStyle={{ fontSize: 20, color: CYAN, textShadow: "0 0 8px rgba(0,212,255,0.2)" }}
                    />
                  </Col>
                </Row>

                <Space direction="vertical" size={2} style={{ width: "100%", marginBottom: 12 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    上次运行：{formatShanghaiTime(task.last_run_at)}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    下次运行：{formatShanghaiTime(task.next_run_at)}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    创建时间：{formatShanghaiTime(task.created_at)}
                  </Text>
                </Space>

                {task.ai_instruction && (
                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 2 }}>
                      AI 指令
                    </Text>
                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 2 }}
                      style={{ fontSize: 12, marginBottom: 0 }}
                    >
                      {task.ai_instruction}
                    </Paragraph>
                  </div>
                )}

                <Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 4 }}>
                  调度：{scheduleDesc(task)}
                </Text>
                {task.next_run_at && (
                  <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
                    下次执行：{formatShanghaiTime(task.next_run_at)}
                  </Text>
                )}

                <Space wrap style={{ marginTop: 8 }}>
                  <Button
                    type="primary"
                    size="small"
                    icon={<PlayCircleOutlined />}
                    onClick={() => handleRun(task)}
                    loading={runningTaskId === task.id}
                    disabled={runningTaskId !== null && runningTaskId !== task.id}
                  >
                    立即执行
                  </Button>
                  <Button
                    size="small"
                    icon={task.status === "active" ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                    onClick={() => handleToggleStatus(task)}
                  >
                    {task.status === "active" ? "暂停" : "恢复"}
                  </Button>
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => openEdit(task)}
                  >
                    编辑
                  </Button>
                  <Popconfirm
                    title="确认删除此自动任务？"
                    onConfirm={() => handleDelete(task.id)}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Button size="small" danger icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {lastRunResult && (
        <Card
          title={
            <Space>
              <CheckCircleOutlined style={{ color: GREEN, filter: "drop-shadow(0 0 4px rgba(0,227,150,0.5))" }} />
              <span style={{ color: CYAN }}>最近一次执行结果</span>
            </Space>
          }
          style={techPanelStyle}
          styles={{ body: cardBodyStyle, header: techPanelHeaderStyle }}
        >
          <Descriptions column={{ xs: 1, md: 2, lg: 4 }} size="small">
            <Descriptions.Item label="关键词">{lastRunResult.keyword}</Descriptions.Item>
            <Descriptions.Item label="来源笔记">
              {lastRunResult.source_note?.id
                ? `#${lastRunResult.source_note.id} ${lastRunResult.source_note.title}`
                : "无匹配来源"}
            </Descriptions.Item>
            <Descriptions.Item label="草稿">
              {lastRunResult.draft?.id
                ? `#${lastRunResult.draft.id} (${lastRunResult.draft.status})`
                : "未生成"}
            </Descriptions.Item>
            <Descriptions.Item label="发布任务">
              {lastRunResult.publish_job?.id
                ? `#${lastRunResult.publish_job.id} (${lastRunResult.publish_job.status})`
                : "跳过（未配置 Creator 账号）"}
            </Descriptions.Item>
          </Descriptions>
          {lastRunResult.draft?.id && (
            <div style={{ marginTop: 12 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                生成标题：{lastRunResult.draft.title}
              </Text>
              <Paragraph
                type="secondary"
                ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
                style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}
              >
                {lastRunResult.draft.body}
              </Paragraph>
            </div>
          )}
        </Card>
      )}

      {showCreate && (
        <Card
          title={
            <Space>
              <PlusOutlined style={{ color: CYAN }} />
              <span style={{ color: CYAN }}>◈ 新建自动运营任务</span>
            </Space>
          }
          style={techPanelStyle}
          styles={{ body: { padding: "20px 24px" }, header: techPanelHeaderStyle }}
          extra={
            <Button type="text" onClick={() => setShowCreate(false)} style={{ color: "rgba(255,255,255,0.45)" }}>
              取消
            </Button>
          }
        >
          <Form layout="vertical">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label="任务名称" required style={formItemStyle}>
                  <Input
                    placeholder="如：低卡早餐自动发布"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    maxLength={128}
                    style={inputStyle}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="关键词（每行一个）" required style={formItemStyle}>
                  <TextArea
                    placeholder={"低卡早餐\n减脂食谱\n健康饮食"}
                    value={createKeywords}
                    onChange={(e) => setCreateKeywords(e.target.value)}
                    rows={3}
                    style={inputStyle}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label="PC 账号（用于抓取）" required style={formItemStyle}>
                  <Select
                    placeholder="选择 PC 账号"
                    value={createPcAccountId}
                    onChange={(v) => setCreatePcAccountId(v)}
                    options={pcAccounts.map((a) => ({
                      value: a.id,
                      label: `${a.nickname || "PC"} (#${a.id})`,
                    }))}
                    allowClear
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="Creator 账号（用于发布）" required style={formItemStyle}>
                  <Select
                    placeholder="选择 Creator 账号"
                    value={createCreatorAccountId}
                    onChange={(v) => setCreateCreatorAccountId(v)}
                    options={creatorAccounts.map((a) => ({
                      value: a.id,
                      label: `${a.nickname || "Creator"} (#${a.id})`,
                    }))}
                    allowClear
                  />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="AI 改写指令（可选）" style={formItemStyle}>
              <TextArea
                placeholder="如：改写为种草风格，加入个人体验感受，适合 25-35 岁女性阅读"
                value={createInstruction}
                onChange={(e) => setCreateInstruction(e.target.value)}
                rows={3}
                maxLength={2000}
                style={inputStyle}
              />
            </Form.Item>

            <Form.Item label="调度方式" style={formItemStyle}>
              <Select value={createScheduleType} onChange={setCreateScheduleType} options={[
                { value: "manual", label: "手动触发" },
                { value: "daily", label: "每日定时" },
                { value: "weekly", label: "每周定时" },
                { value: "interval", label: "自定义间隔" },
              ]} />
            </Form.Item>

            {(createScheduleType === "daily" || createScheduleType === "weekly") && (
              <Form.Item label="执行时间" style={formItemStyle}>
                <Input value={createScheduleTime} onChange={(e) => setCreateScheduleTime(e.target.value)} placeholder="HH:MM" style={{ width: 120, ...inputStyle }} />
              </Form.Item>
            )}

            {createScheduleType === "weekly" && (
              <Form.Item label="执行日期" style={formItemStyle}>
                <Checkbox.Group
                  value={createScheduleDays.split(",").filter(Boolean)}
                  onChange={(vals) => setCreateScheduleDays(vals.join(","))}
                  options={[
                    { label: "周一", value: "1" },
                    { label: "周二", value: "2" },
                    { label: "周三", value: "3" },
                    { label: "周四", value: "4" },
                    { label: "周五", value: "5" },
                    { label: "周六", value: "6" },
                    { label: "周日", value: "7" },
                  ]}
                />
              </Form.Item>
            )}

            {createScheduleType === "interval" && (
              <Form.Item label="间隔小时" style={formItemStyle}>
                <InputNumber min={1} max={168} value={createIntervalHours} onChange={(v) => setCreateIntervalHours(v ?? 24)} />
              </Form.Item>
            )}

            <Form.Item style={{ marginBottom: 0, marginTop: 4 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
                loading={isCreating}
                block
                style={{
                  height: 40,
                  borderRadius: 6,
                  background: `linear-gradient(135deg, ${CYAN}, #0099cc)`,
                  border: "none",
                  boxShadow: `0 0 16px ${CYAN}30`,
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                创建任务
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {!showCreate && (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setShowCreate(true)}
          block
          style={{
            marginTop: 16,
            height: 40,
            borderRadius: 6,
            background: `linear-gradient(135deg, ${CYAN}, #0099cc)`,
            border: "none",
            boxShadow: `0 0 16px ${CYAN}30`,
            fontWeight: 600,
          }}
        >
          新建自动运营任务
        </Button>
      )}

      <Modal
        title={<span style={{ color: CYAN }}>◈ 编辑自动运营任务</span>}
        open={editTask !== null}
        onOk={handleSaveEdit}
        onCancel={() => setEditTask(null)}
        confirmLoading={isSaving}
        okText="保存"
        cancelText="取消"
        styles={{
          content: {
            background: "rgba(17,24,39,0.95)",
            border: "1px solid rgba(0,212,255,0.15)",
            borderRadius: 12,
            boxShadow: "0 0 30px rgba(0,212,255,0.1), 0 8px 32px rgba(0,0,0,0.5)",
          },
          header: {
            background: "transparent",
            borderBottom: "1px solid rgba(0,212,255,0.08)",
          },
          body: {
            background: "transparent",
          },
          footer: {
            background: "transparent",
            borderTop: "1px solid rgba(0,212,255,0.08)",
          },
        }}
      >
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="任务名称" style={formItemStyle}>
            <Input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              maxLength={128}
              style={inputStyle}
            />
          </Form.Item>
          <Form.Item label="关键词（每行一个）" style={formItemStyle}>
            <TextArea
              value={editKeywords}
              onChange={(e) => setEditKeywords(e.target.value)}
              rows={3}
              style={inputStyle}
            />
          </Form.Item>
          <Form.Item label="AI 改写指令" style={formItemStyle}>
            <TextArea
              value={editInstruction}
              onChange={(e) => setEditInstruction(e.target.value)}
              rows={3}
              maxLength={2000}
              style={inputStyle}
            />
          </Form.Item>

          <Form.Item label="调度方式" style={formItemStyle}>
            <Select value={editScheduleType} onChange={setEditScheduleType} options={[
              { value: "manual", label: "手动触发" },
              { value: "daily", label: "每日定时" },
              { value: "weekly", label: "每周定时" },
              { value: "interval", label: "自定义间隔" },
            ]} />
          </Form.Item>

          {(editScheduleType === "daily" || editScheduleType === "weekly") && (
            <Form.Item label="执行时间" style={formItemStyle}>
              <Input value={editScheduleTime} onChange={(e) => setEditScheduleTime(e.target.value)} placeholder="HH:MM" style={{ width: 120, ...inputStyle }} />
            </Form.Item>
          )}

          {editScheduleType === "weekly" && (
            <Form.Item label="执行日期" style={formItemStyle}>
              <Checkbox.Group
                value={editScheduleDays.split(",").filter(Boolean)}
                onChange={(vals) => setEditScheduleDays(vals.join(","))}
                options={[
                  { label: "周一", value: "1" },
                  { label: "周二", value: "2" },
                  { label: "周三", value: "3" },
                  { label: "周四", value: "4" },
                  { label: "周五", value: "5" },
                  { label: "周六", value: "6" },
                  { label: "周日", value: "7" },
                ]}
              />
            </Form.Item>
          )}

          {editScheduleType === "interval" && (
            <Form.Item label="间隔小时" style={formItemStyle}>
              <InputNumber min={1} max={168} value={editIntervalHours} onChange={(v) => setEditIntervalHours(v ?? 24)} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
