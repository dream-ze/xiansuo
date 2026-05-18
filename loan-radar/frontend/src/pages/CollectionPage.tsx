import { useState } from "react";

import CrawlTasksPage from "./CrawlTasksPage";
import MonitorSourcesPage from "./MonitorSourcesPage";

type TabKey = "sources" | "tasks";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "sources", label: "监听源" },
  { key: "tasks", label: "采集任务" },
];

export default function CollectionPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("sources");

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">采集管理</p>
          <h1>智获客雷达</h1>
          <p className="page-description">管理监听源和采集任务，一站式配置数据采集。</p>
        </div>
      </header>

      <div className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={activeTab === tab.key ? "tab-item active" : "tab-item"}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === "sources" && <MonitorSourcesPage embedded />}
        {activeTab === "tasks" && <CrawlTasksPage embedded />}
      </div>
    </main>
  );
}
