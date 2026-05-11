from collections import Counter
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.daily_report import DailyReport
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
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
    "请勿在公开评论中直接承诺贷款成功率或利率范围，避免合规风险。",
    "私信跟进时请勿索取用户身份证、银行卡等敏感信息，应引导至正规渠道申请。",
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

    # 已有同日同平台报告则更新，否则新建
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

    db.commit()
    db.refresh(report)
    return report


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
