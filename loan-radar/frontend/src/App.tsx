import { Link } from "react-router-dom";

import AppRoutes from "./routes";

export default function App() {
  return (
    <div>
      <header style={{ padding: "12px 16px", borderBottom: "1px solid #e5e7eb" }}>
        <nav style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/">Dashboard</Link>
          <Link to="/monitor-sources">MonitorSources</Link>
          <Link to="/crawl-tasks">CrawlTasks</Link>
          <Link to="/posts">Posts</Link>
          <Link to="/comments">Comments</Link>
          <Link to="/leads">Leads</Link>
          <Link to="/daily-reports">DailyReports</Link>
        </nav>
      </header>
      <AppRoutes />
    </div>
  );
}
