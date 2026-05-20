from collections import Counter
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.crm import CrmCustomer, CrmFollowRecord
from app.models.daily_report import DailyReport
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.pending_competitor import PendingCompetitorAccount
from app.models.post import Post

# 用于 top_keywords 的常见贷款需求关键词
_KEYWORD_LIST = [
    "征信花",
    "征信",
    "负债高",
    "负债",
    "网贷太多",
    "查询多",
    "公积金断",
    "房贷",
    "信用卡",
    "急用",
    "周转",
    "借款",
    "贷款",
    "下款",
    "信用贷",
    "房抵贷",
    "公积金",
    "企业",
    "网贷",
]

_CONTENT_SUGGESTION_TEMPLATES = {
    "借款需求": "今日借款需求活跃，建议发布「极速放款攻略」或「征信不好也能贷」类内容，直击痛点。",
    "资质焦虑": "今日资质焦虑评论较多，建议发布「征信花了如何提额」「负债高怎么办」类科普内容，获取信任。",
    "产品咨询": "今日产品咨询量高，建议发布各类贷款产品对比贴，引导用户主动咨询。",
    "弱意向": "今日弱意向用户多，建议发布「一分钟测额度」「利率计算器」等互动内容激活意向。",
}

_DEFAULT_CONTENT_SUGGESTION = "建议持续发布真实客户案例和产品说明内容，提升信任度和转化率。"

_FOLLOW_UP_TEMPLATES = {
    "high_a": "今日 A 级线索较多，建议优先在 1 小时内联系，询问资金用途和征信情况，直接推荐适配方案。",
    "has_a": "今日有 A 级线索，建议当天内完成初步沟通，了解借款需求和还款能力。",
    "has_b": "今日 B 级线索为主，建议发送产品介绍材料，引导填写测额问卷，筛选高质量客户。",
    "low": "今日线索量较少，建议优化监控关键词或增加监控源，扩大流量入口。",
}

_RISK_WARNINGS = [
    "跟进时请勿承诺下款，避免引发合规风险和客户投诉。",
    "请勿夸大利率优势或隐瞒实际费率，确保信息真实透明。",
    "请勿诱导用户增加负债，应基于实际需求推荐合理方案。",
    "建议使用「咨询」「评估」「方案匹配」类话术，避免「包下款」「零门槛」等违规表述。",
    "私信跟进时请勿索取身份证、银行卡等敏感信息，应引导至正规渠道申请。",
    "已识别为广告/同行的评论请勿跟进，避免浪费资源。",
    "请确保所有贷款产品宣传内容符合当地金融监管要求。",
]


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _filter_today(query, model_created_at):
    today = _today_utc()
    return query.filter(func.date(model_created_at) == today)


def _build_top_demands(leads: list) -> list[dict]:
    counter: Counter = Counter()
    for lead in leads:
        if lead.demand_type:
            counter[lead.demand_type] += 1
    return [{"demand_type": k, "count": v} for k, v in counter.most_common(5)]


def _build_top_keywords(comments: list) -> list[dict]:
    counter: Counter = Counter()
    for comment in comments:
        text = comment.content or ""
        for kw in _KEYWORD_LIST:
            if kw in text:
                counter[kw] += 1
    return [{"keyword": k, "count": v} for k, v in counter.most_common(10)]


def _build_hot_posts(posts: list) -> list[dict]:
    hot = [p for p in posts if p.is_hot]
    if not hot:
        hot = sorted(posts, key=lambda p: p.comment_count, reverse=True)[:5]
    else:
        hot = sorted(hot, key=lambda p: p.comment_count, reverse=True)[:5]
    return [
        {
            "id": p.id,
            "title": p.title or "",
            "post_url": p.post_url or "",
            "comment_count": p.comment_count,
            "is_hot": p.is_hot,
        }
        for p in hot
    ]


def _build_content_suggestions(top_demands: list[dict]) -> list[str]:
    suggestions = []
    for item in top_demands[:3]:
        dt = item["demand_type"]
        tmpl = _CONTENT_SUGGESTION_TEMPLATES.get(dt)
        if tmpl:
            suggestions.append(tmpl)
    if not suggestions:
        suggestions.append(_DEFAULT_CONTENT_SUGGESTION)
    return suggestions


def _build_follow_up_suggestions(a_count: int, b_count: int, lead_count: int) -> list[str]:
    if a_count >= 3:
        return [_FOLLOW_UP_TEMPLATES["high_a"]]
    if a_count > 0:
        return [_FOLLOW_UP_TEMPLATES["has_a"]]
    if b_count > 0:
        return [_FOLLOW_UP_TEMPLATES["has_b"]]
    return [_FOLLOW_UP_TEMPLATES["low"]]


def generate_daily_report(db: Session, platform: str | None = None) -> DailyReport:
    today = _today_utc()
    platform_key = platform or "all"

    # 基础查询 —— 按 platform 过滤（如有）
    def _pf(q, model_platform):
        if platform:
            return q.filter(model_platform == platform)
        return q

    # 监控源数量（all time，不限今天）
    source_q = db.query(func.count(MonitorSource.id)).filter(MonitorSource.enabled == True)
    source_q = _pf(source_q, MonitorSource.platform)
    source_count: int = source_q.scalar() or 0

    # 今日帖子
    post_q = _pf(db.query(Post), Post.platform)
    post_q = _filter_today(post_q, Post.created_at)
    posts = post_q.all()
    post_count = len(posts)

    # 今日评论
    comment_q = _pf(db.query(Comment), Comment.platform)
    comment_q = _filter_today(comment_q, Comment.created_at)
    comments = comment_q.all()
    comment_count = len(comments)

    # 今日线索
    lead_q = _pf(db.query(Lead), Lead.platform)
    lead_q = _filter_today(lead_q, Lead.created_at)
    leads = lead_q.all()
    lead_count = len(leads)

    a_count = sum(1 for l in leads if l.lead_level == "A")
    b_count = sum(1 for l in leads if l.lead_level == "B")
    c_count = sum(1 for l in leads if l.lead_level == "C")
    d_count = sum(1 for l in leads if l.lead_level == "D")

    top_demands = _build_top_demands(leads)
    top_keywords = _build_top_keywords(comments)
    hot_posts = _build_hot_posts(posts)
    content_suggestions = _build_content_suggestions(top_demands)
    follow_up_suggestions = _build_follow_up_suggestions(a_count, b_count, lead_count)

    a_lead_details = _build_a_lead_details(leads)
    typical_evidence = _build_typical_evidence(leads)
    discovered_competitors = _build_discovered_competitors(db, platform)
    tomorrow_suggestions = _build_tomorrow_suggestions(a_count, b_count, lead_count, top_demands, top_keywords)
    crm_stats = _build_crm_stats(db)

    existing = (
        db.query(DailyReport)
        .filter(DailyReport.report_date == today, DailyReport.platform == platform_key)
        .first()
    )

    if existing:
        report = existing
    else:
        report = DailyReport(report_date=today, platform=platform_key)
        db.add(report)

    report.source_count = source_count
    report.post_count = post_count
    report.comment_count = comment_count
    report.lead_count = lead_count
    report.a_lead_count = a_count
    report.b_lead_count = b_count
    report.c_lead_count = c_count
    report.d_lead_count = d_count
    report.top_demands = top_demands
    report.top_keywords = top_keywords
    report.hot_posts = hot_posts
    report.content_suggestions = content_suggestions
    report.follow_up_suggestions = follow_up_suggestions
    report.risk_warnings = _RISK_WARNINGS
    report.a_lead_details = a_lead_details
    report.typical_evidence = typical_evidence
    report.discovered_competitors = discovered_competitors
    report.tomorrow_suggestions = tomorrow_suggestions
    report.crm_stats = crm_stats

    db.commit()
    db.refresh(report)
    return report


def _build_a_lead_details(leads: list) -> list[dict]:
    a_leads = [l for l in leads if l.lead_level == "A"]
    if not a_leads:
        return []
    return [
        {
            "id": l.id,
            "platform": l.platform,
            "user_name": l.user_name or "",
            "content": (l.content or "")[:200],
            "lead_score": l.lead_score,
            "demand_type": l.demand_type or "",
            "follow_up_script": l.follow_up_script or "",
            "reason": l.reason or "",
        }
        for l in a_leads[:10]
    ]


def _build_typical_evidence(leads: list) -> list[dict]:
    scored_leads = [l for l in leads if l.lead_level in ("A", "B") and l.evidence]
    if not scored_leads:
        return []
    results = []
    for l in scored_leads[:5]:
        evidence = l.evidence if isinstance(l.evidence, dict) else {}
        matched_words = evidence.get("matched_words", [])
        amounts = evidence.get("amounts", [])
        results.append({
            "lead_id": l.id,
            "platform": l.platform,
            "content": (l.content or "")[:150],
            "matched_words": matched_words,
            "amounts": amounts,
            "lead_level": l.lead_level,
        })
    return results


def _build_discovered_competitors(db: Session, platform: str | None) -> list[dict]:
    today = _today_utc()
    query = db.query(PendingCompetitorAccount).filter(
        func.date(PendingCompetitorAccount.created_at) == today
    )
    if platform:
        query = query.filter(PendingCompetitorAccount.platform == platform)
    competitors = query.order_by(PendingCompetitorAccount.competitor_score.desc()).limit(10).all()
    return [
        {
            "id": c.id,
            "platform": c.platform,
            "account_name": c.account_name,
            "competitor_score": c.competitor_score,
            "status": c.status,
            "discover_reason": c.discover_reason or "",
            "suggest_monitor": c.competitor_score >= 60,
        }
        for c in competitors
    ]


def _build_tomorrow_suggestions(
    a_count: int, b_count: int, lead_count: int, top_demands: list[dict], top_keywords: list[dict]
) -> dict:
    recommended_keywords = []
    for item in top_keywords[:5]:
        kw = item.get("keyword", "")
        if kw:
            recommended_keywords.append(kw)

    if not recommended_keywords:
        recommended_keywords = ["征信花", "急用钱", "负债高", "网贷太多", "公积金贷款"]

    competitor_directions = []
    demand_names = [d.get("demand_type", "") for d in top_demands[:3]]
    if "借款需求" in demand_names:
        competitor_directions.append("关注发布借款攻略类内容的同行账号")
    if "资质焦虑" in demand_names:
        competitor_directions.append("关注发布征信修复/提额类内容的同行账号")
    if "产品咨询" in demand_names:
        competitor_directions.append("关注做贷款产品对比的同行账号")
    if not competitor_directions:
        competitor_directions.append("关注活跃发布贷款相关内容的同行账号")

    content_topics = []
    for dt in demand_names:
        if dt == "借款需求":
            content_topics.append("「急用钱怎么借？3分钟看懂申请条件」")
        elif dt == "资质焦虑":
            content_topics.append("「征信花了还能贷款吗？真实案例分享」")
        elif dt == "产品咨询":
            content_topics.append("「信用贷 vs 抵押贷，哪种更适合你？」")
        elif dt == "弱意向":
            content_topics.append("「一分钟测额度，看看你能贷多少」")
    if not content_topics:
        content_topics.append("「贷款申请全攻略：从准备到下款」")

    follow_up_hints = []
    if a_count >= 3:
        follow_up_hints.append("A级线索充足，建议明天优先跟进A级客户，争取当天完成首次沟通和方案推荐。")
    elif a_count > 0:
        follow_up_hints.append("有A级线索待跟进，建议明天上午完成A级线索的首次联系。")
    if b_count >= 5:
        follow_up_hints.append("B级线索较多，建议通过产品介绍和测额工具筛选高意向客户。")
    if lead_count == 0:
        follow_up_hints.append("今日无线索，建议检查监控关键词是否精准，或增加新的监控源扩大覆盖。")

    return {
        "recommended_keywords": recommended_keywords,
        "competitor_directions": competitor_directions,
        "content_topics": content_topics,
        "follow_up_hints": follow_up_hints if follow_up_hints else ["保持当前监控策略，持续优化关键词和采集频率。"],
    }


def get_today_report(db: Session, platform: str | None = None) -> DailyReport | None:
    today = _today_utc()
    platform_key = platform or "all"
    return (
        db.query(DailyReport)
        .filter(DailyReport.report_date == today, DailyReport.platform == platform_key)
        .first()
    )


def list_daily_reports(db: Session, platform: str | None = None) -> list[DailyReport]:
    query = db.query(DailyReport)
    if platform:
        query = query.filter(DailyReport.platform == platform)
    return query.order_by(DailyReport.report_date.desc(), DailyReport.id.desc()).all()


def _build_crm_stats(db: Session) -> dict:
    today = _today_utc()
    today_new = db.query(func.count(CrmCustomer.id)).filter(
        func.date(CrmCustomer.created_at) == today,
    ).scalar() or 0
    today_follow_count = db.query(func.count(CrmFollowRecord.id)).filter(
        func.date(CrmFollowRecord.created_at) == today,
    ).scalar() or 0
    interested_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "interested",
    ).scalar() or 0
    converted_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "converted",
    ).scalar() or 0
    overdue_follow = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.next_follow_up_at < datetime.now(timezone.utc),
        CrmCustomer.status.notin_(["converted", "invalid"]),
    ).scalar() or 0
    return {
        "today_new_customers": today_new,
        "today_follow_count": today_follow_count,
        "interested_count": interested_count,
        "converted_count": converted_count,
        "overdue_follow_remind": overdue_follow,
    }
