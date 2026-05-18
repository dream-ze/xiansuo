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
  customer_feedback: string;
  next_action: string;
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
  customer_feedback: "",
  next_action: "",
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

  const filteredItems = useMemo(() => {
    return level ? items.filter((item) => item.customer_level === level) : items;
  }, [items, level]);

  const stats = useMemo(() => {
    const pending = items.filter((item) => ["new", "following", "qualified"].includes(item.status)).length;
    const deals = items.filter((item) => item.status === "deal").length;
    const imported = items.filter((item) => item.source_lead_id).length;
    const highValue = items.filter((item) => (item.demand_amount || 0) >= 100000).length;
    return { pending, deals, imported, highValue };
  }, [items]);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "客户列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(customer: CrmCustomer | null) {
    if (!customer) {
      setFollowUps([]);
      setTasks([]);
      return;
    }
    setDetailLoading(true);
    try {
      const [nextFollowUps, nextTasks] = await Promise.all([
        getCrmFollowUps({ customer_id: customer.id, page: 1, page_size: 6 }),
        getCrmTasks({ customer_id: customer.id, status: "pending", page: 1, page_size: 6 }),
      ]);
      setFollowUps(nextFollowUps.items);
      setTasks(nextTasks.items);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadDetail(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  async function handleCreateFollowUp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    if (!followUpForm.content.trim() && !followUpForm.next_action.trim()) {
      showToast("error", "请填写跟进内容", "至少记录本次沟通或下一步动作");
      return;
    }

    setSavingFollowUp(true);
    try {
      await createCrmFollowUp({
        customer_id: selected.id,
        owner_name: selected.owner_name,
        follow_up_type: "manual",
        content: followUpForm.content.trim() || "记录客户跟进",
        customer_feedback: followUpForm.customer_feedback.trim() || null,
        next_action: followUpForm.next_action.trim() || null,
        next_follow_up_at: followUpForm.next_follow_up_at ? new Date(followUpForm.next_follow_up_at).toISOString() : null,
      });

      if (followUpForm.next_action.trim() || followUpForm.next_follow_up_at) {
        await createCrmTask({
          customer_id: selected.id,
          title: followUpForm.next_action.trim() || `继续跟进 ${selected.name}`,
          task_type: "follow_up",
          owner_name: selected.owner_name,
          due_at: followUpForm.next_follow_up_at ? new Date(followUpForm.next_follow_up_at).toISOString() : null,
          priority: selected.customer_level === "A" ? "high" : "normal",
          suggestion: "按客户反馈安排下一次沟通，优先确认需求金额、用途、资质和可接受方案。",
        });
      }

      setFollowUpForm(EMPTY_FOLLOW_UP_FORM);
      showToast("success", "跟进已记录", "提醒任务已同步更新");
      await loadDetail(selected);
    } catch (err) {
      showToast("error", "跟进保存失败", err instanceof Error ? err.message : "请稍后重试");
    } finally {
      setSavingFollowUp(false);
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

  return (
    <main className="page-shell crm-workbench">
      <header className="page-header crm-workbench-hero">
        <div>
          <p className="page-eyebrow">CRM Customer Workbench</p>
          <h1>客户管理</h1>
          <p className="page-description">统一管理手动录入和线索导入的客户，聚焦跟进、提醒和下一步动作。</p>
        </div>
        <div className="action-row">
          <button className="btn-secondary" type="button" onClick={() => { setImportOpen(true); void loadImportLeads(); }}>从线索导入</button>
          <button className="btn-primary" type="button" onClick={openCreateForm}>新增客户</button>
        </div>
      </header>

      <section className="crm-kpi-grid">
        <div className="crm-kpi-card"><span>客户总数</span><strong>{total}</strong><p>当前筛选范围内客户</p></div>
        <div className="crm-kpi-card"><span>待跟进</span><strong>{stats.pending}</strong><p>新客户、跟进中、已确认需求</p></div>
        <div className="crm-kpi-card"><span>线索导入</span><strong>{stats.imported}</strong><p>来自线索池的客户</p></div>
        <div className="crm-kpi-card"><span>高价值需求</span><strong>{stats.highValue}</strong><p>需求金额不低于 10 万</p></div>
      </section>

      <section className="card crm-filter-card">
        <div className="filter-grid crm-filter-grid">
          <label><span>搜索客户</span><input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="客户名、昵称" /></label>
          <label><span>负责人</span><input value={ownerName} onChange={(e) => setOwnerName(e.target.value)} placeholder="销售姓名" /></label>
          <label><span>客户状态</span><select value={status} onChange={(e) => setStatus(e.target.value)}>{STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label><span>客户等级</span><select value={level} onChange={(e) => setLevel(e.target.value)}>{LEVEL_OPTIONS.map((option) => <option key={option || "all"} value={option}>{option || "全部等级"}</option>)}</select></label>
        </div>
        <div className="crm-filter-actions">
          <p className="field-hint">提示：客户页默认隐藏采集任务、帖子 ID、评论 ID 和原始证据，只保留客户可理解的来源摘要。</p>
          <button type="button" className="btn-primary" onClick={() => void loadData()} disabled={loading}>{loading ? "查询中..." : "查询客户"}</button>
        </div>
      </section>

      {error ? <div className="state-panel state-error"><p>{error}</p></div> : null}

      <div className="crm-workbench-grid">
        <section className="card crm-customer-list">
          <div className="card-header card-header-row">
            <div>
              <h2>客户列表</h2>
              <p>点击客户查看资料、跟进记录和提醒任务。</p>
            </div>
            <span className="crm-count">{filteredItems.length} 位客户</span>
          </div>

          {loading ? <p className="state-text">客户加载中...</p> : null}
          {!loading && filteredItems.length === 0 ? (
            <div className="state-panel state-empty">
              <p>还没有符合条件的客户。可以先新增客户，或从线索池导入已确认有效的线索。</p>
            </div>
          ) : null}

          <div className="crm-customer-stack">
            {filteredItems.map((item) => (
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
                  <span className={`status-pill status-${item.status}`}>{getStatusLabel(item.status)}</span>
                </div>
                <div className="crm-customer-meta">
                  <span>{item.customer_level ? `${item.customer_level} 级` : "未评级"}</span>
                  <span>{formatMoney(item.demand_amount)}</span>
                  <span>{compactText(item.owner_name, "未分配")}</span>
                  <span>{item.source_lead_id ? "线索导入" : "手动录入"}</span>
                </div>
              </button>
            ))}
          </div>
        </section>

        <aside className="card crm-detail-panel">
          {activeCustomer ? (
            <>
              <div className="crm-detail-header">
                <div>
                  <p className="page-eyebrow">Customer Profile</p>
                  <h2>{activeCustomer.name}</h2>
                  <p>{activeCustomer.source_lead_id ? "由线索导入，已转入 CRM 跟进" : "手动录入客户"}</p>
                </div>
                <button type="button" className="btn-secondary" onClick={() => openEditForm(activeCustomer)}>编辑资料</button>
              </div>

              <div className="crm-guidance">
                <strong>操作提示</strong>
                <p>先确认客户联系方式、需求金额和用途；沟通后在下方记录跟进，并设置下次提醒。</p>
              </div>

              <section className="drawer-section">
                <h4 className="drawer-section-title">基础资料</h4>
                <div className="detail-grid compact">
                  <div className="detail-field"><span className="detail-label">电话</span><strong className="detail-value">{compactText(activeCustomer.phone)}</strong></div>
                  <div className="detail-field"><span className="detail-label">其他联系方式</span><strong className="detail-value">{compactText(activeCustomer.contact_info)}</strong></div>
                  <div className="detail-field"><span className="detail-label">负责人</span><strong className="detail-value">{compactText(activeCustomer.owner_name, "未分配")}</strong></div>
                  <div className="detail-field"><span className="detail-label">需求金额</span><strong className="detail-value">{formatMoney(activeCustomer.demand_amount)}</strong></div>
                  <div className="detail-field"><span className="detail-label">客户等级</span><strong className="detail-value">{compactText(activeCustomer.customer_level, "未评级")}</strong></div>
                  <div className="detail-field"><span className="detail-label">风险等级</span><strong className="detail-value">{compactText(activeCustomer.risk_level, "未评估")}</strong></div>
                </div>
              </section>

              <section className="drawer-section">
                <h4 className="drawer-section-title">来源与需求</h4>
                <div className="crm-source-box">
                  <div><span>来源</span><strong>{activeCustomer.source_platform ? PLATFORM_LABELS[activeCustomer.source_platform] || activeCustomer.source_platform : "手动录入"}</strong></div>
                  <div><span>客户诉求</span><p>{compactText(activeCustomer.source_summary || activeCustomer.loan_purpose, "暂无来源摘要")}</p></div>
                  <div><span>资质摘要</span><p>{compactText(activeCustomer.qualification_summary, "暂未补充资质信息")}</p></div>
                </div>
              </section>

              <section className="drawer-section">
                <h4 className="drawer-section-title">跟进与提醒</h4>
                {detailLoading ? <p className="state-text">跟进信息加载中...</p> : null}
                <div className="crm-task-list">
                  {tasks.length === 0 ? <p className="field-hint">暂无待办提醒。记录下一步动作后会自动创建提醒。</p> : null}
                  {tasks.map((task) => (
                    <div key={task.id} className={task.is_overdue ? "crm-task-item overdue" : "crm-task-item"}>
                      <strong>{task.title}</strong>
                      <span>{task.due_at ? formatDateTime(task.due_at) : "未设置时间"}</span>
                    </div>
                  ))}
                </div>

                <form className="crm-follow-form" onSubmit={(event) => void handleCreateFollowUp(event)}>
                  <label><span>本次跟进记录</span><textarea className="text-area" value={followUpForm.content} onChange={(e) => setFollowUpForm((current) => ({ ...current, content: e.target.value }))} placeholder="记录沟通内容，例如：客户确认需要 30 万经营周转，明天补充流水。" /></label>
                  <label><span>客户反馈</span><input value={followUpForm.customer_feedback} onChange={(e) => setFollowUpForm((current) => ({ ...current, customer_feedback: e.target.value }))} placeholder="客户目前最关心的问题" /></label>
                  <div className="form-grid">
                    <label><span>下一步动作</span><input value={followUpForm.next_action} onChange={(e) => setFollowUpForm((current) => ({ ...current, next_action: e.target.value }))} placeholder="例如：明天电话确认资料" /></label>
                    <label><span>提醒时间</span><input type="datetime-local" value={followUpForm.next_follow_up_at} onChange={(e) => setFollowUpForm((current) => ({ ...current, next_follow_up_at: e.target.value }))} /></label>
                  </div>
                  <div className="form-actions"><button type="submit" className="btn-primary" disabled={savingFollowUp}>{savingFollowUp ? "保存中..." : "记录跟进并提醒"}</button></div>
                </form>

                <div className="crm-follow-history">
                  <h5>最近跟进</h5>
                  {followUps.length === 0 ? <p className="field-hint">暂无跟进记录。</p> : null}
                  {followUps.map((item) => (
                    <div key={item.id} className="crm-follow-item">
                      <strong>{item.content}</strong>
                      <p>{item.next_action || item.customer_feedback || "暂无下一步"}</p>
                      <span>{formatDateTime(item.created_at)}</span>
                    </div>
                  ))}
                </div>
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
              <div><h2>从线索导入客户</h2><p>只展示尚未转入 CRM 的线索，确认有效后会自动生成客户、商机和首个提醒。</p></div>
              <button type="button" className="modal-close" onClick={() => setImportOpen(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="filter-grid crm-filter-grid">
                <label><span>搜索线索</span><input value={leadKeyword} onChange={(e) => setLeadKeyword(e.target.value)} placeholder="客户昵称、需求内容" /></label>
                <label><span>线索等级</span><select value={leadLevel} onChange={(e) => setLeadLevel(e.target.value)}>{LEVEL_OPTIONS.map((option) => <option key={option || "lead-all"} value={option}>{option || "全部等级"}</option>)}</select></label>
              </div>
              <div className="crm-filter-actions">
                <p className="field-hint">建议优先导入 A/B 级、需求明确、风险可控的线索。</p>
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
                        <span>{lead.lead_score} 分</span>
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
