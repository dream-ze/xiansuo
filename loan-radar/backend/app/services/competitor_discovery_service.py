from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.pending_competitor import PendingCompetitorAccount
from app.models.post import Post


class CompetitorDiscoveryService:
    """Discover suspected competitor accounts from keyword crawl posts."""

    _CONTENT_HINT_WORDS = [
        "贷款",
        "借款",
        "下款",
        "征信",
        "负债",
        "额度",
        "中介",
        "助贷",
        "融资",
        "周转",
    ]
    _COMPETITOR_HINT_WORDS = [
        "助贷",
        "中介",
        "渠道",
        "对接",
        "可做",
        "可接",
        "全国",
        "一手",
    ]

    def discover_from_keyword_crawl(
        self,
        db: Session,
        source_id: int,
        source_keyword: str,
        post_ids: list[int],
    ) -> int:
        if not post_ids:
            return 0

        posts = (
            db.query(Post)
            .filter(Post.id.in_(post_ids), Post.source_id == source_id)
            .all()
        )
        if not posts:
            return 0

        posts_by_profile: dict[str, list[Post]] = defaultdict(list)
        for post in posts:
            profile_url = (post.author_profile_url or "").strip()
            if not profile_url:
                continue
            posts_by_profile[profile_url].append(post)

        if not posts_by_profile:
            return 0

        existing_profile_urls = {
            row[0]
            for row in db.query(PendingCompetitorAccount.profile_url)
            .filter(PendingCompetitorAccount.profile_url.in_(list(posts_by_profile.keys())))
            .all()
        }

        inserted_count = 0

        for profile_url, profile_posts in posts_by_profile.items():
            if profile_url in existing_profile_urls:
                continue

            author_name = (profile_posts[0].author_name or "").strip() or "未知作者"
            platform = profile_posts[0].platform
            post_db_ids = [p.id for p in profile_posts]
            post_source_ids = [p.post_id for p in profile_posts]

            recent_post_count = len(profile_posts)
            recent_comment_count = (
                db.query(Comment)
                .filter(Comment.post_id.in_(post_source_ids))
                .count()
            )
            suspected_lead_count = (
                db.query(Lead)
                .filter(Lead.source_post_id.in_(post_db_ids))
                .count()
            )

            content_relevance_score = self._score_content_relevance(
                keyword=source_keyword,
                author_name=author_name,
                posts=profile_posts,
            )
            interaction_score = self._score_interaction(
                posts=profile_posts,
                recent_comment_count=recent_comment_count,
            )
            lead_potential_score = self._score_lead_potential(suspected_lead_count)
            risk_score = self._score_risk(author_name=author_name, posts=profile_posts)

            competitor_score = round(
                content_relevance_score * 0.35
                + interaction_score * 0.25
                + lead_potential_score * 0.30
                + risk_score * 0.10,
                2,
            )

            if competitor_score < 45:
                continue

            discover_reason = self._build_discover_reason(
                keyword=source_keyword,
                content_relevance_score=content_relevance_score,
                interaction_score=interaction_score,
                lead_potential_score=lead_potential_score,
                risk_score=risk_score,
                recent_post_count=recent_post_count,
                recent_comment_count=recent_comment_count,
                suspected_lead_count=suspected_lead_count,
            )

            db.add(
                PendingCompetitorAccount(
                    platform=platform,
                    account_name=author_name,
                    profile_url=profile_url,
                    source_keyword=source_keyword,
                    source_post_id=profile_posts[0].id,
                    discover_reason=discover_reason,
                    competitor_score=competitor_score,
                    content_relevance_score=content_relevance_score,
                    interaction_score=interaction_score,
                    lead_potential_score=lead_potential_score,
                    risk_score=risk_score,
                    recent_post_count=recent_post_count,
                    recent_comment_count=recent_comment_count,
                    suspected_lead_count=suspected_lead_count,
                    status="pending",
                )
            )
            inserted_count += 1

        return inserted_count

    def list_pending_competitors(
        self,
        db: Session,
        platform: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
    ) -> list[PendingCompetitorAccount]:
        query = db.query(PendingCompetitorAccount)

        if platform is not None:
            query = query.filter(PendingCompetitorAccount.platform == platform)
        if status is not None:
            query = query.filter(PendingCompetitorAccount.status == status)
        if min_score is not None:
            query = query.filter(PendingCompetitorAccount.competitor_score >= min_score)

        return query.order_by(PendingCompetitorAccount.id.desc()).all()

    def get_pending_competitor(
        self,
        db: Session,
        competitor_id: int,
    ) -> PendingCompetitorAccount | None:
        return (
            db.query(PendingCompetitorAccount)
            .filter(PendingCompetitorAccount.id == competitor_id)
            .first()
        )

    def approve_pending_competitor(
        self,
        db: Session,
        competitor: PendingCompetitorAccount,
    ) -> tuple[PendingCompetitorAccount, MonitorSource]:
        if competitor.status != "pending":
            raise ValueError("only pending competitors can be approved")

        competitor.status = "approved"
        monitor_source = MonitorSource(
            source_type="competitor_account",
            platform=competitor.platform,
            name=competitor.account_name,
            value=competitor.profile_url,
            config={"collector_type": "mock"},
            enabled=True,
        )
        db.add(monitor_source)
        db.commit()
        db.refresh(competitor)
        db.refresh(monitor_source)
        return competitor, monitor_source

    def ignore_pending_competitor(
        self,
        db: Session,
        competitor: PendingCompetitorAccount,
    ) -> PendingCompetitorAccount:
        if competitor.status != "pending":
            raise ValueError("only pending competitors can be ignored")

        competitor.status = "ignored"
        db.commit()
        db.refresh(competitor)
        return competitor

    def _score_content_relevance(self, keyword: str, author_name: str, posts: list[Post]) -> float:
        keyword = (keyword or "").strip()
        text_blobs = [author_name]
        text_blobs.extend((p.title or "") + " " + (p.content or "") for p in posts)
        merged_text = " ".join(text_blobs)

        hits = 0
        if keyword and keyword in merged_text:
            hits += 3

        hint_hits = sum(1 for word in self._CONTENT_HINT_WORDS if word in merged_text)
        competitor_hint_hits = sum(1 for word in self._COMPETITOR_HINT_WORDS if word in merged_text)
        hits += min(hint_hits, 6)
        hits += min(competitor_hint_hits, 4)

        return round(min(100, hits * 10), 2)

    def _score_interaction(self, posts: list[Post], recent_comment_count: int) -> float:
        like_count = sum(max(0, p.like_count or 0) for p in posts)
        collect_count = sum(max(0, p.collect_count or 0) for p in posts)
        declared_comment_count = sum(max(0, p.comment_count or 0) for p in posts)
        interaction_volume = like_count + collect_count + declared_comment_count + recent_comment_count

        if interaction_volume >= 300:
            return 100.0
        if interaction_volume >= 180:
            return 85.0
        if interaction_volume >= 100:
            return 70.0
        if interaction_volume >= 50:
            return 55.0
        if interaction_volume > 0:
            return 35.0
        return 0.0

    def _score_lead_potential(self, suspected_lead_count: int) -> float:
        if suspected_lead_count >= 15:
            return 100.0
        if suspected_lead_count >= 10:
            return 85.0
        if suspected_lead_count >= 6:
            return 70.0
        if suspected_lead_count >= 3:
            return 55.0
        if suspected_lead_count > 0:
            return 35.0
        return 0.0

    def _score_risk(self, author_name: str, posts: list[Post]) -> float:
        text_blobs = [author_name]
        text_blobs.extend((p.title or "") + " " + (p.content or "") for p in posts)
        merged_text = " ".join(text_blobs)

        hit_counter = Counter(word for word in self._COMPETITOR_HINT_WORDS if word in merged_text)
        risk_hit = sum(hit_counter.values())
        if risk_hit >= 4:
            return 90.0
        if risk_hit >= 3:
            return 75.0
        if risk_hit >= 2:
            return 60.0
        if risk_hit == 1:
            return 40.0
        return 20.0

    def _build_discover_reason(
        self,
        keyword: str,
        content_relevance_score: float,
        interaction_score: float,
        lead_potential_score: float,
        risk_score: float,
        recent_post_count: int,
        recent_comment_count: int,
        suspected_lead_count: int,
    ) -> str:
        return (
            f"关键词[{keyword}]采集中命中高相关内容；"
            f"内容相关分={content_relevance_score}，互动分={interaction_score}，"
            f"线索潜力分={lead_potential_score}，风险分={risk_score}；"
            f"近期开帖={recent_post_count}，互动评论={recent_comment_count}，"
            f"疑似线索={suspected_lead_count}。"
        )
