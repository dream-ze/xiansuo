import {
  CheckCircleOutlined,
  CloudServerOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Row,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "../components/AppShell";
import { getCookieStatus, getMediaCrawlerHealth, getSchedulerStatus } from "../api/index";
import type { CookiePlatformStatus, MediaCrawlerHealth, SchedulerStatus } from "../api/types";
import { fetchAccounts, refreshAccountStatus } from "../api/xhs-api";
import type { PlatformAccount } from "../api/xhs-types";

const { Text, Paragraph } = Typography;

function accountStatusTag(status: string) {
  switch (status) {
    case "active":
    case "healthy":
      return <Tag color="success"><CheckCircleOutlined /> 健康</Tag>;
    case "expired":
      return <Tag color="error"><ExclamationCircleOutlined /> 已过期</Tag>;
    case "risk":
      return <Tag color="warning"><ExclamationCircleOutlined /> 风险</Tag>;
    default:
      return <Tag color="default">{status || "未知"}</Tag>;
  }
}

function subTypeLabel(subType: string | null) {
  if (subType === "pc") return "PC 端";
  if (subType === "creator") return "创作者端";
  return "-";
}

export function SettingsPage() {
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);

  const [mcHealth, setMcHealth] = useState<MediaCrawlerHealth | null>(null);
  const [mcLoading, setMcLoading] = useState(true);
  const [mcError, setMcError] = useState<string | null>(null);

  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(true);

  const [cookieStatus, setCookieStatus] = useState<CookiePlatformStatus[]>([]);
  const [cookieLoading, setCookieLoading] = useState(true);

  const loadAccounts = useCallback(async () => {
    setAccountsLoading(true);
    setAccountsError(null);
    try {
      const items = await fetchAccounts("xhs");
      setAccounts(items);
    } catch (err) {
      setAccountsError(err instanceof Error ? err.message : "加载账号失败");
    } finally {
      setAccountsLoading(false);
    }
  }, []);

  const loadMcHealth = useCallback(async () => {
    setMcLoading(true);
    setMcError(null);
    try {
      const health = await getMediaCrawlerHealth();
      setMcHealth(health);
    } catch (err) {
      setMcError(err instanceof Error ? err.message : "加载 MediaCrawler 状态失败");
    } finally {
      setMcLoading(false);
    }
  }, []);

  const loadScheduler = useCallback(async () => {
    setSchedulerLoading(true);
    try {
      const status = await getSchedulerStatus();
      setScheduler(status);
    } catch {
      setScheduler(null);
    } finally {
      setSchedulerLoading(false);
    }
  }, []);

  const loadCookieStatus = useCallback(async () => {
    setCookieLoading(true);
    try {
      const result = await getCookieStatus();
      setCookieStatus(result.platforms);
    } catch {
      setCookieStatus([]);
    } finally {
      setCookieLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.all([loadAccounts(), loadMcHealth(), loadScheduler(), loadCookieStatus()]);
  }, [loadAccounts, loadMcHealth, loadScheduler, loadCookieStatus]);

  async function handleRefreshAccount(id: number) {
    setRefreshingId(id);
    try {
      await refreshAccountStatus(id);
      await loadAccounts();
    } catch {
      // silent
    } finally {
      setRefreshingId(null);
    }
  }

  const healthyCount = accounts.filter((a) => a.status === "active" || a.status === "healthy").length;
  const expiredCount = accounts.filter((a) => a.status === "expired").length;

  const accountColumns = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 60,
    },
    {
      title: "昵称",
      dataIndex: "nickname",
      key: "nickname",
    },
    {
      title: "类型",
      dataIndex: "sub_type",
      key: "sub_type",
      width: 120,
      render: (v: string | null) => subTypeLabel(v),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (v: string) => accountStatusTag(v),
    },
    {
      title: "状态消息",
      dataIndex: "status_message",
      key: "status_message",
      ellipsis: true,
      render: (v: string | null) => v || "-",
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: unknown, record: PlatformAccount) => (
        <Button
          type="link"
          size="small"
          icon={<ReloadOutlined />}
          loading={refreshingId === record.id}
          onClick={() => void handleRefreshAccount(record.id)}
        >
          刷新
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <PageHeader
        eyebrow="系统设置"
        title="设置中心"
        description="管理平台账号、Cookie 状态、MediaCrawler 服务和系统信息。"
        action={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void Promise.all([loadAccounts(), loadMcHealth(), loadScheduler(), loadCookieStatus()])}
          >
            全部刷新
          </Button>
        }
      />

      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <SafetyCertificateOutlined />
                <span>账号与 Cookie</span>
              </Space>
            }
            extra={
              <Space>
                <Badge count={expiredCount} offset={[6, 0]} size="small">
                  <Tag color={expiredCount > 0 ? "error" : "success"}>
                    {healthyCount} 健康 / {expiredCount} 过期
                  </Tag>
                </Badge>
              </Space>
            }
            styles={{ body: { padding: 0 } }}
          >
            {accountsError && (
              <div style={{ padding: 16 }}>
                <Alert type="error" message={accountsError} showIcon />
              </div>
            )}
            <Table
              dataSource={accounts}
              columns={accountColumns}
              rowKey="id"
              loading={accountsLoading}
              pagination={false}
              size="small"
              locale={{ emptyText: "暂无账号，请在「账号矩阵」中添加" }}
            />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <SafetyCertificateOutlined />
                <span>Cookie 采集就绪状态</span>
              </Space>
            }
            extra={
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={cookieLoading}
                onClick={() => void loadCookieStatus()}
              >
                刷新
              </Button>
            }
          >
            {cookieLoading && cookieStatus.length === 0 ? (
              <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
            ) : cookieStatus.length === 0 ? (
              <Alert type="info" message="暂无平台账号，请先在「账号矩阵」中添加账号" showIcon />
            ) : (
              <Table
                dataSource={cookieStatus}
                rowKey="platform"
                pagination={false}
                size="small"
                columns={[
                  {
                    title: "平台",
                    dataIndex: "platform",
                    key: "platform",
                    render: (v: string) => v.toUpperCase(),
                  },
                  {
                    title: "活跃账号",
                    dataIndex: "active_accounts",
                    key: "active_accounts",
                    width: 90,
                    render: (v: number) => <Tag color={v > 0 ? "success" : "default"}>{v}</Tag>,
                  },
                  {
                    title: "过期账号",
                    dataIndex: "expired_accounts",
                    key: "expired_accounts",
                    width: 90,
                    render: (v: number) => <Tag color={v > 0 ? "error" : "default"}>{v}</Tag>,
                  },
                  {
                    title: "Cookie 可用",
                    dataIndex: "cookies_available",
                    key: "cookies_available",
                    width: 100,
                    render: (v: boolean) => v
                      ? <Tag color="success"><CheckCircleOutlined /> 可用</Tag>
                      : <Tag color="error"><ExclamationCircleOutlined /> 不可用</Tag>,
                  },
                  {
                    title: "采集就绪",
                    dataIndex: "crawl_ready",
                    key: "crawl_ready",
                    width: 100,
                    render: (v: boolean) => v
                      ? <Tag color="success">就绪</Tag>
                      : <Tag color="warning">未就绪</Tag>,
                  },
                ]}
              />
            )}
          </Card>

          <Card
            title={
              <Space>
                <CloudServerOutlined />
                <span>MediaCrawler 服务</span>
              </Space>
            }
            extra={
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={mcLoading}
                onClick={() => void loadMcHealth()}
              >
                刷新
              </Button>
            }
          >
            {mcError && <Alert type="error" message={mcError} showIcon style={{ marginBottom: 12 }} />}
            {mcLoading && !mcHealth ? (
              <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
            ) : mcHealth ? (
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="状态">
                  <Tag color={mcHealth.status === "healthy" || mcHealth.status === "ok" ? "success" : "warning"}>
                    {mcHealth.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="模式">{mcHealth.mode || "-"}</Descriptions.Item>
                <Descriptions.Item label="API 地址">{mcHealth.api_base_url || "-"}</Descriptions.Item>
                <Descriptions.Item label="共享数据库">
                  {mcHealth.shared_db?.available ? (
                    <Tag color="success">可用</Tag>
                  ) : (
                    <Tag color="default">不可用</Tag>
                  )}
                  {mcHealth.shared_db?.path && (
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>{mcHealth.shared_db.path}</Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="支持平台">
                  <Space size={[4, 4]} wrap>
                    {(mcHealth.supported_platforms || []).map((p) => (
                      <Tag key={p.value}>{p.label}</Tag>
                    ))}
                  </Space>
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Alert type="warning" message="无法获取 MediaCrawler 状态" showIcon />
            )}
          </Card>

          <Card
            title={
              <Space>
                <SettingOutlined />
                <span>定时调度</span>
              </Space>
            }
            style={{ marginTop: 16 }}
          >
            {schedulerLoading ? (
              <div style={{ textAlign: "center", padding: 16 }}><Spin /></div>
            ) : scheduler ? (
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="运行状态">
                  <Tag color={scheduler.running ? "success" : "default"}>
                    {scheduler.running ? "运行中" : "已停止"}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="调度任务数">{scheduler.jobs?.length ?? 0}</Descriptions.Item>
                {scheduler.jobs && scheduler.jobs.length > 0 && (
                  <Descriptions.Item label="任务列表">
                    <Space direction="vertical" size={4}>
                      {scheduler.jobs.map((job) => (
                        <Text key={job.id} style={{ fontSize: 12 }}>
                          {job.name}
                          {job.next_run_time && (
                            <Text type="secondary"> (下次: {new Date(job.next_run_time).toLocaleString("zh-CN")})</Text>
                          )}
                        </Text>
                      ))}
                    </Space>
                  </Descriptions.Item>
                )}
              </Descriptions>
            ) : (
              <Alert type="warning" message="无法获取调度器状态" showIcon />
            )}
          </Card>
        </Col>
      </Row>

      <Card title="项目声明">
        <Paragraph type="secondary">
          智获客雷达 — 助贷线索从发现到成交，一屏推进。
        </Paragraph>
        <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
          本工具仅供合法合规的市场调研与数据分析使用，请遵守相关平台的服务条款与数据使用规范。
          采集的数据仅用于内部业务分析，不得用于任何违法违规用途。
        </Paragraph>
      </Card>
    </div>
  );
}
