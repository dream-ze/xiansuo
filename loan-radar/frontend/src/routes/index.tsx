import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "../components/AppShell";
import DashboardPage from "../pages/DashboardPage";
import CollectionPage from "../pages/CollectionPage";
import CrmFollowUpPage from "../pages/CrmFollowUpPage";
import DailyReportsPage from "../pages/DailyReportsPage";
import LeadsPage from "../pages/LeadsPage/index";
import PendingCompetitorsPage from "../pages/PendingCompetitorsPage";
import PostPoolPage from "../pages/PostPoolPage";
import CommentsPage from "../pages/CommentsPage";
import ScoringRulesPage from "../pages/ScoringRulesPage";
import { TaskCenterPage } from "../pages/TaskCenterPage";
import { ModelConfigPage } from "../pages/ModelConfigPage";
import { SettingsPage } from "../pages/SettingsPage";
import LoginPage from "../pages/LoginPage";

import { XhsDashboard } from "../pages/xhs/xhs-dashboard";
import { XhsAccountsPage } from "../pages/xhs/accounts-page";
import { XhsDiscoveryPage } from "../pages/xhs/discovery-page";
import { XhsCrawlerPage } from "../pages/xhs/crawler-page";
import { XhsKeywordsPage } from "../pages/xhs/keywords-page";
import { XhsAnalyticsPage } from "../pages/xhs/analytics-page";
import { XhsImageStudioPage } from "../pages/xhs/image-studio-page";
import { XhsVideoStudioPage } from "../pages/xhs/video-studio-page";
import { XhsLibraryPage } from "../pages/xhs/library-page";
import { XhsDraftsPage } from "../pages/xhs/rewrite-page";
import { XhsPublishPage } from "../pages/xhs/publish-page";
import { AutoOpsPage } from "../pages/xhs/auto-ops-page";
import { XhsSectionPage } from "../pages/xhs/xhs-section-page";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        {/* 线索雷达 */}
        <Route path="/" element={<DashboardPage />} />
        <Route path="/collection" element={<CollectionPage />} />
        <Route path="/monitor-sources" element={<Navigate to="/collection" replace />} />
        <Route path="/crawl-tasks" element={<Navigate to="/collection" replace />} />
        <Route path="/leads" element={<LeadsPage />} />
        <Route path="/crm" element={<CrmFollowUpPage />} />
        <Route path="/pending-competitors" element={<PendingCompetitorsPage />} />
        <Route path="/daily-reports" element={<DailyReportsPage />} />
        <Route path="/posts" element={<PostPoolPage />} />
        <Route path="/comments" element={<CommentsPage />} />
        <Route path="/scoring-rules" element={<ScoringRulesPage />} />

        {/* 小红书运营 */}
        <Route path="/xhs/dashboard" element={<XhsDashboard />} />
        <Route path="/xhs/accounts" element={<XhsAccountsPage />} />
        <Route path="/xhs/discovery" element={<XhsDiscoveryPage />} />
        <Route path="/xhs/crawler" element={<XhsCrawlerPage />} />
        <Route path="/xhs/keywords" element={<XhsKeywordsPage />} />
        <Route path="/xhs/analytics" element={<XhsAnalyticsPage />} />
        <Route path="/xhs/image-studio" element={<XhsImageStudioPage />} />
        <Route path="/xhs/video-studio" element={<XhsVideoStudioPage />} />
        <Route path="/xhs/library" element={<XhsLibraryPage />} />
        <Route path="/xhs/drafts" element={<XhsDraftsPage />} />
        <Route path="/xhs/publish" element={<XhsPublishPage />} />
        <Route path="/xhs/auto-ops" element={<AutoOpsPage />} />
        <Route path="/xhs/:section" element={<XhsSectionPage />} />

        {/* 通用 */}
        <Route path="/tasks" element={<TaskCenterPage />} />
        <Route path="/models" element={<ModelConfigPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
