import { Navigate, Route, Routes } from "react-router-dom";

import DashboardPage from "../pages/DashboardPage";
import CrawlTasksPage from "../pages/CrawlTasksPage";
import DailyReportsPage from "../pages/DailyReportsPage";
import LeadsPage from "../pages/LeadsPage";
import MonitorSourcesPage from "../pages/MonitorSourcesPage";
import PendingCompetitorsPage from "../pages/PendingCompetitorsPage";
import PostsPage from "../pages/PostsPage";
import CommentsPage from "../pages/CommentsPage";
import CrmContractsPage from "../pages/CrmContractsPage";
import CrmCustomersPage from "../pages/CrmCustomersPage";
import CrmDashboardPage from "../pages/CrmDashboardPage";
import CrmOpportunitiesPage from "../pages/CrmOpportunitiesPage";
import CrmReceivablesPage from "../pages/CrmReceivablesPage";
import CrmTasksPage from "../pages/CrmTasksPage";
import ScoringRulesPage from "../pages/ScoringRulesPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/monitor-sources" element={<MonitorSourcesPage />} />
      <Route path="/crawl-tasks" element={<CrawlTasksPage />} />
      <Route path="/posts" element={<PostsPage />} />
      <Route path="/comments" element={<CommentsPage />} />
      <Route path="/leads" element={<LeadsPage />} />
      <Route path="/crm" element={<CrmDashboardPage />} />
      <Route path="/crm/customers" element={<CrmCustomersPage />} />
      <Route path="/crm/opportunities" element={<CrmOpportunitiesPage />} />
      <Route path="/crm/tasks" element={<CrmTasksPage />} />
      <Route path="/crm/contracts" element={<CrmContractsPage />} />
      <Route path="/crm/receivables" element={<CrmReceivablesPage />} />
      <Route path="/pending-competitors" element={<PendingCompetitorsPage />} />
      <Route path="/daily-reports" element={<DailyReportsPage />} />
      <Route path="/scoring-rules" element={<ScoringRulesPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
