import { EditOutlined, PlayCircleOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Row,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";

import {
  getScoringRules,
  testScoring,
  updateScoringRules,
  type ScoringDimension,
  type ScoringRules,
  type ScoringTestResult,
} from "../api";

const { Title, Text, Paragraph } = Typography;

const DIMENSION_LABELS: Record<string, string> = {
  demand_clarity: "需求明确度",
  urgency: "紧迫程度",
  qualification: "资质条件",
  product_match: "产品匹配",
  weak_intent: "弱意向信号",
  amount: "金额信息",
  authenticity: "真实性",
  risk_penalty: "风险扣分",
};

const LEVEL_COLORS: Record<string, string> = { A: "red", B: "orange", C: "gold", D: "default" };

const SAMPLE_TEXTS = [
  "急需贷款5万，征信花怎么办",
  "我不要贷款，已经还清了",
  "黑户包装百分百下款",
  "想了解一下信用贷的利息",
  "负债太高了，还能办贷款吗",
  "广告位招租，同行加微",
];

export default function ScoringRulesPage() {
  const [rules, setRules] = useState<ScoringRules | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testText, setTestText] = useState("");
  const [testResult, setTestResult] = useState<ScoringTestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [editDraft, setEditDraft] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [error, setError] = useState("");

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getScoringRules();
      setRules(res);
      setEditDraft(JSON.stringify(res, null, 2));
    } catch {
      setError("加载评分规则失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  async function handleTest() {
    if (!testText.trim()) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await testScoring(testText);
      setTestResult(res);
    } catch {
      message.error("评分测试失败");
    } finally {
      setTestLoading(false);
    }
  }

  async function handleSave() {
    try {
      const parsed = JSON.parse(editDraft) as ScoringRules;
      setSaving(true);
      const res = await updateScoringRules(parsed);
      setRules(res);
      setEditDraft(JSON.stringify(res, null, 2));
      setEditMode(false);
      setError("");
      message.success("评分规则已保存");
    } catch (e) {
      if (e instanceof SyntaxError) {
        message.error("JSON 格式错误，请检查");
      } else {
        message.error("保存失败");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!rules) {
    return (
      <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 20px 48px" }}>
        <Alert type="error" message="无法加载评分规则" />
      </div>
    );
  }

  const dimensionColumns = [
    {
      title: "维度", dataIndex: "name", width: 140,
      render: (name: string, dim: ScoringDimension) => dim.description || DIMENSION_LABELS[name] || name,
    },
    { title: "权重", dataIndex: "weight", width: 80 },
    { title: "每词分值", dataIndex: "score_per_hit", width: 100 },
    { title: "上限", dataIndex: "max_score", width: 80 },
    { title: "关键词数", dataIndex: "patterns", width: 100, render: (p: string[]) => p?.length ?? 0 },
  ];

  const testBreakdownColumns = [
    {
      title: "维度", dataIndex: "key", width: 140,
      render: (key: string) => DIMENSION_LABELS[key] || key,
    },
    {
      title: "分值", dataIndex: "value", width: 100,
      render: (value: number) => (
        <Text strong style={{ color: value > 0 ? "#52c41a" : value < 0 ? "#ff4d4f" : "#8c8c8c" }}>
          {value > 0 ? `+${value}` : value}
        </Text>
      ),
    },
  ];

  function getTestEvidence() {
    if (!testResult?.evidence || typeof testResult.evidence !== "object") return null;
    return testResult.evidence as Record<string, unknown>;
  }

  const evidence = getTestEvidence();

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "24px 20px 48px" }}>
      <div style={{ marginBottom: 20 }}>
        <Text type="secondary" style={{ fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}>评分规则</Text>
        <Title level={2} style={{ margin: "4px 0 8px" }}>评分规则管理</Title>
        <Paragraph type="secondary">管理线索评分维度、阈值和关键词规则，支持在线测试。</Paragraph>
      </div>

      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} closable onClose={() => setError("")} />}

      <Row gutter={24}>
        <Col xs={24} lg={14}>
          <Card
            title={`规则概览（v${rules.version}）`}
            size="small"
            extra={
              <Space>
                <Button icon={<ReloadOutlined />} onClick={() => fetchRules()}>刷新</Button>
                <Button
                  type={editMode ? "default" : "primary"}
                  icon={<EditOutlined />}
                  onClick={() => setEditMode(!editMode)}
                >
                  {editMode ? "取消编辑" : "编辑规则"}
                </Button>
              </Space>
            }
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <Text strong style={{ marginBottom: 8, display: "block" }}>评分维度</Text>
                <Table
                  dataSource={rules.dimensions}
                  columns={dimensionColumns}
                  rowKey="name"
                  size="small"
                  scroll={{ x: 600 }}
                  pagination={false}
                />
              </div>

              <div>
                <Text strong style={{ marginBottom: 8, display: "block" }}>线索等级阈值</Text>
                <Space size={12}>
                  {Object.entries(rules.lead_level_thresholds).map(([level, threshold]) => (
                    <Tag key={level} color={LEVEL_COLORS[level] || "default"} style={{ fontSize: 14, padding: "4px 16px" }}>
                      {level}级 ≥ {threshold}分
                    </Tag>
                  ))}
                </Space>
              </div>

              <div>
                <Text strong style={{ marginBottom: 8, display: "block" }}>否定词模式</Text>
                <Space size={[6, 6]} wrap>
                  {rules.negation_patterns.map((p) => <Tag key={p} color="error">{p}</Tag>)}
                </Space>
              </div>

              <div>
                <Text strong style={{ marginBottom: 8, display: "block" }}>风险关键词</Text>
                <Space size={[6, 6]} wrap>
                  {rules.risk_keywords.map((kw) => <Tag key={kw} color="volcano">{kw}</Tag>)}
                </Space>
              </div>

              <div>
                <Text strong style={{ marginBottom: 8, display: "block" }}>负面模式</Text>
                <Space size={[6, 6]} wrap>
                  {rules.negative_patterns.map((p) => <Tag key={p} color="warning">{p}</Tag>)}
                </Space>
              </div>

              <div>
                <Text strong style={{ marginBottom: 8, display: "block" }}>需求类型规则</Text>
                {rules.demand_type_rules.map((rule, i) => (
                  <div key={i} style={{ marginBottom: 6 }}>
                    <Tag color="purple">{rule.type}</Tag>
                    <Text type="secondary">{rule.keywords.join("、")}</Text>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {editMode && (
            <Card title="编辑规则 JSON" size="small" style={{ marginTop: 16 }}>
              <Input.TextArea
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                rows={20}
                style={{ fontFamily: "monospace", fontSize: 13 }}
              />
              <div style={{ marginTop: 8, textAlign: "right" }}>
                <Space>
                  <Button onClick={() => setEditDraft(JSON.stringify(rules, null, 2))}>重置</Button>
                  <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>保存规则</Button>
                </Space>
              </div>
            </Card>
          )}
        </Col>

        <Col xs={24} lg={10}>
          <Card title="评分测试" size="small">
            <Input.TextArea
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              placeholder="输入待评分文本，如：急需贷款5万，征信花怎么办"
              rows={3}
              style={{ marginBottom: 12 }}
            />
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleTest}
              loading={testLoading}
              disabled={!testText.trim()}
              block
            >
              评分
            </Button>

            {testResult && (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 16 }}>
                  <Tag color={LEVEL_COLORS[testResult.lead_level] || "default"} style={{ fontSize: 24, padding: "8px 20px" }}>
                    {testResult.lead_level}级
                  </Tag>
                  <div>
                    <div style={{ fontSize: 20, fontWeight: "bold" }}>{testResult.lead_score}分</div>
                    <Text type="secondary">{testResult.demand_type}</Text>
                  </div>
                  <Tag color={
                    testResult.risk_level === "low" ? "green" :
                    testResult.risk_level === "medium" ? "warning" : "red"
                  }>
                    风险: {testResult.risk_level}
                  </Tag>
                </div>

                <Descriptions column={1} size="small" bordered>
                  <Descriptions.Item label="评分理由">{testResult.reason}</Descriptions.Item>
                  {testResult.follow_up_script && (
                    <Descriptions.Item label="建议话术">
                      <Text style={{ color: "#1677ff" }}>{testResult.follow_up_script}</Text>
                    </Descriptions.Item>
                  )}
                </Descriptions>

                {evidence && (
                  <div style={{ marginTop: 12 }}>
                    <Text strong style={{ marginBottom: 8, display: "block" }}>评分拆解</Text>
                    <Table
                      dataSource={
                        Object.entries((evidence.score_breakdown as Record<string, number>) || {}).map(([key, value]) => ({ key, value }))
                      }
                      columns={testBreakdownColumns}
                      rowKey="key"
                      size="small"
                      scroll={{ x: 400 }}
                      pagination={false}
                    />

                    {Array.isArray(evidence.matched_words) && evidence.matched_words.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>命中关键词：</Text>
                        <div style={{ marginTop: 4 }}>
                          <Space size={[6, 6]} wrap>
                            {(evidence.matched_words as string[]).map((w) => <Tag key={w} color="gold">{w}</Tag>)}
                          </Space>
                        </div>
                      </div>
                    )}

                    {Array.isArray(evidence.amounts) && evidence.amounts.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>金额：</Text>
                        <Space size={[6, 6]} wrap>
                          {(evidence.amounts as string[]).map((a) => <Tag key={a} color="blue">{a}</Tag>)}
                        </Space>
                      </div>
                    )}

                    {Boolean(evidence.negation_detected) && (
                      <Alert
                        type="warning"
                        message="检测到否定词"
                        description={Array.isArray(evidence.negation_words) ? String((evidence.negation_words as string[]).join("、")) : ""}
                        style={{ marginTop: 8 }}
                        showIcon
                      />
                    )}
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card title="快速测试样例" size="small" style={{ marginTop: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {SAMPLE_TEXTS.map((sample) => (
                <Button
                  key={sample}
                  block
                  onClick={() => setTestText(sample)}
                  style={{ textAlign: "left", height: "auto", padding: "6px 12px", whiteSpace: "normal" }}
                >
                  {sample}
                </Button>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
