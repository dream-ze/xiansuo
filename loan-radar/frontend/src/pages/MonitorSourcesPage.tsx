import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  createMonitorSource,
  deleteMonitorSource,
  getCollectorsCapabilities,
  getMonitorSources,
  toggleMonitorSource,
  crawlMonitorSource,
  type CollectorCapability,
  type CrawlTask,
  type MonitorSource,
  type MonitorSourceCreatePayload,
} from "../api/client";

const PLATFORM_OPTIONS = [
  { label: "小红书", value: "xhs" },
  { label: "抖音", value: "douyin" },
  { label: "快手", value: "kuaishou" },
  { label: "B站", value: "bilibili" },
  { label: "微博", value: "weibo" },
  { label: "贴吧", value: "tieba" },
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
  { label: "mock：演示 / 回归测试", value: "mock" },
  { label: "playwright：指定公开帖子链接", value: "playwright" },
  { label: "media_crawler：多平台采集（小红书/抖音/快手/B站/微博/贴吧/知乎）", value: "media_crawler" },
  { label: "external_api：外部采集 API", value: "external_api" },
  { label: "generic_web：通用网页采集", value: "generic_web" },
];

export const SOURCE_ALLOWED_COLLECTOR_TYPES: Record<string, string[]> = {
  keyword: ["mock", "media_crawler", "external_api"],
  competitor_account: ["mock", "media_crawler", "external_api"],
  manual_post: ["playwright", "media_crawler", "generic_web"],
  hot_post_rule: ["mock", "media_crawler"],
};

export function getAllowedCollectorTypesBySourceType(sourceType: string): string[] {
  return SOURCE_ALLOWED_COLLECTOR_TYPES[sourceType] ?? ["mock"];
}

export function getDynamicFieldKeysByCollectorType(collectorType: string): string[] {
  if (collectorType === "external_api") {
    return ["entry_url", "endpoint", "api_key_env", "max_posts", "max_comments_per_post"];
  }
  if (collectorType === "generic_web") {
    return [
      "entry_url",
      "selectors.post_container",
      "selectors.title",
      "selectors.content",
      "selectors.author",
      "selectors.comment_item",
      "max_posts",
      "max_comments_per_post",
    ];
  }
  if (collectorType === "media_crawler") {
    return [
      "login_type",
      "cookies",
      "enable_comments",
      "max_posts",
      "max_comments_per_post",
    ];
  }
  return ["max_posts", "max_comments_per_post"];
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
  entry_url: string;
  endpoint: string;
  api_key_env: string;
  cookies: string;
  login_type: string;
  enable_comments: boolean;
  selector_post_container: string;
  selector_title: string;
  selector_content: string;
  selector_author: string;
  selector_comment_item: string;
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
  entry_url: "",
  endpoint: "",
  api_key_env: "",
  cookies: "",
  login_type: "qrcode",
  enable_comments: true,
  selector_post_container: "",
  selector_title: "",
  selector_content: "",
  selector_author: "",
  selector_comment_item: "",
};

function toPositiveInteger(value: string, fieldName: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${fieldName} 必须是正整数`);
  }
  return parsed;
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//.test(value);
}

export function buildPayloadFromForm(form: CreateFormState): MonitorSourceCreatePayload {
  const sourceType = form.source_type;
  const collectorType = form.collector_type;
  const maxPosts = toPositiveInteger(form.max_posts, "max_posts");
  const maxCommentsPerPost = toPositiveInteger(form.max_comments_per_post, "max_comments_per_post");

  const payloadValue = form.value.trim();
  const entryUrl = form.entry_url.trim();
  const endpoint = form.endpoint.trim();
  const apiKeyEnv = form.api_key_env.trim();
  const cookies = form.cookies.trim();

  if (sourceType === "manual_post" && collectorType === "playwright" && !isHttpUrl(payloadValue)) {
    throw new Error("manual_post + playwright 时，value 必须是 http/https URL");
  }

  if (collectorType === "generic_web" && !entryUrl && !payloadValue) {
    throw new Error("generic_web 必须填写 entry_url 或 value");
  }

  if (collectorType === "external_api" && !endpoint) {
    throw new Error("external_api 必须填写 endpoint");
  }

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

  if (collectorType === "external_api") {
    config.external_api = {
      endpoint,
      ...(apiKeyEnv ? { api_key_env: apiKeyEnv } : {}),
    };
  }

  if (collectorType === "generic_web") {
    const selectors: Record<string, string> = {};
    if (form.selector_post_container.trim()) selectors.post_container = form.selector_post_container.trim();
    if (form.selector_title.trim()) selectors.title = form.selector_title.trim();
    if (form.selector_content.trim()) selectors.content = form.selector_content.trim();
    if (form.selector_author.trim()) selectors.author = form.selector_author.trim();
    if (form.selector_comment_item.trim()) selectors.comment_item = form.selector_comment_item.trim();

    config.entry_url = entryUrl || payloadValue;
    if (Object.keys(selectors).length > 0) {
      config.selectors = selectors;
    }
  }

  if (collectorType === "media_crawler") {
    config.login_type = form.login_type || "qrcode";
    config.enable_comments = form.enable_comments;
    if (cookies) {
      config.cookies = cookies;
    }
  }

  const finalValue = payloadValue;

  return {
    source_type: sourceType,
    platform: form.platform,
    name: form.name.trim(),
    value: finalValue,
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
  const [collectorCapabilities, setCollectorCapabilities] = useState<Record<string, CollectorCapability>>({});
  const [capabilityLoading, setCapabilityLoading] = useState(true);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);

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
        collector_type: allowedCollectorTypes[0] ?? "mock",
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
          <p>根据 source_type 选择可用 collector_type，并填写对应配置。</p>
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
              placeholder={createForm.source_type === "manual_post" ? "公开帖子链接，例如：https://..." : "关键词/账号链接/规则内容"}
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

          {(selectedCollectorType === "external_api" || selectedCollectorType === "generic_web") && (
            <label>
              <span>entry_url</span>
              <input
                value={createForm.entry_url}
                onChange={(event) => setCreateForm((current) => ({ ...current, entry_url: event.target.value }))}
                placeholder="https://example.com/..."
              />
            </label>
          )}

          {selectedCollectorType === "external_api" && (
            <>
              <label>
                <span>endpoint</span>
                <input
                  value={createForm.endpoint}
                  onChange={(event) => setCreateForm((current) => ({ ...current, endpoint: event.target.value }))}
                  placeholder="https://your-api.example.com/collect"
                />
              </label>
              <label>
                <span>api_key_env</span>
                <input
                  value={createForm.api_key_env}
                  onChange={(event) => setCreateForm((current) => ({ ...current, api_key_env: event.target.value }))}
                  placeholder="EXTERNAL_COLLECTOR_API_KEY"
                />
              </label>
            </>
          )}

          {selectedCollectorType === "generic_web" && (
            <>
              <label>
                <span>selectors.post_container</span>
                <input
                  value={createForm.selector_post_container}
                  onChange={(event) => setCreateForm((current) => ({ ...current, selector_post_container: event.target.value }))}
                  placeholder="article, .post"
                />
              </label>
              <label>
                <span>selectors.title</span>
                <input
                  value={createForm.selector_title}
                  onChange={(event) => setCreateForm((current) => ({ ...current, selector_title: event.target.value }))}
                  placeholder="h1, h2"
                />
              </label>
              <label>
                <span>selectors.content</span>
                <input
                  value={createForm.selector_content}
                  onChange={(event) => setCreateForm((current) => ({ ...current, selector_content: event.target.value }))}
                  placeholder="article, .content"
                />
              </label>
              <label>
                <span>selectors.author</span>
                <input
                  value={createForm.selector_author}
                  onChange={(event) => setCreateForm((current) => ({ ...current, selector_author: event.target.value }))}
                  placeholder=".author"
                />
              </label>
              <label>
                <span>selectors.comment_item</span>
                <input
                  value={createForm.selector_comment_item}
                  onChange={(event) => setCreateForm((current) => ({ ...current, selector_comment_item: event.target.value }))}
                  placeholder=".comment"
                />
              </label>
            </>
          )}

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
                  支持小红书、抖音、快手、B站、微博、贴吧、知乎。
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
