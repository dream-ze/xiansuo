import { Navigate, useParams } from "react-router-dom";

const SECTION_ROUTE_MAP: Record<string, string> = {
  accounts: "/xhs/accounts",
  discovery: "/xhs/discovery",
  library: "/xhs/library",
  analytics: "/xhs/analytics",
  "image-studio": "/xhs/image-studio",
  "video-studio": "/xhs/video-studio",
  publish: "/xhs/publish",
  drafts: "/xhs/drafts",
  crawler: "/xhs/crawler",
  keywords: "/xhs/keywords",
  dashboard: "/xhs/dashboard",
  "auto-ops": "/xhs/auto-ops",
};

export function XhsSectionPage() {
  const { section = "discovery" } = useParams();
  const target = SECTION_ROUTE_MAP[section];
  if (target) {
    return <Navigate to={target} replace />;
  }
  return <Navigate to="/xhs/dashboard" replace />;
}
