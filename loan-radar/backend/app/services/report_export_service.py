import json
from datetime import date

from app.models.daily_report import DailyReport

_PLATFORM_LABELS = {
    "all": "全平台",
    "xhs": "小红书",
    "douyin": "抖音",
    "zhihu": "知乎",
}


def _parse_json_field(value) -> dict | list | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    return value


def _normalize_rank_items(value) -> list[dict]:
    parsed = _parse_json_field(value)
    if not parsed or not isinstance(parsed, list):
        return []
    results = []
    for item in parsed:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            results.append({"name": str(item[0] or ""), "count": int(item[1] or 0)})
        elif isinstance(item, dict):
            name = item.get("demand_type") or item.get("name", "")
            count = item.get("count", 0)
            if name is not None:
                results.append({"name": str(name), "count": int(count)})
    return results


def _normalize_keyword_items(value) -> list[dict]:
    parsed = _parse_json_field(value)
    if not parsed or not isinstance(parsed, list):
        return []
    results = []
    for item in parsed:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            results.append({"word": str(item[0] or ""), "count": int(item[1] or 0)})
        elif isinstance(item, dict):
            word = item.get("keyword") or item.get("word", "")
            count = item.get("count", 0)
            if word is not None:
                results.append({"word": str(word), "count": int(count)})
    return results


def export_report_markdown(report: DailyReport) -> str:
    platform_label = _PLATFORM_LABELS.get(report.platform, report.platform)
    report_date = (
        report.report_date.isoformat()
        if isinstance(report.report_date, date)
        else str(report.report_date)
    )

    lines: list[str] = []

    lines.append(f"# 今日获客报告")
    lines.append("")
    lines.append(f"> 日期：{report_date}　|　平台：{platform_label}")
    lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 一、今日扫描概况")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 监控源 | {report.source_count} |")
    lines.append(f"| 帖子 | {report.post_count} |")
    lines.append(f"| 评论 | {report.comment_count} |")
    lines.append(f"| 线索 | {report.lead_count} |")
    lines.append(f"| A级线索 | **{report.a_lead_count}** |")
    lines.append(f"| B级线索 | {report.b_lead_count} |")
    lines.append(f"| C级线索 | {report.c_lead_count} |")
    lines.append(f"| D级线索 | {report.d_lead_count} |")
    lines.append("")

    a_lead_details = _parse_json_field(report.a_lead_details) or []
    lines.append("## 二、A级线索 Top 10")
    lines.append("")
    if not a_lead_details:
        lines.append("*今日暂无A级线索*")
        lines.append("")
    else:
        for i, lead in enumerate(a_lead_details[:10], 1):
            p = _PLATFORM_LABELS.get(lead.get("platform", ""), lead.get("platform", ""))
            user = lead.get("user_name") or "匿名用户"
            content = lead.get("content", "")
            demand = lead.get("demand_type", "")
            score = lead.get("lead_score", "")
            reason = lead.get("reason", "")
            script = lead.get("follow_up_script", "")

            lines.append(f"### {i}. [{p}] {user}")
            lines.append("")
            lines.append(f"- **评分**：{score}")
            if demand:
                lines.append(f"- **需求类型**：{demand}")
            lines.append(f"- **评论内容**：{content}")
            if reason:
                lines.append(f"- **判断理由**：{reason}")
            if script:
                lines.append(f"- **建议话术**：{script}")
            lines.append("")

    typical_evidence = _parse_json_field(report.typical_evidence) or []
    top_demands = _normalize_rank_items(report.top_demands)
    top_keywords = _normalize_keyword_items(report.top_keywords)

    lines.append("## 三、典型需求证据")
    lines.append("")
    if not typical_evidence and not top_demands:
        lines.append("*今日暂无需求证据*")
        lines.append("")
    else:
        if typical_evidence:
            for i, ev in enumerate(typical_evidence, 1):
                p = _PLATFORM_LABELS.get(ev.get("platform", ""), ev.get("platform", ""))
                level = ev.get("lead_level", "")
                content = ev.get("content", "")
                matched = ev.get("matched_words", [])
                amounts = ev.get("amounts", [])

                lines.append(f"### 证据 {i}　[{p}] {level}级")
                lines.append("")
                lines.append(f"> {content}")
                lines.append("")
                if matched:
                    lines.append(f"- **命中关键词**：{'、'.join(matched)}")
                if amounts:
                    lines.append(f"- **金额信息**：{'、'.join(amounts)}")
                lines.append("")

        if top_demands:
            lines.append("### 高频需求")
            lines.append("")
            lines.append("| 需求类型 | 次数 |")
            lines.append("|----------|------|")
            for d in top_demands:
                lines.append(f"| {d['name']} | {d['count']} |")
            lines.append("")

        if top_keywords:
            lines.append("### 高频关键词")
            lines.append("")
            kw_text = "、".join(f"{k['word']}({k['count']})" for k in top_keywords)
            lines.append(kw_text)
            lines.append("")

    discovered_competitors = _parse_json_field(report.discovered_competitors) or []
    lines.append("## 四、同行账号发现")
    lines.append("")
    if not discovered_competitors:
        lines.append("*今日暂无同行账号发现*")
        lines.append("")
    else:
        lines.append("| # | 账号名 | 平台 | 发现原因 | 建议 |")
        lines.append("|---|--------|------|----------|------|")
        for i, comp in enumerate(discovered_competitors, 1):
            p = _PLATFORM_LABELS.get(comp.get("platform", ""), comp.get("platform", ""))
            name = comp.get("account_name", "")
            reason = comp.get("discover_reason", "")
            suggest = "建议监控" if comp.get("suggest_monitor") else "暂不监控"
            lines.append(f"| {i} | {name} | {p} | {reason} | {suggest} |")
        lines.append("")

    tomorrow_suggestions = _parse_json_field(report.tomorrow_suggestions)
    lines.append("## 五、明日采集建议")
    lines.append("")
    if not tomorrow_suggestions or not isinstance(tomorrow_suggestions, dict):
        lines.append("*暂无建议*")
        lines.append("")
    else:
        rec_kw = tomorrow_suggestions.get("recommended_keywords", [])
        comp_dirs = tomorrow_suggestions.get("competitor_directions", [])
        content_topics = tomorrow_suggestions.get("content_topics", [])
        follow_up_hints = tomorrow_suggestions.get("follow_up_hints", [])

        if rec_kw:
            lines.append(f"**推荐关键词**：{'、'.join(rec_kw)}")
            lines.append("")
        if comp_dirs:
            lines.append("**推荐同行方向**：")
            for d in comp_dirs:
                lines.append(f"- {d}")
            lines.append("")
        if content_topics:
            lines.append("**推荐内容选题**：")
            for t in content_topics:
                lines.append(f"- {t}")
            lines.append("")
        if follow_up_hints:
            lines.append("**跟进提示**：")
            for h in follow_up_hints:
                lines.append(f"- {h}")
            lines.append("")

    risk_warnings = _parse_json_field(report.risk_warnings) or []
    lines.append("## 六、合规提醒")
    lines.append("")
    if not risk_warnings:
        lines.append("*暂无提醒*")
        lines.append("")
    else:
        for w in risk_warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*报告由 loan-radar 自动生成 · {report_date}*")
    lines.append("")

    return "\n".join(lines)
