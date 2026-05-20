import { CloseOutlined, LinkOutlined, RightOutlined, TeamOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, Divider, Drawer, Input, Progress, Select, Space, Spin, Tag, Typography, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { convertLeadToCrm, getPost, updateLeadStatus, type Lead, type Post } from "../../api";

const { Text, Paragraph } = Typography;

const PLATFORM_LABELS: Record<string, string> = { xhs: "小红书", douyin: "抖音", zhihu: "知乎" };
const STATUS_LABELS: Record<string, string> = { new: "新线索", contacted: "已跟进", interested: "有意向", invalid: "无效", converted: "已转化" };
const STATUS_OPTIONS = [
  { value: "new", label: "新线索" },
  { value: "contacted", label: "已跟进" },
  { value: "interested", label: "有意向" },
  { value: "invalid", label: "无效" },
  { value: "converted", label: "已转化" },
];
const LEVEL_COLORS: Record<string, string> = { A: "red", B: "blue", C: "orange", D: "default" };

const RISK_CONFIG: Record<string, { bg: string; border: string; color: string }> = {
  A: { bg: "#FFF1F0", border: "#FFCCC7", color: "#CF1322" },
  B: { bg: "#E6F7FF", border: "#91D5FF", color: "#0958D9" },
  C: { bg: "#FFFBE6", border: "#FFE58F", color: "#D48806" },
  D: { bg: "#F5F5F5", border: "#D9D9D9", color: "#8C8C8C" },
};

function RiskBadge({ level }: { level: string }) {
  const cfg = RISK_CONFIG[level] || RISK_CONFIG.D;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      minWidth: 36, height: 26, borderRadius: 4, padding: "0 8px",
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      fontSize: 14, fontWeight: 700, color: cfg.color,
    }}>
      {level}级
    </span>
  );
}
const DIMENSION_LABELS: Record<string, string> = {
  demand_clarity: "需求明确度", urgency: "紧迫程度", qualification: "资质条件",
  product_match: "产品匹配", weak_intent: "弱意向信号", amount: "金额信息",
  authenticity: "真实性", risk_penalty: "风险扣分",
};

function getMatchedWords(evidence: Lead["evidence"]): string[] {
  if (!evidence || typeof evidence !== "object") return [];
  const words = (evidence as Record<string, unknown>).matched_words;
  return Array.isArray(words) ? words : [];
}

function getAmounts(evidence: Lead["evidence"]): string[] {
  if (!evidence || typeof evidence !== "object") return [];
  const amounts = (evidence as Record<string, unknown>).amounts;
  return Array.isArray(amounts) ? amounts : [];
}

function getScoreBreakdown(evidence: Lead["evidence"]): Record<string, number> | null {
  if (!evidence || typeof evidence !== "object") return null;
  const sb = (evidence as Record<string, unknown>).score_breakdown;
  return sb && typeof sb === "object" ? (sb as Record<string, number>) : null;
}

function getNegationInfo(evidence: Lead["evidence"]): { detected: boolean; words?: string[] } {
  if (!evidence || typeof evidence !== "object") return { detected: false };
  const typed = evidence as Record<string, unknown>;
  return {
    detected: !!typed.negation_detected,
    words: Array.isArray(typed.negation_words) ? typed.negation_words as string[] : undefined,
  };
}

function getRiskKeywords(evidence: Lead["evidence"]): string[] {
  if (!evidence || typeof evidence !== "object") return [];
  const typed = evidence as Record<string, unknown>;
  const kws = typed.risk_keywords_matched || typed.negative_keywords_matched;
  return Array.isArray(kws) ? kws : [];
}

type Props = {
  open: boolean;
  lead: Lead | null;
  onClose: () => void;
  onUpdated: () => void;
};

export default function LeadDetailDrawer({ open, lead, onClose, onUpdated }: Props) {
  const [draftStatus, setDraftStatus] = useState<string>(lead?.status ?? "new");
  const [draftNotes, setDraftNotes] = useState<string>(lead?.notes ?? "");
  const [busy, setBusy] = useState(false);
  const [converting, setConverting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (lead) {
      setDraftStatus(lead.status);
      setDraftNotes(lead.notes ?? "");
    }
  }, [lead]);

  if (!lead) return null;

  const matchedWords = getMatchedWords(lead.evidence);
  const amounts = getAmounts(lead.evidence);
  const breakdown = getScoreBreakdown(lead.evidence);
  const negation = getNegationInfo(lead.evidence);
  const riskKws = getRiskKeywords(lead.evidence);
  const hasChanges = draftStatus !== lead.status || draftNotes !== (lead.notes ?? "");

  const [sourcePost, setSourcePost] = useState<Post | null>(null);
  const [postLoading, setPostLoading] = useState(false);

  useEffect(() => {
    if (lead?.source_post_id) {
      setPostLoading(true);
      getPost(lead.source_post_id)
        .then((post) => setSourcePost(post))
        .catch(() => setSourcePost(null))
        .finally(() => setPostLoading(false));
    } else {
      setSourcePost(null);
    }
  }, [lead?.source_post_id]);

  async function handleSaveStatus() {
    if (!hasChanges || !lead) return;
    setBusy(true);
    try {
      await updateLeadStatus(lead.id, draftStatus, draftNotes || null);
      message.success(`线索 #${lead.id} 已更新为${STATUS_LABELS[draftStatus] || draftStatus}`);
      onUpdated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "更新失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleConvertToCrm() {
    if (!lead) return;
    setConverting(true);
    try {
      await convertLeadToCrm(lead.id);
      message.success("已转入 CRM，可在 CRM 跟进台查看");
      onUpdated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "转入 CRM 失败");
    } finally {
      setConverting(false);
    }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={560}
      title={
        <Space>
          <RiskBadge level={lead.lead_level} />
          <span>线索 #{lead.id}</span>
        </Space>
      }
      extra={
        <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <Space size={8} style={{ marginBottom: 8 }}>
            <Tag color="blue">{PLATFORM_LABELS[lead.platform] || lead.platform}</Tag>
            <Tag>{lead.source_type}</Tag>
            {lead.demand_type && <Tag color="purple">{lead.demand_type}</Tag>}
            {lead.risk_level && <Tag color="orange">{lead.risk_level}</Tag>}
          </Space>
          <div style={{ marginBottom: 4 }}>
            <Text strong>{lead.user_name || "匿名用户"}</Text>
            {lead.user_profile_url && (
              <a href={lead.user_profile_url} target="_blank" rel="noreferrer" style={{ marginLeft: 8, fontSize: 12 }}>
                主页 <RightOutlined style={{ fontSize: 10 }} />
              </a>
            )}
          </div>
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>评分</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
            <Progress
              percent={Math.min(100, lead.lead_score)}
              size="small"
              strokeColor={lead.lead_score >= 70 ? "#cf1322" : lead.lead_score >= 40 ? "#faad14" : "#1677ff"}
              style={{ flex: 1 }}
            />
            <Text strong style={{ fontSize: 18 }}>{lead.lead_score}</Text>
          </div>
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>内容</Text>
          <div style={{ background: "#fafafa", padding: 12, borderRadius: 8, marginTop: 4 }}>
            <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap" }}>{lead.content || "-"}</Paragraph>
          </div>
        </div>

        {lead.follow_up_script && (
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>推荐话术</Text>
            <div style={{ background: "#e6f4ff", padding: 12, borderRadius: 8, marginTop: 4, border: "1px solid #91caff" }}>
              <Paragraph style={{ margin: 0, color: "#1677ff" }}>{lead.follow_up_script}</Paragraph>
            </div>
          </div>
        )}

        {lead.reason && (
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>判定理由</Text>
            <Paragraph style={{ marginTop: 4, color: "#595959" }}>{lead.reason}</Paragraph>
          </div>
        )}

        {(matchedWords.length > 0 || amounts.length > 0 || negation.detected || riskKws.length > 0) && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>证据链</Text>
            {matchedWords.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>命中关键词：</Text>
                <div style={{ marginTop: 4 }}>{matchedWords.map((w) => <Tag key={w} color="gold">{w}</Tag>)}</div>
              </div>
            )}
            {amounts.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>金额信息：</Text>
                <div style={{ marginTop: 4 }}>{amounts.map((a) => <Tag key={a} color="blue">{a}</Tag>)}</div>
              </div>
            )}
            {negation.detected && (
              <div style={{ marginBottom: 8 }}>
                <Tag color="warning">⚠️ 否定词检测{negation.words?.length ? `：${negation.words.join("、")}` : ""}</Tag>
              </div>
            )}
            {riskKws.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>风险关键词：</Text>
                <div style={{ marginTop: 4 }}>{riskKws.map((k) => <Tag key={k} color="error">{k}</Tag>)}</div>
              </div>
            )}
          </div>
        )}

        {breakdown && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>评分拆解</Text>
            {Object.entries(breakdown).map(([key, val]) => (
              <div key={key} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>{DIMENSION_LABELS[key] || key}</Text>
                <Text style={{ fontSize: 12, color: val > 0 ? "#52c41a" : val < 0 ? "#ff4d4f" : "#8c8c8c" }}>
                  {val > 0 ? "+" : ""}{val}
                </Text>
              </div>
            ))}
          </div>
        )}

        {lead.is_duplicate && (
          <div style={{ background: "#fffbe6", padding: 12, borderRadius: 8, border: "1px solid #ffe58f" }}>
            <Text style={{ color: "#ad6800" }}>⚠️ 重复线索</Text>
            {lead.duplicate_reason && <Text type="secondary" style={{ marginLeft: 8 }}>{lead.duplicate_reason}</Text>}
          </div>
        )}

        <Divider />

        <div>
          <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>状态更新</Text>
          <Space.Compact style={{ width: "100%", marginBottom: 8 }}>
            <Select
              value={draftStatus}
              onChange={setDraftStatus}
              options={STATUS_OPTIONS}
              style={{ width: 160 }}
            />
            <Button type="primary" onClick={handleSaveStatus} loading={busy} disabled={!hasChanges}>
              保存
            </Button>
          </Space.Compact>
          <Input.TextArea
            value={draftNotes}
            onChange={(e) => setDraftNotes(e.target.value)}
            placeholder="备注..."
            rows={2}
            style={{ marginTop: 8 }}
          />
        </div>

        {lead.status !== "converted" && (
          <Tag color="blue" style={{ alignSelf: "flex-start" }}>状态：{STATUS_LABELS[lead.status] || lead.status}</Tag>
        )}

        <div>
          {lead.crm_customer_id ? (
            <Button type="primary" icon={<TeamOutlined />} onClick={() => navigate("/crm")}>
              已转入 CRM，前往查看
            </Button>
          ) : (
            <Button type="primary" icon={<TeamOutlined />} onClick={handleConvertToCrm} loading={converting}>
              转入 CRM
            </Button>
          )}
        </div>

        <Descriptions column={2} size="small" style={{ marginTop: 8 }}>
          <Descriptions.Item label="创建时间">{dayjs(lead.created_at).format("YYYY-MM-DD HH:mm")}</Descriptions.Item>
        </Descriptions>

        {lead.source_post_id && (
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>来源帖子</Text>
            {postLoading ? (
              <div style={{ textAlign: "center", padding: 16 }}><Spin size="small" /></div>
            ) : sourcePost ? (
              <Card
                size="small"
                style={{ borderRadius: 8, background: "#fafafa" }}
                bodyStyle={{ padding: 12 }}
              >
                <div style={{ marginBottom: 8 }}>
                  <Text strong style={{ fontSize: 14 }}>{sourcePost.title || "无标题"}</Text>
                </div>
                {sourcePost.content && (
                  <Paragraph
                    ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
                    style={{ margin: "0 0 8px", color: "#595959", fontSize: 13 }}
                  >
                    {sourcePost.content}
                  </Paragraph>
                )}
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
                  {sourcePost.author_name && <Text type="secondary" style={{ fontSize: 12 }}>作者：{sourcePost.author_name}</Text>}
                  {sourcePost.like_count > 0 && <Text type="secondary" style={{ fontSize: 12 }}>点赞 {sourcePost.like_count}</Text>}
                  {sourcePost.comment_count > 0 && <Text type="secondary" style={{ fontSize: 12 }}>评论 {sourcePost.comment_count}</Text>}
                  {sourcePost.collect_count > 0 && <Text type="secondary" style={{ fontSize: 12 }}>收藏 {sourcePost.collect_count}</Text>}
                  {sourcePost.is_hot && <Tag color="red" style={{ margin: 0, fontSize: 11 }}>爆款</Tag>}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {sourcePost.post_url && (
                    <a href={sourcePost.post_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                      <LinkOutlined /> 查看原文
                    </a>
                  )}
                  <a onClick={() => navigate(`/posts?highlight=${sourcePost.id}`)} style={{ fontSize: 12, cursor: "pointer" }}>
                    <RightOutlined /> 帖子详情
                  </a>
                </div>
              </Card>
            ) : (
              <Text type="secondary" style={{ fontSize: 12 }}>帖子信息不可用</Text>
            )}
          </div>
        )}
      </div>
    </Drawer>
  );
}
