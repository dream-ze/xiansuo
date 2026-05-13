import { Navigate, Route, Routes } from "react-router-dom";

import DashboardPage from "../pages/DashboardPage";
import CrawlTasksPage from "../pages/CrawlTasksPage";
import RealCollectionTasksPage from "../pages/RealCollectionTasksPage";
import DailyReportsPage from "../pages/DailyReportsPage";
import LeadsPage from "../pages/LeadsPage";
import MonitorSourcesPage from "../pages/MonitorSourcesPage";
import PostsPage from "../pages/PostsPage";
import CommentsPage from "../pages/CommentsPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/monitor-sources" element={<MonitorSourcesPage />} />
      <Route path="/crawl-tasks" element={<CrawlTasksPage />} />
      <Route path="/collection-tasks" element={<RealCollectionTasksPage />} />
      <Route path="/posts" element={<PostsPage />} />
      <Route path="/comments" element={<CommentsPage />} />
      <Route path="/leads" element={<LeadsPage />} />
      <Route path="/daily-reports" element={<DailyReportsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
