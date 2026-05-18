import { Link, useLocation } from "react-router-dom";

import ToastContainer from "./components/ToastContainer";
import AppRoutes from "./routes";

const NAV_ITEMS = [
  { to: "/", label: "仪表盘" },
  { to: "/monitor-sources", label: "监听源" },
  { to: "/crawl-tasks", label: "采集任务" },
  { to: "/posts", label: "帖子" },
  { to: "/comments", label: "评论" },
  { to: "/leads", label: "线索" },
  { to: "/crm", label: "CRM" },
  { to: "/crm/tasks", label: "CRM任务" },
  { to: "/pending-competitors", label: "同行发现" },
  { to: "/daily-reports", label: "日报" },
  { to: "/scoring-rules", label: "评分规则" },
];

export default function App() {
  const location = useLocation();

  return (
    <div>
      <header className="app-header">
        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={location.pathname === item.to ? "nav-link active" : "nav-link"}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      <AppRoutes />
      <ToastContainer />
    </div>
  );
}
