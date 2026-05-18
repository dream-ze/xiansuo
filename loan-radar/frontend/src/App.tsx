import { Link, useLocation } from "react-router-dom";

import ToastContainer from "./components/ToastContainer";
import AppRoutes from "./routes";

const NAV_ITEMS = [
  { to: "/", label: "驾驶舱" },
  { to: "/collection", label: "采集" },
  { to: "/posts", label: "帖子" },
  { to: "/comments", label: "评论" },
  { to: "/leads", label: "线索跟踪" },
  {
    label: "CRM",
    children: [
      { to: "/crm/dashboard", label: "CRM 总览" },
      { to: "/crm/customers", label: "客户管理" },
      { to: "/crm/opportunities", label: "销售漏斗" },
      { to: "/crm/tasks", label: "任务提醒" },
      { to: "/crm/contracts", label: "合同管理" },
      { to: "/crm/receivables", label: "回款管理" },
    ],
  },
  { to: "/pending-competitors", label: "同行发现" },
  { to: "/daily-reports", label: "日报" },
  { to: "/scoring-rules", label: "评分规则" },
];

function isItemActive(path: string, locationPath: string) {
  if (path === "/collection") {
    return ["/collection", "/monitor-sources", "/crawl-tasks"].includes(locationPath);
  }
  if (path === "/crm/dashboard" || path === "/crm") {
    return locationPath.startsWith("/crm");
  }
  return locationPath === path;
}

function NavItem({ item, locationPath }: { item: typeof NAV_ITEMS[number]; locationPath: string }) {
  if ("children" in item && item.children) {
    const isGroupActive = item.children.some((child) => isItemActive(child.to, locationPath));
    return (
      <span className={`nav-group${isGroupActive ? " active" : ""}`}>
        <span className="nav-link">{item.label} ▾</span>
        <span className="nav-dropdown">
          {item.children.map((child) => (
            <Link
              key={child.to}
              to={child.to}
              className={isItemActive(child.to, locationPath) ? "nav-dropdown-item active" : "nav-dropdown-item"}
            >
              {child.label}
            </Link>
          ))}
        </span>
      </span>
    );
  }

  const path = item.to!;
  return (
    <Link
      to={path}
      className={isItemActive(path, locationPath) ? "nav-link active" : "nav-link"}
    >
      {item.label}
    </Link>
  );
}

export default function App() {
  const location = useLocation();

  return (
    <div>
      <header className="app-header">
        <nav className="app-nav">
          <span className="nav-brand">智获客雷达</span>
          {NAV_ITEMS.map((item) => (
            <NavItem key={item.label} item={item} locationPath={location.pathname} />
          ))}
        </nav>
      </header>
      <AppRoutes />
      <ToastContainer />
    </div>
  );
}
