import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createMonitorSource,
  deleteMonitorSource,
  getCollectorsCapabilities,
  getMonitorSources,
  toggleMonitorSource,
  crawlMonitorSource,
  updateMonitorSource,
  generateDemoData,
  type CollectorCapability,
  type CrawlTask,
  type MonitorSource,
  type MonitorSourceCreatePayload,
} from "../api/index";

const PLATFORM_OPTIONS = [
  { label: "小红书", value: "xhs" },
  { label: "抖音", value: "douyin" },
  { label: "知乎", value: "zhihu" },
];

const SOURCE_TYPE_OPTIONS = [
  { label: "关键词", value: "keyword" },
  { label: "同行账号", value: "competitor_account" },
  { label: "指定帖子链接", value: "manual_post" },
  { label: "爆款规则", value: "hot_post_rule" },
];

const COLLECTOR_TYPE_OPTIONS = [
  { label: "media_crawler：多平台采集（小红书/抖音/知乎）", value: "media_crawler" },
  { label: "xhs_sdk：小红书 SDK 直连采集", value: "xhs_sdk" },
];

export const SOURCE_ALLOWED_COLLECTOR_TYPES: Record<string, string[]> = {
  keyword: ["media_crawler", "xhs_sdk"],
  competitor_account: ["media_crawler"],
  manual_post: ["media_crawler", "xhs_sdk"],
  hot_post_rule: ["media_crawler"],
};

export function getAllowedCollectorTypesBySourceType(sourceType: string): string[] {
  return SOURCE_ALLOWED_COLLECTOR_TYPES[sourceType] ?? ["media_crawler"];
}

export function getDynamicFieldKeysByCollectorType(collectorType: string): string[] {
  if (collectorType === "media_crawler") {
    return [
      "login_type",
      "cookies",
      "enable_comments",
      "max_posts",
      "max_comments_per_post",
      "time_range",
    ];
  }
  return ["max_posts", "max_comments_per_post", "time_range"];
}

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

export type CreateFormState = {
  source_type: string;
  platform: string;
  name: string;
  value: string;
  collector_type: string;
  max_posts: string;
  max_comments_per_post: string;
  enabled: boolean;
  schedule_enabled: boolean;
  schedule_cron: string;
  cookies: string;
  login_type: string;
  enable_comments: boolean;
  time_range: string;
};

export const DEFAULT_CREATE_FORM: CreateFormState = {
  source_type: "keyword",
  platform: "xhs",
  name: "关键词 - 征信花了",
  value: "征信花了",
  collector_type: "media_crawler",
  max_posts: "10",
  max_comments_per_post: "10",
  enabled: true,
  schedule_enabled: false,
  schedule_cron: "0 */2 * * *",
  cookies: "",
  login_type: "qrcode",
  enable_comments: true,
  time_range: "",
};

function toPositiveInteger(value: string, fieldName: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${fieldName} 必须是正整数`);
  }
  return parsed;
}

export function buildPayloadFromForm(form: CreateFormState): MonitorSourceCreatePayload {
  const sourceType = form.source_type;
  const collectorType = form.collector_type;
  const maxPosts = toPositiveInteger(form.max_posts, "max_posts");
  const maxCommentsPerPost = toPositiveInteger(form.max_comments_per_post, "max_comments_per_post");

  const payloadValue = form.value.trim();
  const cookies = form.cookies.trim();

  if (collectorType === "media_crawler") {
    const validLoginTypes = ["cookie", "qrcode", "phone"];
    if (form.login_type && !validLoginTypes.includes(form.login_type)) {
      throw new Error("media_crawler login_type 必须是 cookie/qrcode/phone");
    }
  }

  const config: Record<string, unknown> = {
    collector_type: collectorType,
    max_posts: maxPosts,
    max_comments_per_post: maxCommentsPerPost,
  };

  if (collectorType === "media_crawler") {
    config.login_type = form.login_type || "qrcode";
    config.enable_comments = form.enable_comments;
    if (cookies) {
      config.cookies = cookies;
    }
  }

  if (form.time_range) {
    config.time_range = form.time_range;
  }

  const finalValue = payloadValue;

  return {
    source_type: sourceType,
    platform: form.platform,
    name: form.name.trim(),
    value: finalValue,
    config,
    enabled: form.enabled,
    schedule_enabled: form.schedule_enabled,
    schedule_cron: form.schedule_enabled ? form.schedule_cron.trim() || null : null,
    last_crawled_at: null,
  };
}

export default function MonitorSourcesPage({ embedded = false }: { embedded?: boolean } = {}) {
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
  const [collectorCapabilities, setCollectorCapabilities] = useState<Record<string, CollectorCapability>>({});
  const [capabilityLoading, setCapabilityLoading] = useState(true);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  const allowedCollectorTypes = useMemo(() => {
    return getAllowedCollectorTypesBySourceType(createForm.source_type);
  }, [createForm.source_type]);

  const collectorTypeOptions = useMemo(() => {
    return COLLECTOR_TYPE_OPTIONS.filter((option) => allowedCollectorTypes.includes(option.value));
  }, [allowedCollectorTypes]);

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

  async function loadCollectorCapabilities() {
    setCapabilityLoading(true);
    setCapabilityError(null);

    try {
      const result = await getCollectorsCapabilities();
      setCollectorCapabilities(result.collectors || {});
    } catch {
      setCapabilityError("采集器能力加载失败");
      setCollectorCapabilities({});
    } finally {
      setCapabilityLoading(false);
    }
  }

  useEffect(() => {
    void loadSources();
  }, [refreshTick]);

  useEffect(() => {
    void loadCollectorCapabilities();
  }, []);

  useEffect(() => {
    if (!allowedCollectorTypes.includes(createForm.collector_type)) {
      setCreateForm((current) => ({
        ...current,
        collector_type: allowedCollectorTypes[0] ?? "media_crawler",
      }));
    }
  }, [allowedCollectorTypes, createForm.collector_type]);

  const hasItems = useMemo(() => items.length > 0, [items]);
  const selectedCollectorType = createForm.collector_type;
  const capabilityEntries = useMemo(() => Object.entries(collectorCapabilities), [collectorCapabilities]);

  function updateSourceType(sourceType: string) {
    setCreateForm((current) => {
      const nextAllowed = getAllowedCollectorTypesBySourceType(sourceType);
      const nextCollectorType = nextAllowed.includes(current.collector_type)
        ? current.collector_type
        : nextAllowed[0];

      return {
        ...current,
        source_type: sourceType,
        collector_type: nextCollectorType,
        name: sourceType === "manual_post" ? "真实帖子链接" : current.name,
        value: sourceType === "manual_post" ? "" : current.value,
      };
    });
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
      const payload = buildPayloadFromForm(createForm);
      if (!payload.name || !payload.value) {
        throw new Error("名称和内容/链接不能为空");
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
      const result = await crawlMonitorSource(item.id) as CrawlTask & { queue_position?: number };
      const position = result.queue_position;
      setActionMessage(`${item.name} 已加入采集队列${position ? `，排队位置：${position}` : ""}，任务 #${result.id}`);
    } catch (crawlError) {
      setActionError(crawlError instanceof Error ? crawlError.message : "触发采集失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleToggleSchedule(item: MonitorSource) {
    setBusyKey(`schedule-${item.id}`);
    setActionError(null);
    setActionMessage(null);

    try {
      const newEnabled = !item.schedule_enabled;
      await updateMonitorSource(item.id, {
        schedule_enabled: newEnabled,
        schedule_cron: newEnabled ? (item.schedule_cron || "0 */2 * * *") : item.schedule_cron,
      });
      await refreshList();
      setActionMessage(`${item.name} 定时采集已${newEnabled ? "开启" : "关闭"}`);
    } catch (scheduleError) {
      setActionError(scheduleError instanceof Error ? scheduleError.message : "切换定时采集失败");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleGenerateDemo() {
    setDemoLoading(true);
    setDemoError(null);
    setActionMessage(null);

    try {
      const result = await generateDemoData();
      await refreshList();
      const sourceNames = result.demo_sources.map((s) => s.name).join("、");
      setActionMessage(`演示数据生成中：${sourceNames}。请稍后查看帖子池、评论池、线索池和日报。`);
    } catch (demoErr) {
      setDemoError(demoErr instanceof Error ? demoErr.message : "生成演示数据失败");
    } finally {
      setDemoLoading(false);
    }
  }

  const pageContent = (
    <>
      <header className="page-header">
        <div>
          <p className="page-eyebrow">监控源管理</p>
          <h1>智获客雷达</h1>
          <p className="page-description">查看、创建和管理监控源，支持关键词、同行账号、指定帖子链接和爆款规则。</p>
        </div>
      </header>

      <section className="card">
        <div className="card-header card-header-row">
          <div>
            <h2>采集器能力说明</h2>
            <p>来自接口 GET /api/collectors，展示当前后端已注册能力。</p>
          </div>
          <button type="button" onClick={() => void loadCollectorCapabilities()} disabled={capabilityLoading}>
            {capabilityLoading ? "加载中..." : "刷新能力"}
          </button>
        </div>
        {capabilityError ? <p className="inline-error">采集器能力加载失败</p> : null}
        {!capabilityError && capabilityEntries.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>采集器</th>
                  <th>状态</th>
                  <th>支持 source_type</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {capabilityEntries.map(([key, capability]) => (
                  <tr key={key}>
                    <td>{capability.name || key}</td>
                    <td>{capability.status}</td>
                    <td>{Array.isArray(capability.supports) ? capability.supports.join(" / ") : "-"}</td>
                    <td className="cell-break">{capability.description || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="card">
        <div className="card-header">
          <h2>新增监控源</h2>
          <p>当前采集依赖 MediaCrawler API 服务，请确保服务已启动。支持平台：小红书、抖音、知乎。</p>
        </div>
        <div className="state-panel state-empty" style={{ marginBottom: "12px" }}>
          <p>⚠️ 采集功能依赖 MediaCrawler。支持两种模式：<br/>
          · <strong>内嵌模式</strong>：设置环境变量 <code>MEDIA_CRAWLER_HOME</code> 指向 MediaCrawler 目录，无需单独启动服务<br/>
          · <strong>HTTP 模式</strong>：启动 MediaCrawler API 服务（默认 http://127.0.0.1:8080）<br/>
          可通过 <code>/api/monitor-sources/media-crawler/health</code> 检查当前模式和服务状态。</p>
        </div>
        <div style={{ marginBottom: "12px" }}>
            <button
              type="button"
              onClick={() => void handleGenerateDemo()}
              disabled={demoLoading}
              style={{
                padding: "10px 20px",
                fontSize: "14px",
                fontWeight: 600,
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                cursor: demoLoading ? "not-allowed" : "pointer",
              }}
            >
              {demoLoading ? "生成中..." : "🎭 一键生成演示数据"}
            </button>
            {demoError && <p className="inline-error" style={{ marginTop: "8px" }}>{demoError}</p>}
            <small className="field-hint" style={{ display: "block", marginTop: "4px" }}>
              自动创建演示监控源并触发采集，生成帖子、评论、线索、日报等完整链路数据。所有演示数据标记 demo=true。
            </small>
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
              placeholder={createForm.source_type === "manual_post" ? "帖子链接，例如：https://..." : "关键词/账号链接/规则内容"}
            />
          </label>
          <label>
            <span>collector_type</span>
            <select
              value={createForm.collector_type}
              onChange={(event) => setCreateForm((current) => ({ ...current, collector_type: event.target.value }))}
            >
              {collectorTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {selectedCollectorType === "media_crawler" && (
            <>
              <label>
                <span>登录方式 (login_type)</span>
                <select
                  value={createForm.login_type}
                  onChange={(event) => setCreateForm((current) => ({ ...current, login_type: event.target.value }))}
                >
                  <option value="qrcode">扫码登录（推荐）</option>
                  <option value="cookie">Cookie 登录</option>
                  <option value="phone">手机号登录</option>
                </select>
              </label>
              <label className="form-grid-span-2">
                <span>cookies（可选）</span>
                <textarea
                  className="text-area"
                  value={createForm.cookies}
                  onChange={(event) => setCreateForm((current) => ({ ...current, cookies: event.target.value }))}
                  placeholder="sessionid=...; userid=...（Cookie 登录时填写，扫码登录可留空）"
                />
                <small className="field-hint">
                  扫码登录无需填写 Cookie，采集时会弹出浏览器窗口扫码。Cookie 登录需填写目标平台的 Cookie。
                  支持小红书、抖音、知乎。
                </small>
              </label>
              <label>
                <span>采集评论 (enable_comments)</span>
                <select
                  value={createForm.enable_comments ? "true" : "false"}
                  onChange={(event) => setCreateForm((current) => ({ ...current, enable_comments: event.target.value === "true" }))}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </select>
              </label>
            </>
          )}

          <label>
            <span>时间范围 (time_range)</span>
            <select
              value={createForm.time_range}
              onChange={(event) => setCreateForm((current) => ({ ...current, time_range: event.target.value }))}
            >
              <option value="">不限（采集全部）</option>
              <option value="7d">最近 7 天</option>
              <option value="15d">最近 15 天</option>
              <option value="30d">最近 30 天</option>
              <option value="90d">最近 90 天</option>
            </select>
            <small className="field-hint">
              设置后仅入库发布时间在范围内的帖子和评论。设置时间范围会自动提升采集量以确保覆盖。
            </small>
          </label>

          <label>
            <span>max_posts</span>
            <input
              type="number"
              min={1}
              value={createForm.max_posts}
              onChange={(event) => setCreateForm((current) => ({ ...current, max_posts: event.target.value }))}
              placeholder="例如：10"
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
          <label>
            <span>定时采集</span>
            <select
              value={createForm.schedule_enabled ? "true" : "false"}
              onChange={(event) => setCreateForm((current) => ({ ...current, schedule_enabled: event.target.value === "true" }))}
            >
              <option value="false">关闭</option>
              <option value="true">开启</option>
            </select>
          </label>
          {createForm.schedule_enabled && (
            <label>
              <span>Cron 表达式</span>
              <input
                value={createForm.schedule_cron}
                onChange={(event) => setCreateForm((current) => ({ ...current, schedule_cron: event.target.value }))}
                placeholder="0 */2 * * *（每2小时）"
              />
              <small className="field-hint">
                格式：分 时 日 月 周，例如：0 */2 * * * = 每2小时，0 9 * * * = 每天9点，30 8,20 * * * = 每天8:30和20:30
              </small>
            </label>
          )}
          <div className="form-actions form-grid-span-2">
            <button type="submit" disabled={createLoading}>
              {createLoading ? "提交中..." : "新增"}
            </button>
          </div>
        </form>
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
                  <th>时间范围</th>
                  <th>状态</th>
                  <th>定时采集</th>
                  <th>最后采集时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const toggleLoading = busyKey === `toggle-${item.id}`;
                  const deleteLoading = busyKey === `delete-${item.id}`;
                  const crawlLoading = busyKey === `crawl-${item.id}`;
                  const scheduleLoading = busyKey === `schedule-${item.id}`;

                  return (
                    <tr key={item.id}>
                      <td>{item.source_type}</td>
                      <td>{item.platform}</td>
                      <td>{item.name}</td>
                      <td className="cell-break">{item.value}</td>
                      <td>{typeof item.config === "object" && item.config && "collector_type" in item.config ? String((item.config as Record<string, unknown>).collector_type) : "media_crawler"}</td>
                      <td>{typeof item.config === "object" && item.config && "time_range" in item.config ? String((item.config as Record<string, unknown>).time_range) : "-"}</td>
                      <td>{item.enabled ? "启用" : "停用"}</td>
                      <td>
                        {item.schedule_enabled ? (
                          <span className="status-pill status-running">{item.schedule_cron || "未配置"}</span>
                        ) : (
                          <span className="status-pill status-failed">关闭</span>
                        )}
                      </td>
                      <td>{formatDateTime(item.last_crawled_at)}</td>
                      <td>
                        <div className="action-row">
                          <button type="button" onClick={() => void handleToggle(item)} disabled={toggleLoading || deleteLoading || crawlLoading}>
                            {item.enabled ? "停用" : "启用"}
                          </button>
                          <button type="button" onClick={() => void handleCrawl(item)} disabled={toggleLoading || deleteLoading || crawlLoading}>
                            {crawlLoading ? "入队中..." : "立即采集"}
                          </button>
                          <button type="button" onClick={() => void handleToggleSchedule(item)} disabled={scheduleLoading || deleteLoading}>
                            {scheduleLoading ? "..." : item.schedule_enabled ? "关闭定时" : "开启定时"}
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
    </>
  );

  if (embedded) return pageContent;
  return <main className="page-shell">{pageContent}</main>;
}
