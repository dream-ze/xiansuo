import { useEffect, useMemo, useState } from "react";

import {
  convertLeadToCrm,
  createCrmCustomer,
  createCrmFollowUp,
  createCrmTask,
  getCrmCustomers,
  getCrmFollowUps,
  getCrmTasks,
  getLeads,
  updateCrmCustomer,
  updateCrmTask,
  type CrmCustomer,
  type CrmFollowUp,
  type CrmTask,
  type Lead,
} from "../api/client";
import { showToast } from "../components/ToastContainer";

const STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "new", label: "新客户" },
  { value: "following", label: "跟进中" },
  { value: "qualified", label: "已确认需求" },
  { value: "deal", label: "已成交" },
  { value: "lost", label: "已流失" },
  { value: "invalid", label: "无效客户" },
];

const STATUS_LABELS: Record<string, string> = {
  new: "新客户",
  following: "跟进中",
  qualified: "已确认需求",
  deal: "已成交",
  lost: "已流失",
  invalid: "无效客户",
};

const LEVEL_OPTIONS = ["", "A", "B", "C", "D"];

const PLATFORM_LABELS: Record<string, string> = {
  xhs: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
};

type CustomerForm = {
  name: string;
  phone: string;
  contact_info: string;
  owner_name: string;
  demand_amount: string;
  loan_purpose: string;
  qualification_summary: string;
  risk_level: string;
  customer_level: string;
  status: string;
  notes: string;
};

type FollowUpForm = {
  content: string;
  next_follow_up_at: string;
};

const EMPTY_CUSTOMER_FORM: CustomerForm = {
  name: "",
  phone: "",
  contact_info: "",
  owner_name: "",
  demand_amount: "",
  loan_purpose: "",
  qualification_summary: "",
  risk_level: "",
  customer_level: "",
  status: "new",
  notes: "",
};

const EMPTY_FOLLOW_UP_FORM: FollowUpForm = {
  content: "",
  next_follow_up_at: "",
};

function compactText(text: string | null | undefined, fallback = "-") {
  return text && text.trim() ? text : fallback;
}

function formatMoney(value: number | null | undefined) {
  if (!value) return "-";
  if (value >= 10000) return `${(value / 10000).toFixed(value % 10000 === 0 ? 0 : 1)} 万`;
  return value.toLocaleString();
}

function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRelativeTime(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 0) {
    if (diffMins > -60) return `${Math.abs(diffMins)} 分钟前`;
    const diffHours = Math.floor(Math.abs(diffMins) / 60);
    if (diffHours < 24) return `${diffHours} 小时前`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} 天前`;
  }
  if (diffMins < 60) return `${diffMins} 分钟后`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} 小时后`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays <= 7) return `${diffDays} 天后`;
  return formatDate(value);
}

function isOverdue(dueAt: string | null | undefined): boolean {
  if (!dueAt) return false;
  return new Date(dueAt) < new Date();
}

function isDueToday(dueAt: string | null | undefined): boolean {
  if (!dueAt) return false;
  const due = new Date(dueAt);
  const now = new Date();
  return due.toDateString() === now.toDateString() && due >= now;
}

function getStatusLabel(status: string) {
  return STATUS_LABELS[status] || status;
}

function toCustomerForm(customer: CrmCustomer): CustomerForm {
  return {
    name: customer.name,
    phone: customer.phone || "",
    contact_info: customer.contact_info || "",
    owner_name: customer.owner_name || "",
    demand_amount: customer.demand_amount ? String(customer.demand_amount) : "",
    loan_purpose: customer.loan_purpose || "",
    qualification_summary: customer.qualification_summary || "",
    risk_level: customer.risk_level || "",
    customer_level: customer.customer_level || "",
    status: customer.status,
    notes: customer.notes || "",
  };
}

function buildCustomerPayload(form: CustomerForm) {
  return {
    name: form.name.trim(),
    phone: form.phone.trim() || null,
    contact_info: form.contact_info.trim() || null,
    owner_name: form.owner_name.trim() || null,
    demand_amount: form.demand_amount ? Number(form.demand_amount) : null,
    loan_purpose: form.loan_purpose.trim() || null,
    qualification_summary: form.qualification_summary.trim() || null,
    risk_level: form.risk_level.trim() || null,
    customer_level: form.customer_level.trim() || null,
    status: form.status || "new",
    notes: form.notes.trim() || null,
  };
}

export default function CrmCustomersPage() {
  const [items, setItems] = useState<CrmCustomer[]>([]);
  const [keyword, setKeyword] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [status, setStatus] = useState("");
  const [level, setLevel] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const [selected, setSelected] = useState<CrmCustomer | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<CrmCustomer | null>(null);
  const [customerForm, setCustomerForm] = useState<CustomerForm>(EMPTY_CUSTOMER_FORM);
  const [savingCustomer, setSavingCustomer] = useState(false);

  const [followUps, setFollowUps] = useState<CrmFollowUp[]>([]);
  const [tasks, setTasks] = useState<CrmTask[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [followUpForm, setFollowUpForm] = useState<FollowUpForm>(EMPTY_FOLLOW_UP_FORM);
  const [savingFollowUp, setSavingFollowUp] = useState(false);

  const [importOpen, setImportOpen] = useState(false);
  const [leadKeyword, setLeadKeyword] = useState("");
  const [leadLevel, setLeadLevel] = useState("");
  const [leadLoading, setLeadLoading] = useState(false);
  const [leadError, setLeadError] = useState<string | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [convertingId, setConvertingId] = useState<number | null>(null);

  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);

  const customerTaskMap = useMemo(() => {
    const map = new Map<number, CrmTask[]>();
    for (const task of tasks) {
      if (task.customer_id != null && task.status === "pending") {
        const list = map.get(task.customer_id) || [];
        list.push(task);
        map.set(task.customer_id, list);
      }
    }
    return map;
  }, [tasks]);

  const filteredItems = useMemo(() => {
    return level ? items.filter((item) => item.customer_level === level) : items;
  }, [items, level]);

  const stats = useMemo(() => {
    const pending = items.filter((item) => ["new", "following", "qualified"].includes(item.status)).length;
    const deals = items.filter((item) => item.status === "deal").length;
    const overdueCount = tasks.filter((t) => t.is_overdue).length;
    const todayCount = tasks.filter((t) => isDueToday(t.due_at)).length;
    return { pending, deals, overdueCount, todayCount };
  }, [items, tasks]);

  const activeNextReminder = useMemo(() => {
    if (!selected) return null;
    const customerTasks = customerTaskMap.get(selected.id) || [];
    const pending = customerTasks.filter((t) => t.status === "pending" && t.due_at).sort((a, b) => new Date(a.due_at!).getTime() - new Date(b.due_at!).getTime());
    return pending[0] || null;
  }, [selected, customerTaskMap]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const result = await getCrmCustomers({
        keyword: keyword || undefined,
        owner_name: ownerName || undefined,
        status: status || undefined,
        page: 1,
        page_size: 80,
      });
      setItems(result.items);
      setTotal(result.total);
      setSelected((current) => {
        if (!current) return result.items[0] || null;
        return result.items.find((item) => item.id === current.id) || result.items[0] || null;
      });

      const allTasksResult = await getCrmTasks({ status: "pending", page: 1, page_size: 200 });
      setTasks(allTasksResult.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "客户列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(customer: CrmCustomer | null) {
    if (!customer) {
      setFollowUps([]);
      return;
    }
    setDetailLoading(true);
    try {
      const nextFollowUps = await getCrmFollowUps({ customer_id: customer.id, page: 1, page_size: 20 });
      setFollowUps(nextFollowUps.items);
    } catch (err) {
      showToast("error", "详情加载失败", err instanceof Error ? err.message : "请稍后重试");
    } finally {
      setDetailLoading(false);
    }
  }

  async function loadImportLeads() {
    setLeadLoading(true);
    setLeadError(null);
    try {
      const result = await getLeads({
        keyword: leadKeyword || undefined,
        lead_level: leadLevel || undefined,
        converted_to_crm: false,
        page: 1,
        page_size: 20,
      });
      setLeads(result.items);
    } catch (err) {
      setLeadError(err instanceof Error ? err.message : "线索加载失败");
    } finally {
      setLeadLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    void loadDetail(selected);
  }, [selected?.id]);

  function openCreateForm() {
    setEditingCustomer(null);
    setCustomerForm(EMPTY_CUSTOMER_FORM);
    setFormOpen(true);
  }

  function openEditForm(customer: CrmCustomer) {
    setEditingCustomer(customer);
    setCustomerForm(toCustomerForm(customer));
    setFormOpen(true);
  }

  async function handleSaveCustomer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!customerForm.name.trim()) {
      showToast("error", "请填写客户名称", "客户名称是建档的唯一必填项");
      return;
    }
    setSavingCustomer(true);
    try {
      const payload = buildCustomerPayload(customerForm);
      const saved = editingCustomer
        ? await updateCrmCustomer(editingCustomer.id, payload)
        : await createCrmCustomer(payload);
      showToast("success", editingCustomer ? "客户已更新" : "客户已新增", saved.name);
      setFormOpen(false);
      setSelected(saved);
      await loadData();
    } catch (err) {
      showToast("error", "保存失败", err instanceof Error ? err.message : "请稍后重试");
    } finally {
      setSavingCustomer(false);
    }
  }

  async function handleStatusChange(customer: CrmCustomer, nextStatus: string) {
    try {
      const saved = await updateCrmCustomer(customer.id, { status: nextStatus });
      showToast("success", "状态已更新", `${customer.name} → ${getStatusLabel(nextStatus)}`);
      setSelected(saved);
      await loadData();
    } catch (err) {
      showToast("error", "状态更新失败", err instanceof Error ? err.message : "请稍后重试");
    }
  }

  async function handleCreateFollowUp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    if (!followUpForm.content.trim()) {
      showToast("error", "请填写跟进内容", "记录一下沟通了什么");
      return;
    }

    setSavingFollowUp(true);
    try {
      await createCrmFollowUp({
        customer_id: selected.id,
        owner_name: selected.owner_name,
        follow_up_type: "manual",
        content: followUpForm.content.trim(),
      });

      if (followUpForm.next_follow_up_at) {
        await createCrmTask({
          customer_id: selected.id,
          title: `跟进：${selected.name}`,
          task_type: "follow_up",
          owner_name: selected.owner_name,
          due_at: new Date(followUpForm.next_follow_up_at).toISOString(),
          status: "pending",
          priority: selected.customer_level === "A" ? "high" : "normal",
        });
      }

      setFollowUpForm(EMPTY_FOLLOW_UP_FORM);
      showToast("success", "跟进已记录", followUpForm.next_follow_up_at ? "已设置下次提醒" : undefined);
      await loadDetail(selected);
      const allTasksResult = await getCrmTasks({ status: "pending", page: 1, page_size: 200 });
      setTasks(allTasksResult.items);
    } catch (err) {
      showToast("error", "跟进保存失败", err instanceof Error ? err.message : "请稍后重试");
    } finally {
      setSavingFollowUp(false);
    }
  }

  async function handleCompleteTask(task: CrmTask) {
    setBusyTaskId(task.id);
    try {
      await updateCrmTask(task.id, { status: "done" });
      showToast("success", "任务已完成", task.title);
      const allTasksResult = await getCrmTasks({ status: "pending", page: 1, page_size: 200 });
      setTasks(allTasksResult.items);
    } catch (err) {
      showToast("error", "完成失败", err instanceof Error ? err.message : "请稍后重试");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleConvertLead(lead: Lead) {
    setConvertingId(lead.id);
    try {
      const result = await convertLeadToCrm(lead.id, { owner_name: selected?.owner_name || undefined });
      showToast("success", "线索已导入客户", result.customer.name);
      setImportOpen(false);
      setSelected(result.customer);
      await loadData();
    } catch (err) {
      showToast("error", "导入失败", err instanceof Error ? err.message : "请稍后重试");
    } finally {
      setConvertingId(null);
    }
  }

  const activeCustomer = selected;

  function getCustomerReminderTag(customer: CrmCustomer) {
    const customerTasks = customerTaskMap.get(customer.id) || [];
    const overdueTasks = customerTasks.filter((t) => t.is_overdue);
    const todayTasks = customerTasks.filter((t) => isDueToday(t.due_at));

    if (overdueTasks.length > 0) return { type: "overdue" as const, label: "已逾期" };
    if (todayTasks.length > 0) return { type: "today" as const, label: "今天联系" };
    const nextTask = customerTasks.filter((t) => t.due_at).sort((a, b) => new Date(a.due_at!).getTime() - new Date(b.due_at!).getTime())[0];
    if (nextTask) return { type: "scheduled" as const, label: formatRelativeTime(nextTask.due_at) || "已安排" };
    return null;
  }

  return (
    <main className="page-shell crm-workbench">
      <header className="page-header crm-workbench-hero">
        <div>
          <p className="page-eyebrow">客户管理</p>
          <h1>智获客雷达</h1>
          <p className="page-description">管理客户档案，记录跟进并设置提醒，不错过任何一次联系。</p>
        </div>
        <div className="action-row">
          <button className="btn-secondary" type="button" onClick={() => { setImportOpen(true); void loadImportLeads(); }}>从线索导入</button>
          <button className="btn-primary" type="button" onClick={openCreateForm}>新增客户</button>
        </div>
      </header>

      <section className="crm-kpi-grid">
        <div className="crm-kpi-card"><span>客户总数</span><strong>{total}</strong><p>当前筛选范围内</p></div>
        <div className="crm-kpi-card crm-kpi-warn"><span>逾期未联系</span><strong>{stats.overdueCount}</strong><p>需要立即跟进</p></div>
        <div className="crm-kpi-card crm-kpi-today"><span>今天待联系</span><strong>{stats.todayCount}</strong><p>今天需要跟进</p></div>
        <div className="crm-kpi-card"><span>已成交</span><strong>{stats.deals}</strong><p>状态为已成交</p></div>
      </section>

      <section className="card crm-filter-card">
        <div className="filter-grid crm-filter-grid">
          <label><span>搜索客户</span><input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="客户名、昵称" /></label>
          <label><span>负责人</span><input value={ownerName} onChange={(e) => setOwnerName(e.target.value)} placeholder="销售姓名" /></label>
          <label><span>客户状态</span><select value={status} onChange={(e) => setStatus(e.target.value)}>{STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label><span>客户等级</span><select value={level} onChange={(e) => setLevel(e.target.value)}>{LEVEL_OPTIONS.map((option) => <option key={option || "all"} value={option}>{option || "全部等级"}</option>)}</select></label>
        </div>
        <div className="crm-filter-actions">
          <button type="button" className="btn-primary" onClick={() => void loadData()} disabled={loading}>{loading ? "查询中..." : "查询客户"}</button>
        </div>
      </section>

      {error ? <div className="state-panel state-error"><p>{error}</p></div> : null}

      <div className="crm-workbench-grid">
        <section className="card crm-customer-list">
          <div className="card-header card-header-row">
            <div>
              <h2>客户列表</h2>
              <p>点击客户查看详情和跟进记录</p>
            </div>
            <span className="crm-count">{filteredItems.length} 位客户</span>
          </div>

          {loading ? <p className="state-text">客户加载中...</p> : null}
          {!loading && filteredItems.length === 0 ? (
            <div className="state-panel state-empty">
              <p>还没有符合条件的客户。可以先新增客户，或从线索池导入。</p>
            </div>
          ) : null}

          <div className="crm-customer-stack">
            {filteredItems.map((item) => {
              const reminder = getCustomerReminderTag(item);
              return (
                <button
                  key={item.id}
                  type="button"
                  className={activeCustomer?.id === item.id ? "crm-customer-row active" : "crm-customer-row"}
                  onClick={() => setSelected(item)}
                >
                  <div className="crm-customer-row-main">
                    <div>
                      <strong>{item.name}</strong>
                      <p>{compactText(item.loan_purpose, "暂未填写贷款用途")}</p>
                    </div>
                    <div className="crm-customer-row-right">
                      {reminder ? (
                        <span className={`crm-reminder-tag crm-reminder-${reminder.type}`}>{reminder.label}</span>
                      ) : null}
                      <span className={`status-pill status-${item.status}`}>{getStatusLabel(item.status)}</span>
                    </div>
                  </div>
                  <div className="crm-customer-meta">
                    <span>{item.customer_level ? `${item.customer_level} 级` : "未评级"}</span>
                    <span>{formatMoney(item.demand_amount)}</span>
                    <span>{compactText(item.owner_name, "未分配")}</span>
                    <span>{item.source_platform ? PLATFORM_LABELS[item.source_platform] || item.source_platform : "手动录入"}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <aside className="card crm-detail-panel">
          {activeCustomer ? (
            <>
              <div className="crm-detail-header">
                <div>
                  <h2>{activeCustomer.name}</h2>
                  <div className="crm-detail-status-row">
                    <span className={`status-pill status-${activeCustomer.status}`}>{getStatusLabel(activeCustomer.status)}</span>
                    {activeCustomer.customer_level ? <span className="crm-level-badge">{activeCustomer.customer_level}级</span> : null}
                    <select
                      className="crm-status-quick"
                      value={activeCustomer.status}
                      onChange={(e) => void handleStatusChange(activeCustomer, e.target.value)}
                    >
                      {STATUS_OPTIONS.filter((o) => o.value).map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <button type="button" className="btn-secondary" onClick={() => openEditForm(activeCustomer)}>编辑资料</button>
              </div>

              {activeNextReminder ? (
                <div className={`crm-next-reminder ${activeNextReminder.is_overdue ? "crm-reminder-overdue" : ""}`}>
                  <div className="crm-next-reminder-icon">⏰</div>
                  <div className="crm-next-reminder-info">
                    <strong>{activeNextReminder.is_overdue ? "已逾期，请尽快联系" : "下次提醒"}</strong>
                    <span>{formatDateTime(activeNextReminder.due_at)}（{formatRelativeTime(activeNextReminder.due_at)}）</span>
                  </div>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={busyTaskId === activeNextReminder.id}
                    onClick={() => void handleCompleteTask(activeNextReminder)}
                  >
                    {busyTaskId === activeNextReminder.id ? "..." : "已联系"}
                  </button>
                </div>
              ) : (
                <div className="crm-next-reminder crm-reminder-none">
                  <div className="crm-next-reminder-icon">📋</div>
                  <div className="crm-next-reminder-info">
                    <strong>暂无提醒</strong>
                    <span>在下方记录跟进时可设置下次提醒时间</span>
                  </div>
                </div>
              )}

              <section className="drawer-section">
                <h4 className="drawer-section-title">基础资料</h4>
                <div className="detail-grid compact">
                  <div className="detail-field"><span className="detail-label">电话</span><strong className="detail-value">{compactText(activeCustomer.phone)}</strong></div>
                  <div className="detail-field"><span className="detail-label">其他联系方式</span><strong className="detail-value">{compactText(activeCustomer.contact_info)}</strong></div>
                  <div className="detail-field"><span className="detail-label">负责人</span><strong className="detail-value">{compactText(activeCustomer.owner_name, "未分配")}</strong></div>
                  <div className="detail-field"><span className="detail-label">需求金额</span><strong className="detail-value">{formatMoney(activeCustomer.demand_amount)}</strong></div>
                  <div className="detail-field"><span className="detail-label">贷款用途</span><strong className="detail-value">{compactText(activeCustomer.loan_purpose)}</strong></div>
                  <div className="detail-field"><span className="detail-label">风险等级</span><strong className="detail-value">{compactText(activeCustomer.risk_level, "未评估")}</strong></div>
                </div>
              </section>

              {activeCustomer.source_platform || activeCustomer.source_summary ? (
                <section className="drawer-section">
                  <h4 className="drawer-section-title">来源信息</h4>
                  <div className="crm-source-box">
                    <div><span>来源</span><strong>{activeCustomer.source_platform ? PLATFORM_LABELS[activeCustomer.source_platform] || activeCustomer.source_platform : "手动录入"}</strong></div>
                    {activeCustomer.source_summary ? <div><span>原始内容</span><p>{activeCustomer.source_summary}</p></div> : null}
                    {activeCustomer.qualification_summary ? <div><span>资质摘要</span><p>{activeCustomer.qualification_summary}</p></div> : null}
                  </div>
                </section>
              ) : null}

              <section className="drawer-section">
                <h4 className="drawer-section-title">跟进记录</h4>
                {detailLoading ? <p className="state-text">加载中...</p> : null}

                <div className="crm-timeline">
                  {followUps.length === 0 && !detailLoading ? (
                    <div className="crm-timeline-empty">暂无跟进记录，在下方记录第一次沟通</div>
                  ) : null}
                  {followUps.map((item) => (
                    <div key={item.id} className="crm-timeline-item">
                      <div className="crm-timeline-dot" />
                      <div className="crm-timeline-content">
                        <div className="crm-timeline-header">
                          <span className="crm-timeline-type">{item.follow_up_type === "stage_change" ? "状态变更" : "手动跟进"}</span>
                          <span className="crm-timeline-time">{formatDateTime(item.created_at)}</span>
                        </div>
                        <p>{item.content}</p>
                        {item.customer_feedback ? <p className="crm-timeline-feedback">客户反馈：{item.customer_feedback}</p> : null}
                        {item.next_action ? <p className="crm-timeline-next">下一步：{item.next_action}</p> : null}
                      </div>
                    </div>
                  ))}
                </div>

                <form className="crm-follow-form" onSubmit={(event) => void handleCreateFollowUp(event)}>
                  <label>
                    <span>沟通内容</span>
                    <textarea
                      className="text-area"
                      value={followUpForm.content}
                      onChange={(e) => setFollowUpForm((current) => ({ ...current, content: e.target.value }))}
                      placeholder="记录沟通内容，例如：客户确认需要 30 万经营周转"
                      rows={2}
                    />
                  </label>
                  <div className="crm-follow-form-row">
                    <label>
                      <span>下次提醒时间</span>
                      <input
                        type="datetime-local"
                        value={followUpForm.next_follow_up_at}
                        onChange={(e) => setFollowUpForm((current) => ({ ...current, next_follow_up_at: e.target.value }))}
                      />
                    </label>
                    <button type="submit" className="btn-primary" disabled={savingFollowUp}>
                      {savingFollowUp ? "保存中..." : "记录跟进"}
                    </button>
                  </div>
                </form>
              </section>

              {activeCustomer.notes ? (
                <section className="drawer-section">
                  <h4 className="drawer-section-title">备注</h4>
                  <div className="detail-text-block">{activeCustomer.notes}</div>
                </section>
              ) : null}
            </>
          ) : (
            <div className="state-panel state-empty"><p>请选择一个客户查看详情，或新增客户开始建档。</p></div>
          )}
        </aside>
      </div>

      {formOpen ? (
        <div className="modal-overlay" role="presentation" onClick={() => setFormOpen(false)}>
          <div className="modal-content modal-lg" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div><h2>{editingCustomer ? "编辑客户" : "新增客户"}</h2><p>只需客户名称即可建档，其余资料可后续补充。</p></div>
              <button type="button" className="modal-close" onClick={() => setFormOpen(false)}>×</button>
            </div>
            <form className="modal-body" onSubmit={(event) => void handleSaveCustomer(event)}>
              <div className="form-grid">
                <label><span>客户名称 *</span><input value={customerForm.name} onChange={(e) => setCustomerForm((current) => ({ ...current, name: e.target.value }))} placeholder="客户姓名或企业名称" /></label>
                <label><span>负责人</span><input value={customerForm.owner_name} onChange={(e) => setCustomerForm((current) => ({ ...current, owner_name: e.target.value }))} placeholder="销售负责人" /></label>
                <label><span>电话</span><input value={customerForm.phone} onChange={(e) => setCustomerForm((current) => ({ ...current, phone: e.target.value }))} placeholder="手机号" /></label>
                <label><span>其他联系方式</span><input value={customerForm.contact_info} onChange={(e) => setCustomerForm((current) => ({ ...current, contact_info: e.target.value }))} placeholder="微信、主页或其他联系方式" /></label>
                <label><span>需求金额</span><input type="number" value={customerForm.demand_amount} onChange={(e) => setCustomerForm((current) => ({ ...current, demand_amount: e.target.value }))} placeholder="例如 300000" /></label>
                <label><span>贷款用途</span><input value={customerForm.loan_purpose} onChange={(e) => setCustomerForm((current) => ({ ...current, loan_purpose: e.target.value }))} placeholder="经营周转、装修、车辆等" /></label>
                <label><span>客户等级</span><select value={customerForm.customer_level} onChange={(e) => setCustomerForm((current) => ({ ...current, customer_level: e.target.value }))}>{LEVEL_OPTIONS.map((option) => <option key={option || "empty"} value={option}>{option || "未评级"}</option>)}</select></label>
                <label><span>客户状态</span><select value={customerForm.status} onChange={(e) => setCustomerForm((current) => ({ ...current, status: e.target.value }))}>{STATUS_OPTIONS.filter((option) => option.value).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
                <label className="form-grid-span-2"><span>资质摘要</span><textarea className="text-area" value={customerForm.qualification_summary} onChange={(e) => setCustomerForm((current) => ({ ...current, qualification_summary: e.target.value }))} placeholder="收入、流水、征信、资产等关键信息" /></label>
                <label className="form-grid-span-2"><span>备注</span><textarea className="text-area" value={customerForm.notes} onChange={(e) => setCustomerForm((current) => ({ ...current, notes: e.target.value }))} placeholder="补充客户背景或沟通偏好" /></label>
              </div>
              <div className="form-actions"><button type="submit" className="btn-primary" disabled={savingCustomer}>{savingCustomer ? "保存中..." : "保存客户"}</button></div>
            </form>
          </div>
        </div>
      ) : null}

      {importOpen ? (
        <div className="modal-overlay" role="presentation" onClick={() => setImportOpen(false)}>
          <div className="modal-content modal-lg" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div><h2>从线索导入客户</h2><p>只展示尚未转入 CRM 的线索，确认有效后会自动生成客户和首个提醒。</p></div>
              <button type="button" className="modal-close" onClick={() => setImportOpen(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="filter-grid crm-filter-grid">
                <label><span>搜索线索</span><input value={leadKeyword} onChange={(e) => setLeadKeyword(e.target.value)} placeholder="客户昵称、需求内容" /></label>
                <label><span>线索等级</span><select value={leadLevel} onChange={(e) => setLeadLevel(e.target.value)}>{LEVEL_OPTIONS.map((option) => <option key={option || "lead-all"} value={option}>{option || "全部等级"}</option>)}</select></label>
              </div>
              <div className="crm-filter-actions">
                <button type="button" className="btn-primary" onClick={() => void loadImportLeads()} disabled={leadLoading}>{leadLoading ? "加载中..." : "查询线索"}</button>
              </div>
              {leadError ? <p className="inline-error">{leadError}</p> : null}
              <div className="crm-import-list">
                {leads.length === 0 && !leadLoading ? <div className="state-panel state-empty"><p>暂无可导入线索。</p></div> : null}
                {leads.map((lead) => (
                  <div key={lead.id} className="crm-import-item">
                    <div>
                      <strong>{lead.user_name || `线索 ${lead.id}`}</strong>
                      <p>{compactText(lead.content, "暂无线索内容")}</p>
                      <div className="crm-customer-meta">
                        <span>{lead.lead_level} 级</span>
                        <span>{PLATFORM_LABELS[lead.platform] || lead.platform}</span>
                        <span>{compactText(lead.demand_type, "未识别需求")}</span>
                      </div>
                    </div>
                    <button type="button" className="btn-primary" onClick={() => void handleConvertLead(lead)} disabled={convertingId === lead.id}>{convertingId === lead.id ? "导入中..." : "导入客户"}</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
