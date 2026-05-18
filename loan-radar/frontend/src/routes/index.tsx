import { Navigate, Route, Routes } from "react-router-dom";

import DashboardPage from "../pages/DashboardPage";
import CollectionPage from "../pages/CollectionPage";
import DailyReportsPage from "../pages/DailyReportsPage";
import LeadsPage from "../pages/LeadsPage";
import PendingCompetitorsPage from "../pages/PendingCompetitorsPage";
import PostsPage from "../pages/PostsPage";
import CommentsPage from "../pages/CommentsPage";
import CrmCustomersPage from "../pages/CrmCustomersPage";
import CrmDashboardPage from "../pages/CrmDashboardPage";
import CrmOpportunitiesPage from "../pages/CrmOpportunitiesPage";
import CrmTasksPage from "../pages/CrmTasksPage";
import CrmContractsPage from "../pages/CrmContractsPage";
import CrmReceivablesPage from "../pages/CrmReceivablesPage";
import ScoringRulesPage from "../pages/ScoringRulesPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/collection" element={<CollectionPage />} />
      <Route path="/monitor-sources" element={<Navigate to="/collection" replace />} />
      <Route path="/crawl-tasks" element={<Navigate to="/collection" replace />} />
      <Route path="/posts" element={<PostsPage />} />
      <Route path="/comments" element={<CommentsPage />} />
      <Route path="/leads" element={<LeadsPage />} />
      <Route path="/crm" element={<Navigate to="/crm/dashboard" replace />} />
      <Route path="/crm/dashboard" element={<CrmDashboardPage />} />
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
