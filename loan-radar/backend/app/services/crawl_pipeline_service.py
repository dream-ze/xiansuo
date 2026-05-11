from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.collectors import CollectorFactory
from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.post import Post
from app.services.competitor_discovery_service import CompetitorDiscoveryService
from app.services.crawl_task_service import (
    create_running_crawl_task,
    mark_crawl_task_failed,
    mark_crawl_task_success,
)
from app.services.lead_scoring_service import LeadScoringService


def run_monitor_source_crawl(db: Session, source: MonitorSource) -> CrawlTask:
    crawl_task = create_running_crawl_task(db, source)

    try:
        collector_source = SimpleNamespace(
            source_type=source.source_type,
            platform=source.platform,
            value=source.value,
            config=(source.config or {}),
        )
        collector = CollectorFactory.create(collector_source)
        collector_result = collector.collect(collector_source)

        post_id_map = {}
        created_post_ids: list[int] = []
        for collected_post in collector_result.posts:
            post = Post(
                platform=collected_post.platform,
                source_id=source.id,
                source_type=source.source_type,
                post_id=collected_post.post_id,
                title=collected_post.title,
                content=collected_post.content,
                post_url=collected_post.post_url,
                author_name=collected_post.author_name,
                author_profile_url=collected_post.author_profile_url,
                like_count=collected_post.like_count,
                comment_count=collected_post.comment_count,
                collect_count=collected_post.collect_count,
                publish_time=collected_post.publish_time,
                is_hot=collected_post.is_hot,
                raw_data=collected_post.raw_data,
            )
            db.add(post)
            db.flush()
            post_id_map[collected_post.post_id] = post.id
            created_post_ids.append(post.id)

        scoring_service = LeadScoringService()
        lead_count = 0

        for collected_comment in collector_result.comments:
            comment = Comment(
                platform=collected_comment.platform,
                post_id=collected_comment.post_id,
                comment_id=collected_comment.comment_id,
                user_name=collected_comment.user_name,
                user_profile_url=collected_comment.user_profile_url,
                content=collected_comment.content,
                like_count=collected_comment.like_count,
                publish_time=collected_comment.publish_time,
                raw_data=collected_comment.raw_data,
                is_suspected_demand=False,
            )

            scoring_result = scoring_service.score(collected_comment.content or "")
            comment.is_suspected_demand = scoring_result.is_suspected_demand
            comment.demand_type = scoring_result.demand_type
            comment.risk_level = scoring_result.risk_level

            db.add(comment)
            db.flush()

            if scoring_result.is_suspected_demand:
                lead = Lead(
                    platform=collected_comment.platform,
                    source_id=source.id,
                    source_type=source.source_type,
                    source_post_id=post_id_map.get(collected_comment.post_id),
                    source_comment_id=comment.id,
                    user_name=collected_comment.user_name,
                    content=collected_comment.content,
                    lead_level=scoring_result.lead_level,
                    lead_score=scoring_result.lead_score,
                    demand_type=scoring_result.demand_type,
                    risk_level=scoring_result.risk_level,
                    evidence=scoring_result.evidence,
                    reason=scoring_result.reason,
                    follow_up_script=scoring_result.follow_up_script,
                    status="new",
                )
                db.add(lead)
                lead_count += 1

        discovered_competitor_count = 0
        if source.source_type == "keyword":
            discovery_service = CompetitorDiscoveryService()
            discovered_competitor_count = discovery_service.discover_from_keyword_crawl(
                db=db,
                source_id=source.id,
                source_keyword=source.value,
                post_ids=created_post_ids,
            )

        db.commit()

        return mark_crawl_task_success(
            db=db,
            crawl_task=crawl_task,
            post_count=len(collector_result.posts),
            comment_count=len(collector_result.comments),
            lead_count=lead_count,
            discovered_competitor_count=discovered_competitor_count,
        )
    except Exception as error:
        db.rollback()
        error_message = f"crawl failed for source_id={source.id}, source_type={source.source_type}: {error}"
        return mark_crawl_task_failed(db, crawl_task, error_message)
