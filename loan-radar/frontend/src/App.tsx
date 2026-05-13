import { Link } from "react-router-dom";

import AppRoutes from "./routes";

export default function App() {
  return (
    <div>
      <header style={{ padding: "12px 16px", borderBottom: "1px solid #e5e7eb" }}>
        <nav style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/">仪表板</Link>
          <Link to="/monitor-sources">监听源</Link>
          <Link to="/crawl-tasks">爬虫任务</Link>
          <Link to="/collection-tasks">真实采集任务</Link>
          <Link to="/posts">帖子</Link>
          <Link to="/comments">评论</Link>
          <Link to="/leads">线索</Link>
          <Link to="/daily-reports">日报</Link>
        </nav>
      </header>
      <AppRoutes />
    </div>
  );
}
