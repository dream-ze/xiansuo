import {
  BellOutlined,
  CloudDownloadOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  KeyOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RadarChartOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  ScheduleOutlined,
  SearchOutlined,
  SendOutlined,
  SettingOutlined,
  StarOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
  AimOutlined,
  BarChartOutlined,
  UserSwitchOutlined,
  ReadOutlined,
} from "@ant-design/icons";
import {
  Avatar,
  Badge,
  Breadcrumb,
  Button,
  Col,
  Dropdown,
  Input,
  Layout,
  List,
  Menu,
  Row,
  Space,
  Tag,
  Typography,
} from "antd";
import type { MenuProps } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, Outlet } from "react-router-dom";

import { markAllNotificationsRead, markNotificationRead, fetchNotifications, fetchUnreadNotificationCount } from "../api/xhs-api";
import type { AppNotification } from "../api/xhs-types";

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < breakpoint);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpoint]);
  return isMobile;
}

const radarNavItems: MenuProps["items"] = [
  { key: "/", icon: <DashboardOutlined />, label: "工作台" },
  { key: "/collection", icon: <SearchOutlined />, label: "采集中心" },
  { key: "/posts", icon: <ReadOutlined />, label: "帖子池" },
  { key: "/leads", icon: <StarOutlined />, label: "线索池" },
  { key: "/crm", icon: <TeamOutlined />, label: "CRM 跟进" },
  { key: "/pending-competitors", icon: <UserSwitchOutlined />, label: "同行发现" },
  { key: "/daily-reports", icon: <BarChartOutlined />, label: "获客报告" },
];

const xhsNavItems: MenuProps["items"] = [
  { key: "/xhs/dashboard", icon: <DashboardOutlined />, label: "运营总览" },
  { key: "/xhs/accounts", icon: <SafetyCertificateOutlined />, label: "账号矩阵" },
  { key: "/xhs/discovery", icon: <AimOutlined />, label: "笔记发现" },
  { key: "/xhs/crawler", icon: <CloudDownloadOutlined />, label: "数据抓取" },
  { key: "/xhs/keywords", icon: <KeyOutlined />, label: "关键词组" },
  { key: "/xhs/analytics", icon: <BarChartOutlined />, label: "数据洞察" },
  { key: "/xhs/image-studio", icon: <StarOutlined />, label: "图片工坊" },
  { key: "/xhs/video-studio", icon: <VideoCameraOutlined />, label: "视频工坊" },
  { key: "/xhs/library", icon: <DatabaseOutlined />, label: "内容库" },
  { key: "/xhs/drafts", icon: <FileTextOutlined />, label: "草稿工坊" },
  { key: "/xhs/publish", icon: <SendOutlined />, label: "发布中心" },
  { key: "/xhs/auto-ops", icon: <ThunderboltOutlined />, label: "自动运营" },
];

const footerNavItems: MenuProps["items"] = [
  { key: "/tasks", icon: <ScheduleOutlined />, label: "任务中心" },
  { key: "/models", icon: <RobotOutlined />, label: "模型配置" },
  { key: "/settings", icon: <SettingOutlined />, label: "系统设置" },
];

const BREADCRUMB_MAP: Record<string, string> = {
  "/": "工作台",
  "/collection": "采集中心",
  "/posts": "帖子池",
  "/leads": "线索池",
  "/crm": "CRM 跟进",
  "/pending-competitors": "同行发现",
  "/daily-reports": "获客报告",
  "/tasks": "任务中心",
  "/models": "模型配置",
  "/settings": "系统设置",
  "/xhs/dashboard": "运营总览",
  "/xhs/accounts": "账号矩阵",
  "/xhs/discovery": "笔记发现",
  "/xhs/crawler": "数据抓取",
  "/xhs/keywords": "关键词组",
  "/xhs/analytics": "数据洞察",
  "/xhs/image-studio": "图片工坊",
  "/xhs/video-studio": "视频工坊",
  "/xhs/library": "内容库",
  "/xhs/drafts": "草稿工坊",
  "/xhs/publish": "发布中心",
  "/xhs/auto-ops": "自动运营",
};

function levelColor(level: string): string {
  if (level === "error") return "#ff4560";
  if (level === "warning") return "#ffb020";
  if (level === "success") return "#00e396";
  return "rgba(255,255,255,0.35)";
}

function sourceTypeLabel(sourceType: string): string {
  const labels: Record<string, string> = {
    crawl_task: "采集",
    lead: "线索",
    task: "任务",
    account: "账号",
    account_expired: "Cookie",
    publish_job: "发布",
  };
  return labels[sourceType] || sourceType;
}

function getSelectedKey(pathname: string): string {
  if (pathname === "/collection" || pathname === "/monitor-sources" || pathname === "/crawl-tasks") return "/collection";
  if (pathname.startsWith("/crm")) return "/crm";
  if (pathname === "/comments" || pathname === "/scoring-rules") return "/leads";
  if (pathname.startsWith("/xhs")) return pathname;
  return pathname;
}

function isXhsPath(pathname: string): boolean {
  return pathname.startsWith("/xhs");
}

export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const isMobile = useIsMobile();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
  }, []);

  useEffect(() => {
    if (isMobile) {
      setCollapsed(true);
      setMobileOpen(false);
    }
  }, [isMobile]);

  useEffect(() => {
    if (isMobile) setMobileOpen(false);
  }, [location.pathname, isMobile]);

  const loadNotifications = useCallback(async () => {
    try {
      const [res, unreadRes] = await Promise.all([
        fetchNotifications({ page_size: 20 }),
        fetchUnreadNotificationCount(),
      ]);
      setNotifications(res.items);
      setUnreadCount(unreadRes.count);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    void loadNotifications();
    const timer = setInterval(() => void loadNotifications(), 30_000);
    return () => clearInterval(timer);
  }, [loadNotifications]);

  const handleMarkRead = async (id: number) => { await markNotificationRead(id); void loadNotifications(); };
  const handleMarkAllRead = async () => { await markAllNotificationsRead(); void loadNotifications(); };
  const handleMenuClick: MenuProps["onClick"] = ({ key }) => { navigate(key); };
  const selectedKeys = [getSelectedKey(location.pathname)];

  const breadcrumbItems = useMemo(() => {
    const items = [{ title: <span style={{ cursor: "pointer", color: "rgba(0,212,255,0.85)" }} onClick={() => navigate("/")}>智获客雷达</span> }];
    const xhs = isXhsPath(location.pathname);
    if (xhs) {
      items.push({ title: <span style={{ cursor: "pointer", color: "rgba(0,212,255,0.7)" }} onClick={() => navigate("/xhs/dashboard")}>小红书运营</span> });
    }
    const label = BREADCRUMB_MAP[location.pathname];
    if (label) {
      items.push({ title: <span style={{ color: "rgba(255,255,255,0.85)" }}>{label}</span> });
    }
    return items;
  }, [location.pathname, navigate]);

  const notificationDropdownContent = (
    <div style={{ width: isMobile ? "calc(100vw - 24px)" : 380, maxWidth: 380, background: "#111827", borderRadius: 8, overflow: "hidden", boxShadow: "0 0 20px rgba(0,212,255,0.15), 0 4px 16px rgba(0,0,0,0.5)", border: "1px solid rgba(0,212,255,0.15)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid rgba(0,212,255,0.1)" }}>
        <Text strong style={{ fontSize: 14, color: "rgba(255,255,255,0.88)" }}>通知中心</Text>
        {unreadCount > 0 && <Button type="link" size="small" onClick={() => void handleMarkAllRead()}>全部已读</Button>}
      </div>
      <div style={{ maxHeight: 400, overflowY: "auto" }}>
        {notifications.length === 0 ? (
          <div style={{ padding: "40px 16px", textAlign: "center", color: "rgba(255,255,255,0.25)" }}>
            <BellOutlined style={{ fontSize: 32, marginBottom: 8, display: "block" }} />
            暂无通知
          </div>
        ) : (
          <List
            dataSource={notifications}
            renderItem={(n) => (
              <List.Item key={n.id} style={{ padding: "10px 16px", cursor: n.read ? "default" : "pointer", background: n.read ? "transparent" : "rgba(0,212,255,0.06)", borderBottom: "1px solid rgba(0,212,255,0.06)" }} onClick={() => !n.read && void handleMarkRead(n.id)}>
                <List.Item.Meta
                  avatar={<span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: levelColor(n.level), marginTop: 6, boxShadow: `0 0 6px ${levelColor(n.level)}` }} />}
                  title={<Space size={4}><Text style={{ fontSize: 13, color: "rgba(255,255,255,0.85)" }}>{n.title}</Text>{n.source_type && <Tag style={{ fontSize: 10, lineHeight: "16px", padding: "0 4px", margin: 0, background: "rgba(0,212,255,0.1)", border: "1px solid rgba(0,212,255,0.2)", color: "#00d4ff" }}>{sourceTypeLabel(n.source_type)}</Tag>}</Space>}
                  description={<div>{n.body && <Text type="secondary" style={{ fontSize: 12, display: "block" }}>{n.body}</Text>}<Text type="secondary" style={{ fontSize: 11 }}>{new Date(n.created_at).toLocaleString("zh-CN")}</Text></div>}
                />
              </List.Item>
            )}
          />
        )}
      </div>
    </div>
  );

  const siderWidth = isMobile ? 0 : (collapsed ? 64 : 220);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {isMobile && mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
            zIndex: 99, transition: "opacity 0.2s",
          }}
        />
      )}
      <Sider
        collapsed={isMobile ? false : collapsed}
        width={220}
        collapsedWidth={64}
        theme="dark"
        trigger={null}
        style={{
          height: "100vh",
          position: "fixed",
          left: isMobile ? (mobileOpen ? 0 : -220) : 0,
          top: 0,
          bottom: 0,
          overflow: "hidden",
          zIndex: 100,
          transition: "left 0.2s",
          background: "linear-gradient(180deg, #060a14 0%, #0a1020 100%)",
          borderRight: "1px solid rgba(0,212,255,0.08)",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          <div
            style={{
              padding: collapsed ? "16px 0" : "16px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: collapsed ? "center" : "space-between",
              borderBottom: "1px solid rgba(0,212,255,0.1)",
              flexShrink: 0,
              cursor: "pointer",
              height: 56,
            }}
            onClick={() => navigate("/")}
          >
            <Space align="center" size={collapsed ? 0 : 10}>
              <RadarChartOutlined style={{ fontSize: 22, color: "#00d4ff", flexShrink: 0, filter: "drop-shadow(0 0 6px rgba(0,212,255,0.5))" }} />
              {!collapsed && <span style={{ fontWeight: 700, fontSize: 15, color: "#fff", letterSpacing: 0.5, textShadow: "0 0 12px rgba(0,212,255,0.3)" }}>智获客雷达</span>}
            </Space>
            {!collapsed && !isMobile && (
              <Button
                type="text"
                size="small"
                icon={<MenuFoldOutlined />}
                onClick={(e) => { e.stopPropagation(); setCollapsed(true); }}
                style={{ color: "rgba(0,212,255,0.45)" }}
              />
            )}
          </div>
          {collapsed && !isMobile && (
            <div style={{ textAlign: "center", padding: "4px 0", borderBottom: "1px solid rgba(0,212,255,0.1)", flexShrink: 0 }}>
              <Button type="text" size="small" icon={<MenuUnfoldOutlined />} onClick={() => setCollapsed(false)} style={{ color: "rgba(0,212,255,0.45)" }} />
            </div>
          )}

          <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden", paddingTop: 4 }}>
            {!collapsed && (
              <div style={{ padding: "8px 20px 4px", fontSize: 11, color: "rgba(0,212,255,0.5)", letterSpacing: 2, fontWeight: 600, textTransform: "uppercase" }}>
                ◆ 线索雷达
              </div>
            )}
            <Menu theme="dark" mode="inline" selectedKeys={selectedKeys} onClick={handleMenuClick} items={radarNavItems} style={{ borderRight: 0 }} />
            {!collapsed && (
              <div style={{ padding: "16px 20px 4px", fontSize: 11, color: "rgba(0,212,255,0.5)", borderTop: "1px solid rgba(0,212,255,0.06)", marginTop: 4, letterSpacing: 2, fontWeight: 600, textTransform: "uppercase" }}>
                ◆ 小红书运营
              </div>
            )}
            {collapsed && <div style={{ borderTop: "1px solid rgba(0,212,255,0.06)", margin: "4px 16px" }} />}
            <Menu theme="dark" mode="inline" selectedKeys={selectedKeys} onClick={handleMenuClick} items={xhsNavItems} style={{ borderRight: 0 }} />
          </div>

          <div style={{ flexShrink: 0, borderTop: "1px solid rgba(0,212,255,0.1)" }}>
            <Menu theme="dark" mode="inline" selectedKeys={selectedKeys} onClick={handleMenuClick} items={footerNavItems} style={{ borderRight: 0 }} />
          </div>
        </div>
      </Sider>

      <Layout style={{ marginLeft: siderWidth, transition: "margin-left 0.2s" }}>
        <Header style={{
          padding: isMobile ? "0 12px" : "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid rgba(0,212,255,0.1)",
          height: 56,
          lineHeight: "56px",
          background: "rgba(10,14,26,0.85)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          gap: 8,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0, flex: 1 }}>
            {isMobile && (
              <Button type="text" icon={mobileOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />} onClick={() => setMobileOpen(!mobileOpen)} style={{ flexShrink: 0 }} />
            )}
            <div style={{ minWidth: 0, overflow: "hidden" }}>
              <Breadcrumb items={breadcrumbItems} />
            </div>
          </div>
          <Space size={isMobile ? 8 : 16} align="center" style={{ flexShrink: 0 }}>
            <Dropdown popupRender={() => notificationDropdownContent} trigger={["click"]} placement="bottomRight">
              <Badge count={unreadCount} size="small" offset={[-2, 2]}>
                <Button type="text" icon={<BellOutlined style={{ fontSize: 16, color: "rgba(0,212,255,0.7)" }} />} style={{ display: "flex", alignItems: "center", justifyContent: "center" }} />
              </Badge>
            </Dropdown>
            <Dropdown
              menu={{
                onClick: ({ key }) => {
                  if (key === "logout") {
                    localStorage.removeItem("access_token");
                    localStorage.removeItem("refresh_token");
                    window.location.href = "/login";
                  }
                },
                items: [
                  { key: "logout", label: "退出登录" },
                ],
              }}
              trigger={["click"]}
              placement="bottomRight"
            >
              <Avatar size={30} style={{ background: "linear-gradient(135deg, #00d4ff 0%, #0066ff 100%)", cursor: "pointer", fontSize: 14, boxShadow: "0 0 8px rgba(0,212,255,0.3)" }}>A</Avatar>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ background: "radial-gradient(ellipse at 50% 0%, rgba(0,212,255,0.04) 0%, transparent 60%), #0a0e1a", padding: isMobile ? "12px" : "20px 24px", minHeight: "calc(100vh - 56px)", overflow: "auto" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return (
    <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
      <Col xs={24} sm={undefined} flex={action ? "1" : undefined}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div>
            <Text style={{ fontSize: 12, color: "rgba(0,212,255,0.6)", letterSpacing: "0.1em", textTransform: "uppercase" }}>{eyebrow}</Text>
            <div style={{ fontSize: 18, fontWeight: 600, color: "rgba(255,255,255,0.88)", marginTop: 2, textShadow: "0 0 12px rgba(0,212,255,0.15)" }}>{title}</div>
          </div>
        </div>
        {description && <Text style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", marginTop: 2, display: "block" }}>{description}</Text>}
      </Col>
      {action && <Col xs={24} sm="auto" style={{ marginTop: 8 }}>{action}</Col>}
    </Row>
  );
}
