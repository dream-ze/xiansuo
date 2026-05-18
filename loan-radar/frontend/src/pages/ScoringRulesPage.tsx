import { useCallback, useEffect, useState } from "react";

import {
  getScoringRules,
  testScoring,
  updateScoringRules,
  type ScoringDimension,
  type ScoringRules,
  type ScoringTestResult,
} from "../api/client";

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

const LEVEL_COLORS: Record<string, string> = {
  A: "#e53e3e",
  B: "#dd6b20",
  C: "#d69e2e",
  D: "#718096",
};

export default function ScoringRulesPage() {
  const [rules, setRules] = useState<ScoringRules | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testText, setTestText] = useState("");
  const [testResult, setTestResult] = useState<ScoringTestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [editDraft, setEditDraft] = useState<string>("");
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

  const handleTest = async () => {
    if (!testText.trim()) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await testScoring(testText);
      setTestResult(res);
    } catch {
      setError("评分测试失败");
    } finally {
      setTestLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const parsed = JSON.parse(editDraft) as ScoringRules;
      setSaving(true);
      const res = await updateScoringRules(parsed);
      setRules(res);
      setEditDraft(JSON.stringify(res, null, 2));
      setEditMode(false);
      setError("");
    } catch (e) {
      setError(e instanceof SyntaxError ? "JSON 格式错误" : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="page-container"><p>加载中...</p></div>;
  if (!rules) return <div className="page-container"><p>无法加载评分规则</p></div>;

  return (
    <div className="page-container">
      <h2>评分规则管理</h2>

      {error && <div className="alert alert-error">{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div>
          <h3>规则概览 (v{rules.version})</h3>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>评分维度</h4>
            <table className="data-table">
              <thead>
                <tr>
                  <th>维度</th>
                  <th>权重</th>
                  <th>每词分值</th>
                  <th>上限</th>
                  <th>关键词数</th>
                </tr>
              </thead>
              <tbody>
                {rules.dimensions.map((dim: ScoringDimension) => (
                  <tr key={dim.name}>
                    <td>{dim.description || dim.name}</td>
                    <td>{dim.weight}</td>
                    <td>{dim.score_per_hit}</td>
                    <td>{dim.max_score}</td>
                    <td>{dim.patterns.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>线索等级阈值</h4>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {Object.entries(rules.lead_level_thresholds).map(([level, threshold]) => (
                <div key={level} style={{
                  padding: "8px 16px",
                  borderRadius: 8,
                  background: LEVEL_COLORS[level] || "#ccc",
                  color: "#fff",
                  fontWeight: "bold",
                }}>
                  {level}级 ≥ {threshold}分
                </div>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>否定词模式</h4>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {rules.negation_patterns.map((p) => (
                <span key={p} className="tag" style={{ background: "#fed7d7", color: "#c53030" }}>{p}</span>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>风险关键词</h4>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {rules.risk_keywords.map((kw) => (
                <span key={kw} className="tag" style={{ background: "#fed7d7", color: "#9b2c2c" }}>{kw}</span>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>负面模式</h4>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {rules.negative_patterns.map((p) => (
                <span key={p} className="tag" style={{ background: "#fefcbf", color: "#975a16" }}>{p}</span>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>需求类型规则</h4>
            {rules.demand_type_rules.map((rule, i) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <strong>{rule.type}</strong>：{rule.keywords.join("、")}
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn btn-primary"
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? "取消编辑" : "编辑规则"}
            </button>
          </div>

          {editMode && (
            <div style={{ marginTop: 16 }}>
              <textarea
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                style={{
                  width: "100%",
                  minHeight: 400,
                  fontFamily: "monospace",
                  fontSize: 13,
                  padding: 12,
                  border: "1px solid #ddd",
                  borderRadius: 6,
                }}
              />
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button
                  className="btn btn-primary"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? "保存中..." : "保存规则"}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => { setEditDraft(JSON.stringify(rules, null, 2)); }}
                >
                  重置
                </button>
              </div>
            </div>
          )}
        </div>

        <div>
          <h3>评分测试</h3>
          <div className="card">
            <div style={{ marginBottom: 12 }}>
              <textarea
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                placeholder="输入待评分文本，如：急需贷款5万，征信花怎么办"
                style={{
                  width: "100%",
                  minHeight: 80,
                  padding: 12,
                  border: "1px solid #ddd",
                  borderRadius: 6,
                  fontSize: 14,
                }}
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={handleTest}
              disabled={testLoading || !testText.trim()}
            >
              {testLoading ? "评分中..." : "评分"}
            </button>

            {testResult && (
              <div style={{ marginTop: 16 }}>
                <div style={{
                  display: "flex",
                  gap: 16,
                  alignItems: "center",
                  marginBottom: 16,
                }}>
                  <div style={{
                    padding: "12px 24px",
                    borderRadius: 12,
                    background: LEVEL_COLORS[testResult.lead_level] || "#ccc",
                    color: "#fff",
                    fontSize: 24,
                    fontWeight: "bold",
                  }}>
                    {testResult.lead_level}
                  </div>
                  <div>
                    <div style={{ fontSize: 20, fontWeight: "bold" }}>{testResult.lead_score}分</div>
                    <div style={{ color: "#666" }}>{testResult.demand_type}</div>
                  </div>
                  <div style={{
                    padding: "4px 12px",
                    borderRadius: 4,
                    background: testResult.risk_level === "low" ? "#c6f6d5" :
                      testResult.risk_level === "medium" ? "#fefcbf" : "#fed7d7",
                    color: testResult.risk_level === "low" ? "#276749" :
                      testResult.risk_level === "medium" ? "#975a16" : "#c53030",
                    fontSize: 12,
                    fontWeight: "bold",
                  }}>
                    风险: {testResult.risk_level}
                  </div>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <strong>评分理由：</strong>{testResult.reason}
                </div>

                {testResult.follow_up_script && (
                  <div style={{ marginBottom: 12 }}>
                    <strong>建议话术：</strong>{testResult.follow_up_script}
                  </div>
                )}

                {testResult.evidence && (
                  <div>
                    <strong>评分拆解：</strong>
                    <table className="data-table" style={{ marginTop: 8 }}>
                      <thead>
                        <tr>
                          <th>维度</th>
                          <th>分值</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(
                          (testResult.evidence as Record<string, unknown>).score_breakdown as Record<string, number> || {}
                        ).map(([key, value]) => (
                          <tr key={key}>
                            <td>{DIMENSION_LABELS[key] || key}</td>
                            <td style={{
                              color: value < 0 ? "#c53030" : value > 0 ? "#276749" : "#666",
                              fontWeight: value !== 0 ? "bold" : "normal",
                            }}>
                              {value > 0 ? `+${value}` : value}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    {((testResult.evidence as Record<string, unknown>).matched_words as string[])?.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <strong>命中关键词：</strong>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                          {((testResult.evidence as Record<string, unknown>).matched_words as string[]).map((w) => (
                            <span key={w} className="tag">{w}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {((testResult.evidence as Record<string, unknown>).amounts as string[])?.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <strong>金额：</strong>{((testResult.evidence as Record<string, unknown>).amounts as string[]).join(", ")}
                      </div>
                    )}

                    {Boolean((testResult.evidence as Record<string, unknown>).negation_detected) && (
                      <div style={{ marginTop: 8, padding: "8px 12px", background: "#fefcbf", borderRadius: 4 }}>
                        ⚠️ 检测到否定词：{((testResult.evidence as Record<string, unknown>).negation_words as string[])?.join("、")}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h4>快速测试样例</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                "急需贷款5万，征信花怎么办",
                "我不要贷款，已经还清了",
                "黑户包装百分百下款",
                "想了解一下信用贷的利息",
                "负债太高了，还能办贷款吗",
                "广告位招租，同行加微",
              ].map((sample) => (
                <button
                  key={sample}
                  className="btn btn-secondary"
                  style={{ textAlign: "left", fontSize: 13 }}
                  onClick={() => { setTestText(sample); }}
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

