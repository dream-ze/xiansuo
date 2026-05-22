from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.daily_report import DailyReport
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.pending_competitor import PendingCompetitorAccount
from app.models.post import Post

PLATFORM_URL_MAP = {
    "xhs": {"base": "https://www.xiaohongshu.com", "post": "https://www.xiaohongshu.com/explore", "user": "https://www.xiaohongshu.com/user/profile"},
    "douyin": {"base": "https://www.douyin.com", "post": "https://www.douyin.com/video", "user": "https://www.douyin.com/user"},
    "zhihu": {"base": "https://www.zhihu.com", "post": "https://www.zhihu.com/question", "user": "https://www.zhihu.com/people"},
}


def _platform_post_url(platform: str, post_id: str) -> str:
    m = PLATFORM_URL_MAP.get(platform, PLATFORM_URL_MAP["zhihu"])
    return f"{m['post']}/{post_id}"


def _platform_user_url(platform: str, user_id: str) -> str:
    m = PLATFORM_URL_MAP.get(platform, PLATFORM_URL_MAP["zhihu"])
    return f"{m['user']}/{user_id}"
from app.services.daily_report_service import generate_daily_report
from app.services.lead_scoring_service import LeadScoringService


DEMO_TAG = {"demo": True}

MONITOR_SOURCES = [
    {
        "source_type": "keyword",
        "platform": "xhs",
        "name": "演示 - 征信花了",
        "value": "征信花了",
        "config": {"collector_type": "media_crawler", "mode": "real", "max_posts": 10, "enable_comments": True},
    },
    {
        "source_type": "competitor_account",
        "platform": "douyin",
        "name": "演示 - 助贷顾问小王",
        "value": "助贷顾问小王",
        "config": {"collector_type": "media_crawler", "mode": "real", "max_posts": 5, "enable_comments": True},
    },
    {
        "source_type": "manual_post",
        "platform": "zhihu",
        "name": "演示 - 指定帖子",
        "value": "https://www.zhihu.com/question/demo-manual-post",
        "config": {"collector_type": "media_crawler", "mode": "real", "max_posts": 1, "enable_comments": True},
    },
]

POST_TEMPLATES = [
    {
        "title": "征信花了还能贷吗？分享我的经历",
        "content": "征信查询太多了，之前不懂事点了很多网贷，现在想办信用贷被拒，有没有办法补救？",
        "author": "小红薯A",
        "platform": "xhs",
        "source_type": "keyword",
    },
    {
        "title": "急用5万周转，有什么渠道推荐",
        "content": "家里有急事需要5万周转，征信还算干净，有没有靠谱的渠道？利息别太高就行。",
        "author": "小红薯B",
        "platform": "xhs",
        "source_type": "keyword",
    },
    {
        "title": "负债高能不能做？真实案例分享",
        "content": "负债率超过50%了，月供压力很大，有没有做债务重组的渠道？或者能下款的信用贷？",
        "author": "小红薯C",
        "platform": "xhs",
        "source_type": "keyword",
    },
    {
        "title": "有逾期怎么处理？过来人经验",
        "content": "信用卡逾期了3个月，已经还清了，但征信上还有记录，多久能消除？现在还能贷款吗？",
        "author": "小红薯D",
        "platform": "xhs",
        "source_type": "keyword",
    },
    {
        "title": "网贷太多还能下款吗？亲测有效",
        "content": "网贷笔数太多被银行拒了，后来找了个正规渠道做了一笔房抵贷，终于上岸了。分享给大家参考。",
        "author": "助贷顾问小王",
        "platform": "douyin",
        "source_type": "competitor_account",
    },
    {
        "title": "公积金断了还能贷吗？政策解读",
        "content": "换工作导致公积金断缴了3个月，之前连续缴了2年，现在还能申请公积金信用贷吗？",
        "author": "助贷顾问小王",
        "platform": "douyin",
        "source_type": "competitor_account",
    },
    {
        "title": "查询多是不是没希望了？",
        "content": "半年内征信查询了20多次，大部分是网贷审批查询，现在想办正规贷款还有机会吗？",
        "author": "小红薯E",
        "platform": "xhs",
        "source_type": "keyword",
    },
    {
        "title": "信用卡快还不上了怎么办",
        "content": "信用卡欠了8万，每月最低还款都很吃力，有没有分期或者代还的方案？不想逾期。",
        "author": "小红薯F",
        "platform": "xhs",
        "source_type": "keyword",
    },
    {
        "title": "企业周转需要20万，怎么操作",
        "content": "小公司经营周转需要20万，有营业执照和流水，但法人征信有瑕疵，能做企业贷吗？",
        "author": "知乎答主G",
        "platform": "zhihu",
        "source_type": "manual_post",
    },
    {
        "title": "房抵贷一般多久能办下来",
        "content": "想用房子抵押贷一笔钱出来，请问从申请到放款一般需要多久？需要准备什么材料？",
        "author": "知乎答主H",
        "platform": "zhihu",
        "source_type": "manual_post",
    },
]

DEMAND_COMMENTS = [
    {
        "content": "急用8万周转，征信花了能贷款吗？网贷太多还不上了怎么办",
        "target_level": "A",
    },
    {
        "content": "急用10万借款，负债高征信花，能申请信用贷吗？马上需要",
        "target_level": "A",
    },
    {
        "content": "征信花了急需5万贷款周转，网贷太多查询多，今天能下款吗",
        "target_level": "A",
    },
    {
        "content": "负债高征信花，急用3万借款怎么办，现在就申请贷款",
        "target_level": "A",
    },
    {
        "content": "急用15万周转，征信花负债高，能办房抵贷吗？尽快回复",
        "target_level": "A",
    },
    {
        "content": "征信花想贷款5万，负债高网贷太多，能申请吗",
        "target_level": "B",
    },
    {
        "content": "负债高能申请信用贷吗？网贷太多还不上怎么办",
        "target_level": "B",
    },
    {
        "content": "征信花了想借款3万周转，查询多还能贷款吗",
        "target_level": "B",
    },
    {
        "content": "急用钱，征信花负债高，房抵贷利率多少",
        "target_level": "B",
    },
    {
        "content": "网贷太多查询多，能申请公积金贷款吗？负债高",
        "target_level": "B",
    },
    {
        "content": "征信花能贷吗？想申请信用贷8万周转",
        "target_level": "B",
    },
    {
        "content": "负债高怎么办，想借款10万做房抵贷",
        "target_level": "B",
    },
    {
        "content": "网贷太多征信花，信用贷被拒了还能申请什么",
        "target_level": "B",
    },
    {
        "content": "征信花想申请信用贷，负债高能办吗",
        "target_level": "B",
    },
    {
        "content": "征信花了还能贷款吗？负债高怎么处理",
        "target_level": "C",
    },
    {
        "content": "网贷太多怎么办，查询多能消除吗",
        "target_level": "C",
    },
    {
        "content": "负债高怎么降低月供，有方案吗",
        "target_level": "C",
    },
    {
        "content": "征信花多久能恢复，公积金断了影响贷款吗",
        "target_level": "C",
    },
    {
        "content": "信用卡还不上怎么办，逾期了有什么后果",
        "target_level": "C",
    },
    {
        "content": "企业贷需要什么条件，营业执照多久能申请",
        "target_level": "C",
    },
    {
        "content": "房抵贷利息多少，一般多久放款",
        "target_level": "C",
    },
    {
        "content": "专业助贷全国可做，一手渠道对接，加盟引流",
        "target_level": "D",
    },
    {
        "content": "同行交流，代理加盟贷款业务，广告引流",
        "target_level": "D",
    },
    {
        "content": "代理加盟贷款业务，利润丰厚，引流推广",
        "target_level": "D",
    },
]

NON_DEMAND_COMMENTS = [
    "我也遇到过类似情况，最后找了个靠谱的中介",
    "建议先打一份征信报告看看具体情况",
    "可以做债务重组，我之前就是这么操作的",
    "千万别再点网贷了，越点越花",
    "感谢分享，收藏了",
    "这个方案不错，学到了",
    "建议去正规银行咨询，别找小贷公司",
    "先还清逾期，等半年再申请",
    "可以尝试公积金信用贷，利率比较低",
    "有房做抵押贷是最划算的方案",
    "企业贷需要看经营流水和纳税记录",
    "征信花了可以先养征信，半年内别再查",
    "我之前也是这样，后来做了债务重组上岸了",
    "找正规渠道，别信什么包下款的广告",
    "建议先打征信报告，看具体查询次数",
    "逾期记录5年后会自动消除",
    "负债高可以先做债务优化，降低月供",
    "公积金贷款利率最低，优先考虑",
    "房抵贷一般7-15个工作日放款",
    "企业贷需要营业执照满1年",
    "信用卡可以申请分期，减轻月供压力",
    "征信查询记录2年后不再显示",
    "建议找正规银行，别碰高利贷",
    "有社保也可以做信用贷",
    "先结清小额网贷，再申请大额",
]

COMPETITOR_ACCOUNTS = [
    {
        "account_name": "助贷顾问小王",
        "profile_url": "https://www.douyin.com/user/competitor-1",
        "platform": "douyin",
        "source_keyword": "征信花了",
        "discover_reason": "多次发布助贷相关内容，疑似同行推广账号",
    },
    {
        "account_name": "贷款规划师李姐",
        "profile_url": "https://www.douyin.com/user/competitor-2",
        "platform": "douyin",
        "source_keyword": "征信花了",
        "discover_reason": "评论区主动留联系方式推广贷款服务",
    },
    {
        "account_name": "信贷经理老张",
        "profile_url": "https://www.xiaohongshu.com/user/profile/competitor-3",
        "platform": "xhs",
        "source_keyword": "征信花了",
        "discover_reason": "发布大量贷款产品对比内容，疑似中介账号",
    },
    {
        "account_name": "金融小助手",
        "profile_url": "https://www.xiaohongshu.com/user/profile/competitor-4",
        "platform": "xhs",
        "source_keyword": "征信花了",
        "discover_reason": "频繁回复贷款咨询，引导私信，疑似获客账号",
    },
    {
        "account_name": "靠谱贷款推荐",
        "profile_url": "https://www.zhihu.com/people/competitor-5",
        "platform": "zhihu",
        "source_keyword": "征信花了",
        "discover_reason": "知乎专栏持续发布贷款攻略，含推广信息",
    },
]


def _content_hash(content: str | None) -> str:
    if not content:
        return ""
    return hashlib.sha256(content.strip().lower().encode("utf-8")).hexdigest()[:16]


def _clean_demo_data(db: Session) -> dict[str, int]:
    demo_comment_ids = [
        row[0] for row in db.query(Comment.id).filter(
            Comment.raw_data["demo"].as_boolean().is_(True)
        ).all()
    ]

    if demo_comment_ids:
        db.query(Lead).filter(Lead.source_comment_id.in_(demo_comment_ids)).delete(synchronize_session=False)

    demo_source_ids = [
        row[0] for row in db.query(MonitorSource.id).filter(
            MonitorSource.name.like("演示 - %")
        ).all()
    ]

    if demo_source_ids:
        db.query(CrawlTask).filter(CrawlTask.source_id.in_(demo_source_ids)).delete(synchronize_session=False)

    db.query(Comment).filter(Comment.raw_data["demo"].as_boolean().is_(True)).delete(synchronize_session=False)
    db.query(Post).filter(Post.raw_data["demo"].as_boolean().is_(True)).delete(synchronize_session=False)
    db.query(PendingCompetitorAccount).filter(
        PendingCompetitorAccount.profile_url.like("https://www.douyin.com/user/competitor-%")
    ).delete(synchronize_session=False)
    db.query(MonitorSource).filter(MonitorSource.name.like("演示 - %")).delete(synchronize_session=False)
    db.query(DailyReport).filter(
        DailyReport.report_date == datetime.now(timezone.utc).date()
    ).delete(synchronize_session=False)

    db.commit()

    return {
        "sources": len(demo_source_ids),
        "comments": len(demo_comment_ids),
    }


def _create_monitor_sources(db: Session) -> dict[tuple[str, str], MonitorSource]:
    sources = {}
    for cfg in MONITOR_SOURCES:
        source = MonitorSource(
            source_type=cfg["source_type"],
            platform=cfg["platform"],
            name=cfg["name"],
            value=cfg["value"],
            config=cfg["config"],
            enabled=True,
        )
        db.add(source)
        db.flush()
        sources[(cfg["platform"], cfg["source_type"])] = source
    db.commit()
    return sources


def _create_posts(db: Session, sources: dict[tuple[str, str], MonitorSource]) -> list[dict]:
    now = datetime.now(timezone.utc)
    posts = []
    for i, tpl in enumerate(POST_TEMPLATES):
        source = sources.get((tpl["platform"], tpl["source_type"]))
        if not source:
            continue

        post_id = f"demo-{tpl['source_type']}-{i + 1}-{uuid.uuid4().hex[:8]}"
        is_hot = i < 2
        like_count = 500 + i * 50 if is_hot else 20 + i * 3

        post = Post(
            platform=tpl["platform"],
            source_id=source.id,
            source_type=tpl["source_type"],
            post_id=post_id,
            content_hash=_content_hash(tpl["content"]),
            title=tpl["title"],
            content=tpl["content"],
            post_url=_platform_post_url(tpl["platform"], post_id),
            author_name=tpl["author"],
            author_profile_url=_platform_user_url(tpl["platform"], f"author-{i + 1}"),
            like_count=like_count,
            comment_count=5,
            collect_count=100 + i * 10 if is_hot else i * 2,
            publish_time=now - timedelta(hours=i + 1),
            is_hot=is_hot,
            raw_data={**DEMO_TAG, "source_type": tpl["source_type"]},
        )
        db.add(post)
        db.flush()
        posts.append({"post": post, "template": tpl})

    db.commit()
    return posts


def _create_comments_and_leads(db: Session, posts: list[dict]) -> tuple[int, int, dict[str, int]]:
    scoring_service = LeadScoringService()
    comment_count = 0
    lead_count = 0
    level_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}

    demand_idx = 0
    non_demand_idx = 0

    for post_info in posts:
        post = post_info["post"]

        num_demand = 3
        num_non_demand = 2

        for j in range(num_demand):
            if demand_idx >= len(DEMAND_COMMENTS):
                demand_idx = 0
            tpl = DEMAND_COMMENTS[demand_idx]
            demand_idx += 1

            comment_id = f"{post.post_id}-comment-d{demand_idx}-{uuid.uuid4().hex[:6]}"
            user_name = f"用户{demand_idx}"

            comment = Comment(
                platform=post.platform,
                post_id=post.post_id,
                comment_id=comment_id,
                content_hash=_content_hash(tpl["content"]),
                user_name=user_name,
                user_profile_url=_platform_user_url(post.platform, f"commenter-d{demand_idx}"),
                content=tpl["content"],
                like_count=j % 10,
                publish_time=datetime.now(timezone.utc) - timedelta(minutes=j * 5),
                is_suspected_demand=False,
                raw_data={**DEMO_TAG, "target_level": tpl["target_level"]},
            )

            scoring_result = scoring_service.score(tpl["content"])
            comment.is_suspected_demand = scoring_result.is_suspected_demand
            comment.demand_type = scoring_result.demand_type
            comment.risk_level = scoring_result.risk_level

            if tpl["target_level"] == "D":
                comment.is_suspected_demand = True
                comment.demand_type = "无效/风险"
                comment.risk_level = "high"

            db.add(comment)
            db.flush()
            comment_count += 1

            should_create_lead = scoring_result.is_suspected_demand or tpl["target_level"] == "D"
            if should_create_lead:
                existing = db.query(Lead).filter(
                    Lead.platform == comment.platform,
                    Lead.source_comment_id == comment.id,
                ).first()
                if not existing:
                    lead_level = scoring_result.lead_level
                    lead_score = scoring_result.lead_score
                    demand_type = scoring_result.demand_type
                    risk_level = scoring_result.risk_level
                    evidence = scoring_result.evidence
                    reason = scoring_result.reason
                    follow_up_script = scoring_result.follow_up_script

                    if tpl["target_level"] == "D":
                        lead_level = "D"
                        demand_type = "无效/风险"
                        risk_level = "high"
                        evidence = {**scoring_result.evidence, "negative_keywords_matched": ["同行", "代理", "加盟", "引流"]}
                        reason = "识别为 D 级线索，需求类型为无效/风险，命中负面关键词：同行、代理、加盟、引流。"
                        follow_up_script = "这条内容暂不建议直接跟进，可观察是否存在广告、同行或高风险特征。"

                    lead = Lead(
                        platform=comment.platform,
                        source_id=post.source_id,
                        source_type=post.source_type,
                        source_post_id=post.id,
                        source_comment_id=comment.id,
                        user_name=comment.user_name,
                        user_profile_url=comment.user_profile_url,
                        content_hash=_content_hash(comment.content),
                        content=comment.content,
                        lead_level=lead_level,
                        lead_score=lead_score,
                        demand_type=demand_type,
                        risk_level=risk_level,
                        evidence=evidence,
                        reason=reason,
                        follow_up_script=follow_up_script,
                        status="new",
                        is_duplicate=False,
                    )
                    db.add(lead)
                    lead_count += 1
                    level_counts[lead_level] = level_counts.get(lead_level, 0) + 1

        for j in range(num_non_demand):
            if non_demand_idx >= len(NON_DEMAND_COMMENTS):
                non_demand_idx = 0
            content = NON_DEMAND_COMMENTS[non_demand_idx]
            non_demand_idx += 1

            comment_id = f"{post.post_id}-comment-n{non_demand_idx}-{uuid.uuid4().hex[:6]}"
            user_name = f"路人{non_demand_idx}"

            comment = Comment(
                platform=post.platform,
                post_id=post.post_id,
                comment_id=comment_id,
                content_hash=_content_hash(content),
                user_name=user_name,
                user_profile_url=_platform_user_url(post.platform, f"commenter-n{non_demand_idx}"),
                content=content,
                like_count=j % 5,
                publish_time=datetime.now(timezone.utc) - timedelta(minutes=j * 3),
                is_suspected_demand=False,
                raw_data={**DEMO_TAG, "is_non_demand": True},
            )

            scoring_result = scoring_service.score(content)
            comment.is_suspected_demand = scoring_result.is_suspected_demand
            comment.demand_type = scoring_result.demand_type
            comment.risk_level = scoring_result.risk_level

            db.add(comment)
            db.flush()
            comment_count += 1

    db.commit()
    return comment_count, lead_count, level_counts


def _create_competitors(db: Session, sources: dict) -> int:
    keyword_source = sources.get(("xhs", "keyword"))
    count = 0
    for comp in COMPETITOR_ACCOUNTS:
        existing = db.query(PendingCompetitorAccount).filter(
            PendingCompetitorAccount.profile_url == comp["profile_url"]
        ).first()
        if existing:
            continue

        source_post_id = None
        if keyword_source:
            demo_post = db.query(Post).filter(
                Post.source_id == keyword_source.id,
                Post.raw_data["demo"].as_boolean().is_(True),
            ).first()
            if demo_post:
                source_post_id = demo_post.id

        competitor = PendingCompetitorAccount(
            platform=comp["platform"],
            account_name=comp["account_name"],
            profile_url=comp["profile_url"],
            source_keyword=comp["source_keyword"],
            source_post_id=source_post_id,
            discover_reason=comp["discover_reason"],
            competitor_score=75.0,
            content_relevance_score=80.0,
            interaction_score=60.0,
            lead_potential_score=70.0,
            risk_score=30.0,
            recent_post_count=5,
            recent_comment_count=20,
            suspected_lead_count=3,
            status="pending",
        )
        db.add(competitor)
        count += 1

    db.commit()
    return count


def _create_crawl_tasks(db: Session, sources: dict) -> int:
    count = 0
    now = datetime.now(timezone.utc)
    for key, source in sources.items():
        task = CrawlTask(
            source_id=source.id,
            source_type=source.source_type,
            source_value=source.value,
            platform=source.platform,
            status="success",
            progress="completed",
            limit_count=10,
            started_at=now - timedelta(minutes=10),
            finished_at=now - timedelta(minutes=9),
            post_count=3,
            comment_count=15,
            lead_count=8,
            collected_posts=3,
            collected_comments=15,
        )
        db.add(task)
        count += 1
    db.commit()
    return count


def seed_demo_data(db: Session) -> dict:
    cleaned = _clean_demo_data(db)

    sources = _create_monitor_sources(db)
    posts = _create_posts(db, sources)
    comment_count, lead_count, level_counts = _create_comments_and_leads(db, posts)
    competitor_count = _create_competitors(db, sources)
    task_count = _create_crawl_tasks(db, sources)
    report = generate_daily_report(db)

    return {
        "sources": len(sources),
        "posts": len(posts),
        "comments": comment_count,
        "leads": lead_count,
        "lead_levels": level_counts,
        "competitors": competitor_count,
        "crawl_tasks": task_count,
        "report_date": str(report.report_date),
        "cleaned": cleaned,
    }
