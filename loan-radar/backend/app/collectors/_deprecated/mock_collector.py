import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.collectors.base import (
    BaseCollector,
    CollectedComment,
    CollectedPost,
    CollectorResult,
)

MOCK_POST_TEMPLATES = [
    {
        "title": "征信花了还能贷吗？分享我的经历",
        "content": "征信查询太多了，之前不懂事点了很多网贷，现在想办信用贷被拒，有没有办法补救？",
        "author": "小红薯A",
    },
    {
        "title": "急用5万周转，有什么渠道推荐",
        "content": "家里有急事需要5万周转，征信还算干净，有没有靠谱的渠道？利息别太高就行。",
        "author": "抖音用户B",
    },
    {
        "title": "负债高能不能做？真实案例分享",
        "content": "负债率超过50%了，月供压力很大，有没有做债务重组的渠道？或者能下款的信用贷？",
        "author": "知乎答主C",
    },
    {
        "title": "有逾期怎么处理？过来人经验",
        "content": "信用卡逾期了3个月，已经还清了，但征信上还有记录，多久能消除？现在还能贷款吗？",
        "author": "小红薯D",
    },
    {
        "title": "网贷太多还能下款吗？亲测有效",
        "content": "网贷笔数太多被银行拒了，后来找了个助贷中介做了一笔房抵贷，终于上岸了。分享给大家参考。",
        "author": "抖音用户E",
    },
    {
        "title": "公积金断了还能贷吗？政策解读",
        "content": "换工作导致公积金断缴了3个月，之前连续缴了2年，现在还能申请公积金信用贷吗？",
        "author": "知乎答主F",
    },
    {
        "title": "查询多是不是没希望了？",
        "content": "半年内征信查询了20多次，大部分是网贷审批查询，现在想办正规贷款还有机会吗？",
        "author": "小红薯G",
    },
    {
        "title": "信用卡快还不上了怎么办",
        "content": "信用卡欠了8万，每月最低还款都很吃力，有没有分期或者代还的方案？不想逾期。",
        "author": "抖音用户H",
    },
    {
        "title": "企业周转需要20万，怎么操作",
        "content": "小公司经营周转需要20万，有营业执照和流水，但法人征信有瑕疵，能做企业贷吗？",
        "author": "知乎答主I",
    },
    {
        "title": "房抵贷一般多久能办下来",
        "content": "想用房子抵押贷一笔钱出来，请问从申请到放款一般需要多久？需要准备什么材料？",
        "author": "小红薯J",
    },
]

MOCK_COMMENT_TEMPLATES = [
    {"content": "征信花了还能贷款吗", "is_demand": True},
    {"content": "急用5万周转，有没有靠谱渠道", "is_demand": True},
    {"content": "负债高还能申请吗", "is_demand": True},
    {"content": "有逾期怎么处理", "is_demand": True},
    {"content": "网贷太多还能下款吗", "is_demand": True},
    {"content": "企业周转需要20万怎么办", "is_demand": True},
    {"content": "房抵贷一般多久能办下来", "is_demand": True},
    {"content": "公积金断了还能贷吗", "is_demand": True},
    {"content": "查询多是不是没希望了", "is_demand": True},
    {"content": "信用卡快还不上了怎么办", "is_demand": True},
    {"content": "我也遇到过类似情况，最后找了个靠谱的中介", "is_demand": False},
    {"content": "建议先打一份征信报告看看具体情况", "is_demand": False},
    {"content": "可以做债务重组，我之前就是这么操作的", "is_demand": False},
    {"content": "千万别再点网贷了，越点越花", "is_demand": False},
    {"content": "有房的话可以做抵押贷，利息低很多", "is_demand": True},
    {"content": "需要5万左右，征信花了能做吗", "is_demand": True},
    {"content": "负债30万，月供压力太大了", "is_demand": True},
    {"content": "逾期已还清，多久能恢复", "is_demand": True},
    {"content": "感谢分享，收藏了", "is_demand": False},
    {"content": "这个方案不错，学到了", "is_demand": False},
    {"content": "有没有做信用贷的渠道推荐", "is_demand": True},
    {"content": "公积金信用贷利率多少", "is_demand": True},
    {"content": "征信查询多怎么消除记录", "is_demand": True},
    {"content": "我这边可以帮你看看，私信你了", "is_demand": False},
    {"content": "专业助贷，全国可做，需要的私聊", "is_demand": False},
    {"content": "房贷利率现在多少？想转贷", "is_demand": True},
    {"content": "有营业执照能做什么贷款", "is_demand": True},
    {"content": "信用贷被拒了还有其他办法吗", "is_demand": True},
    {"content": "这个中介靠谱吗？收费多少", "is_demand": False},
    {"content": "我也想知道，蹲一个回复", "is_demand": False},
]

MOCK_COMPETITOR_AUTHORS = [
    {"name": "助贷顾问小王", "profile": "https://mock.local/users/competitor-1"},
    {"name": "贷款规划师李姐", "profile": "https://mock.local/users/competitor-2"},
    {"name": "信贷经理老张", "profile": "https://mock.local/users/competitor-3"},
]

SOURCE_TYPE_RULES = {
    "keyword": {"post_count": 5, "comments_per_post": 6, "is_hot": False},
    "competitor_account": {"post_count": 3, "comments_per_post": 8, "is_hot": False},
    "manual_post": {"post_count": 1, "comments_per_post": 15, "is_hot": False},
    "hot_post_rule": {"post_count": 5, "comments_per_post": 10, "is_hot": True},
}


def _is_mock_enabled() -> bool:
    return os.getenv("ENABLE_MOCK_COLLECTOR", "false").strip().lower() in ("true", "1", "yes")


class MockCollector(BaseCollector):
    """演示采集器 - 生成贴近助贷场景的模拟数据

    仅在 ENABLE_MOCK_COLLECTOR=true 时可用。
    所有生成的数据均标记 raw_data.demo = true，避免与真实数据混淆。
    """

    def collect(self, source: Any) -> CollectorResult:
        source_type = getattr(source, "source_type", "keyword")
        platform = getattr(source, "platform", "xhs")
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

        return CollectorResult(
            posts=posts,
            comments=comments,
            metadata={"demo": True, "collector_type": "mock"},
        )

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
        template = MOCK_POST_TEMPLATES[(index - 1) % len(MOCK_POST_TEMPLATES)]
        post_id = f"demo-{source_type}-{index}-{uuid.uuid4().hex[:8]}"
        like_count = 500 + index * 50 if is_hot else 20 + index * 3

        is_competitor = index <= len(MOCK_COMPETITOR_AUTHORS) and source_type == "keyword"

        return CollectedPost(
            platform=platform,
            post_id=post_id,
            title=template["title"],
            content=template["content"],
            post_url=f"https://demo.local/{platform}/posts/{post_id}",
            author_name=MOCK_COMPETITOR_AUTHORS[index - 1]["name"] if is_competitor else template["author"],
            author_profile_url=(
                MOCK_COMPETITOR_AUTHORS[index - 1]["profile"]
                if is_competitor
                else f"https://demo.local/{platform}/users/author-{index}"
            ),
            like_count=like_count,
            comment_count=comments_per_post,
            collect_count=100 + index * 10 if is_hot else index * 2,
            publish_time=now - timedelta(hours=index),
            is_hot=is_hot,
            raw_data={
                "demo": True,
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
        template = MOCK_COMMENT_TEMPLATES[(comment_index - 1) % len(MOCK_COMMENT_TEMPLATES)]

        return CollectedComment(
            platform=platform,
            post_id=post_id,
            comment_id=f"{post_id}-comment-{comment_index}",
            user_name=f"用户{comment_index}",
            user_profile_url=f"https://demo.local/{platform}/users/commenter-{comment_index}",
            content=template["content"],
            like_count=comment_index % 10,
            publish_time=now - timedelta(minutes=comment_index * 5),
            raw_data={
                "demo": True,
                "is_demand_template": template["is_demand"],
            },
        )
