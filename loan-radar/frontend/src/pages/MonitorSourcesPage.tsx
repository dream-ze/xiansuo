import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  createMonitorSource,
  deleteMonitorSource,
  getMonitorSources,
  toggleMonitorSource,
  crawlMonitorSource,
  type CrawlTask,
  type MonitorSource,
  type MonitorSourceCreatePayload,
} from "../api/client";

const PLATFORM_OPTIONS = [
  { label: "小红书", value: "xhs" },
  { label: "抖音", value: "douyin" },
  { label: "知乎", value: "zhihu" },
  { label: "其他", value: "other" },
];

const SOURCE_TYPE_OPTIONS = [
  { label: "关键词", value: "keyword" },
  { label: "同行账号", value: "competitor_account" },
  { label: "指定帖子链接", value: "manual_post" },
  { label: "爆款规则", value: "hot_post_rule" },
];

const COLLECTOR_TYPE_OPTIONS = [
  { label: "Mock", value: "mock" },
  { label: "Playwright", value: "playwright" },
];

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

type CreateFormState = {
  source_type: string;
  platform: string;
  name: string;
  value: string;
  collector_type: string;
  max_posts: string;
  max_comments_per_post: string;
  enabled: boolean;
};

const DEFAULT_CREATE_FORM: CreateFormState = {
  source_type: "keyword",
  platform: "xhs",
  name: "关键词 - 征信花了",
  value: "征信花了",
  collector_type: "mock",
  max_posts: "10",
  max_comments_per_post: "10",
  enabled: true,
};

function createPayloadFromForm(form: CreateFormState): MonitorSourceCreatePayload {
  const maxPosts = Number(form.max_posts);
  const maxCommentsPerPost = Number(form.max_comments_per_post);
  const collectorType = form.source_type === "manual_post" ? form.collector_type : "mock";
  const config: Record<string, unknown> = {
    collector_type: collectorType,
  };

  if (form.source_type !== "manual_post" && Number.isFinite(maxPosts) && maxPosts > 0) {
    config.max_posts = maxPosts;
  }
  if (Number.isFinite(maxCommentsPerPost) && maxCommentsPerPost > 0) {
    config.max_comments_per_post = maxCommentsPerPost;
  }

  return {
    source_type: form.source_type,
    platform: form.platform,
    name: form.name.trim(),
    value: form.value.trim(),
    config,
    enabled: form.enabled,
    last_crawled_at: null,
  };
}

export default function MonitorSourcesPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<MonitorSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<CreateFormState>(DEFAULT_CREATE_FORM);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function loadSources() {
    setLoading(true);
    setError(null);

    try {
      const sources = await getMonitorSources();
      setItems(sources);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载监控源失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSources();
  }, [refreshTick]);

  const hasItems = useMemo(() => items.length > 0, [items]);
  const isManualPost = createForm.source_type === "manual_post";

  function updateSourceType(sourceType: string) {
    setCreateForm((current) => ({
      ...current,
      source_type: sourceType,
      collector_type: sourceType === "manual_post" ? "playwright" : "mock",
      name: sourceType === "manual_post" ? "真实帖子链接" : current.name,
      value: sourceType === "manual_post" ? "" : current.value,
      max_posts: sourceType === "manual_post" ? "1" : current.max_posts,
    }));
  }

  async function refreshList() {
    setRefreshTick((current) => current + 1);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateLoading(true);
    setCreateError(null);
    setActionMessage(null);

    try {
      const payload = createPayloadFromForm(createForm);
      if (!payload.name || !payload.value) {
        throw new Error("名称和内容/链接不能为空");
      }
      if (payload.source_type === "manual_post" && payload.config && typeof payload.config === "object") {
        const config = payload.config as Record<string, unknown>;
        if (config.collector_type === "playwright" && !/^https?:\/\//.test(payload.value)) {
          throw new Error("真实采集只支持 http/https 公开帖子链接");
        }
      }
      const created = await createMonitorSource(payload);
      await refreshList();
      setActionMessage(`新增成功：${created.name}`);
      setCreateForm((current) => ({
        ...current,
        name: current.source_type === "keyword" ? "关键词 - 征信花了" : "",
        value: current.source_type === "keyword" ? "征信花了" : "",
      }));
    } catch (submitError) {
      setCreateError(submitError instanceof Error ? submitError.message : "创建失败");
    } finally {
      setCreateLoading(false);
    }
  }

  async function handleToggle(item: MonitorSource) {
    setBusyKey(`toggle-${item.id}`);
    setActionError(null);
    setActionMessage(null);

    try {
      await toggleMonitorSource(item.id, !item.enabled);
      await refreshList();
      setActionMessage(`${item.name} 已${item.enabled ? "停用" : "启用"}`);
    } catch (toggleError) {
      setActionError(toggleError instanceof Error ? toggleError.message : "启用/停用失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDelete(item: MonitorSource) {
    setBusyKey(`delete-${item.id}`);
    setActionError(null);
    setActionMessage(null);

    try {
      await deleteMonitorSource(item.id);
      await refreshList();
      setActionMessage(`${item.name} 已删除`);
    } catch (deleteError) {
      setActionError(deleteError instanceof Error ? deleteError.message : "删除失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleCrawl(item: MonitorSource) {
    setBusyKey(`crawl-${item.id}`);
    setActionError(null);
    setActionMessage(null);

    try {
      const task = (await crawlMonitorSource(item.id)) as CrawlTask;
      await refreshList();
      if (task.status === "success") {
        navigate("/crawl-tasks");
      } else {
        setActionError(task.error_message || `立即采集失败：任务 #${task.id}`);
      }
    } catch (crawlError) {
      setActionError(crawlError instanceof Error ? crawlError.message : "触发采集失败");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">监控源管理</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看、创建和管理监控源，支持关键词、同行账号、指定帖子链接和爆款规则。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header">
          <h2>新增监控源</h2>
          <p>支持新增关键词、同行账号、指定帖子链接、爆款规则。</p>
        </div>
        <form className="form-grid" onSubmit={handleCreate}>
          <label>
            <span>source_type</span>
            <select
              value={createForm.source_type}
              onChange={(event) => updateSourceType(event.target.value)}
            >
              {SOURCE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>platform</span>
            <select
              value={createForm.platform}
              onChange={(event) => setCreateForm((current) => ({ ...current, platform: event.target.value }))}
            >
              {PLATFORM_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>name</span>
            <input
              value={createForm.name}
              onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="例如：关键词 - 征信花了"
            />
          </label>
          <label>
            <span>value</span>
            <input
              value={createForm.value}
              onChange={(event) => setCreateForm((current) => ({ ...current, value: event.target.value }))}
              placeholder={isManualPost ? "公开帖子链接，例如：https://..." : "关键词/账号链接/规则内容"}
            />
          </label>
          <label>
            <span>collector_type</span>
            <select
              value={createForm.collector_type}
              onChange={(event) => setCreateForm((current) => ({ ...current, collector_type: event.target.value }))}
            >
              {COLLECTOR_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value} disabled={option.value === "playwright" && !isManualPost}>
                  {option.label}
                </option>
              ))}
            </select>
            <small className="field-hint">
              {isManualPost ? "Playwright 只采集公开可访问单帖；不支持登录、验证码或批量搜索。" : "关键词、同行账号和爆款规则当前使用 Mock 采集。"}
            </small>
          </label>
          <label className={isManualPost ? "field-muted" : ""}>
            <span>max_posts</span>
            <input
              type="number"
              min={1}
              disabled={isManualPost}
              value={createForm.max_posts}
              onChange={(event) => setCreateForm((current) => ({ ...current, max_posts: event.target.value }))}
              placeholder={isManualPost ? "指定帖子固定为 1" : "例如：10"}
            />
          </label>
          <label>
            <span>max_comments_per_post</span>
            <input
              type="number"
              min={1}
              value={createForm.max_comments_per_post}
              onChange={(event) => setCreateForm((current) => ({ ...current, max_comments_per_post: event.target.value }))}
              placeholder="例如：10"
            />
          </label>
          <label>
            <span>enabled</span>
            <select
              value={createForm.enabled ? "true" : "false"}
              onChange={(event) => setCreateForm((current) => ({ ...current, enabled: event.target.value === "true" }))}
            >
              <option value="true">启用</option>
              <option value="false">停用</option>
            </select>
          </label>
          <div className="form-actions form-grid-span-2">
            <button type="submit" disabled={createLoading}>
              {createLoading ? "提交中..." : "新增"}
            </button>
          </div>
        </form>
        {isManualPost ? (
          <div className="state-panel state-empty" style={{ marginTop: 14 }}>
            <p>真实采集 MVP 只处理公开帖子链接。若页面需要登录、结构变化或加载超时，任务会失败并在采集任务中心展示原因。</p>
          </div>
        ) : null}
        {createError ? <p className="inline-error">{createError}</p> : null}
      </section>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>监控源列表</h2>
            <p>支持启用、停用、删除和手动触发采集。</p>
          </div>
          <button type="button" onClick={refreshList} disabled={loading}>
            刷新列表
          </button>
        </div>

        {loading ? <p className="state-text">加载中...</p> : null}
        {error ? (
          <div className="state-panel state-error">
            <p>{error}</p>
            <button type="button" onClick={refreshList}>
              重试
            </button>
          </div>
        ) : null}
        {actionMessage ? (
          <div className="state-panel state-empty">
            <p>{actionMessage}</p>
          </div>
        ) : null}
        {actionError ? <p className="inline-error">{actionError}</p> : null}

        {!loading && !error && !hasItems ? (
          <div className="state-panel state-empty">
            <p>暂无监控源，请先新增关键词或同行账号。</p>
          </div>
        ) : null}

        {!loading && !error && hasItems ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>来源类型</th>
                  <th>平台</th>
                  <th>名称</th>
                  <th>内容/链接</th>
                  <th>采集器</th>
                  <th>状态</th>
                  <th>最后采集时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const toggleLoading = busyKey === `toggle-${item.id}`;
                  const deleteLoading = busyKey === `delete-${item.id}`;
                  const crawlLoading = busyKey === `crawl-${item.id}`;

                  return (
                    <tr key={item.id}>
                      <td>{item.source_type}</td>
                      <td>{item.platform}</td>
                      <td>{item.name}</td>
                      <td className="cell-break">{item.value}</td>
                      <td>{typeof item.config === "object" && item.config && "collector_type" in item.config ? String((item.config as Record<string, unknown>).collector_type) : "mock"}</td>
                      <td>{item.enabled ? "启用" : "停用"}</td>
                      <td>{formatDateTime(item.last_crawled_at)}</td>
                      <td>
                        <div className="action-row">
                          <button type="button" onClick={() => void handleToggle(item)} disabled={toggleLoading || deleteLoading || crawlLoading}>
                            {item.enabled ? "停用" : "启用"}
                          </button>
                          <button type="button" onClick={() => void handleCrawl(item)} disabled={toggleLoading || deleteLoading || crawlLoading}>
                            {crawlLoading ? "采集中..." : "立即采集"}
                          </button>
                          <button type="button" className="danger" onClick={() => void handleDelete(item)} disabled={toggleLoading || deleteLoading || crawlLoading}>
                            {deleteLoading ? "删除中..." : "删除"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
