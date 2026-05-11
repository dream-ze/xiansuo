from datetime import datetime, timedelta, timezone
from typing import Any

from app.collectors.base import (
    BaseCollector,
    CollectedComment,
    CollectedPost,
    CollectorResult,
)

DEMAND_COMMENT_SAMPLES = [
    "征信花了还能贷吗",
    "负债高还能申请吗",
    "急用 5 万怎么办",
    "有房贷还能办信用贷吗",
    "网贷太多还能下款吗",
    "企业周转需要 20 万怎么办",
    "房抵贷一般多久能办下来",
    "公积金断了还能贷吗",
    "查询多是不是没希望了",
    "信用卡快还不上了怎么办",
]

SOURCE_TYPE_RULES = {
    "keyword": {"post_count": 10, "comments_per_post": 10, "is_hot": False},
    "competitor_account": {"post_count": 5, "comments_per_post": 10, "is_hot": False},
    "manual_post": {"post_count": 1, "comments_per_post": 50, "is_hot": False},
    "hot_post_rule": {"post_count": 10, "comments_per_post": 20, "is_hot": True},
}


class MockCollector(BaseCollector):
    def collect(self, source: Any) -> CollectorResult:
        source_type = getattr(source, "source_type", "keyword")
        platform = getattr(source, "platform", "other")
        source_value = getattr(source, "value", "") or source_type
        rule = SOURCE_TYPE_RULES.get(source_type, SOURCE_TYPE_RULES["keyword"])
        now = datetime.now(timezone.utc)

        posts = [
            self._build_post(
                platform=platform,
                source_type=source_type,
                source_value=source_value,
                index=index,
                is_hot=rule["is_hot"],
                comments_per_post=rule["comments_per_post"],
                now=now,
            )
            for index in range(1, rule["post_count"] + 1)
        ]

        comments = [
            self._build_comment(
                platform=platform,
                post_id=post.post_id,
                comment_index=comment_index,
                now=now,
            )
            for post in posts
            for comment_index in range(1, rule["comments_per_post"] + 1)
        ]

        return CollectorResult(posts=posts, comments=comments)

    def _build_post(
        self,
        platform: str,
        source_type: str,
        source_value: str,
        index: int,
        is_hot: bool,
        comments_per_post: int,
        now: datetime,
    ) -> CollectedPost:
        post_id = f"mock-{source_type}-{index}"
        like_count = 500 + index * 50 if is_hot else 20 + index

        return CollectedPost(
            platform=platform,
            post_id=post_id,
            title=f"{source_value} 模拟帖子 {index}",
            content=f"围绕 {source_value} 的模拟帖子内容，用于验证采集主链路。",
            post_url=f"https://mock.local/{platform}/posts/{post_id}",
            author_name=f"模拟作者{index}",
            author_profile_url=f"https://mock.local/{platform}/users/author-{index}",
            like_count=like_count,
            comment_count=comments_per_post,
            collect_count=100 + index * 10 if is_hot else index,
            publish_time=now - timedelta(hours=index),
            is_hot=is_hot,
            raw_data={
                "mock": True,
                "source_type": source_type,
                "source_value": source_value,
            },
        )

    def _build_comment(
        self,
        platform: str,
        post_id: str,
        comment_index: int,
        now: datetime,
    ) -> CollectedComment:
        sample = DEMAND_COMMENT_SAMPLES[(comment_index - 1) % len(DEMAND_COMMENT_SAMPLES)]

        return CollectedComment(
            platform=platform,
            post_id=post_id,
            comment_id=f"{post_id}-comment-{comment_index}",
            user_name=f"模拟用户{comment_index}",
            user_profile_url=f"https://mock.local/{platform}/users/commenter-{comment_index}",
            content=sample,
            like_count=comment_index,
            publish_time=now - timedelta(minutes=comment_index),
            raw_data={
                "mock": True,
                "sample_index": comment_index,
            },
        )
