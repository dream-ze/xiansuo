"""采集管道服务 - 负责采集、去重、入库、评分等一整条链路"""

import re
from datetime import datetime, timezone
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


def _sanitize_error_message(error: Exception | str) -> str:
    """脱敏错误信息，避免敏感数据泄露
    
    移除：Cookie、API Key、URL 参数中的 token/key 等
    
    Args:
        error: 原始错误信息
    
    Returns:
        脱敏后的错误信息
    """
    msg = str(error)
    
    # 脱敏 Cookie
    msg = re.sub(r'cookie["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'cookie=***', msg, flags=re.IGNORECASE)
    
    # 脱敏 API Key
    msg = re.sub(r'(api[_-]?)?key["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'key=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'token["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'token=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'password=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'authorization["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'Authorization=***', msg, flags=re.IGNORECASE)
    
    # 脱敏 URL 中的 key/token/auth 参数
    msg = re.sub(r'[?&](key|token|auth|api_key|apikey)=[^&\s]+', '&key=***', msg, flags=re.IGNORECASE)
    
    return msg


def _post_already_exists(db: Session, platform: str, post_id: str) -> bool:
    """检查 post 是否已存在
    
    Args:
        db: 数据库连接
        platform: 平台名称
        post_id: 帖子 ID
    
    Returns:
        是否已存在
    """
    existing = db.query(Post).filter(
        Post.platform == platform,
        Post.post_id == post_id,
    ).first()
    return existing is not None


def _comment_already_exists(db: Session, platform: str, comment_id: str) -> bool:
    """检查 comment 是否已存在
    
    Args:
        db: 数据库连接
        platform: 平台名称
        comment_id: 评论 ID
    
    Returns:
        是否已存在
    """
    existing = db.query(Comment).filter(
        Comment.platform == platform,
        Comment.comment_id == comment_id,
    ).first()
    return existing is not None


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
        new_posts_count = 0
        
        # Phase 2: 去重逻辑 - 检查 posts 是否已存在
        for collected_post in collector_result.posts:
            # 按 platform + post_id 检查是否已存在
            if _post_already_exists(db, collected_post.platform, collected_post.post_id):
                # 帖子已存在，跳过入库
                continue
            
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
            new_posts_count += 1

        scoring_service = LeadScoringService()
        lead_count = 0
        new_comments_count = 0

        # Phase 2: 去重逻辑 - 检查 comments 是否已存在
        for collected_comment in collector_result.comments:
            # 按 platform + comment_id 检查是否已存在
            if _comment_already_exists(db, collected_comment.platform, collected_comment.comment_id):
                # 评论已存在，跳过入库和评分
                continue
            
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
            new_comments_count += 1

            # Phase 2: 只对新评论生成 leads（已存在的评论不重复生成）
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

        # Phase 2: 采集成功后更新 last_crawled_at
        source.last_crawled_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()

        return mark_crawl_task_success(
            db=db,
            crawl_task=crawl_task,
            post_count=new_posts_count,  # 只计算新增的 posts
            comment_count=new_comments_count,  # 只计算新增的 comments
            lead_count=lead_count,
            discovered_competitor_count=discovered_competitor_count,
        )
    except Exception as error:
        db.rollback()
        # Phase 2: 脱敏 error_message，避免敏感数据泄露
        sanitized_error = _sanitize_error_message(error)
        error_message = f"crawl failed for source_id={source.id}, source_type={source.source_type}: {sanitized_error}"
        return mark_crawl_task_failed(db, crawl_task, error_message)
