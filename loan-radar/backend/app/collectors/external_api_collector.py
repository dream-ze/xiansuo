"""外部 API 采集器 - 调用自定义 API 获取采集数据"""

import hashlib
import os
import time
from typing import Any

import requests

from app.collectors.base import BaseCollector, CollectedComment, CollectedPost, CollectorResult
from app.collectors.config import CollectorConfig


class ExternalApiCollector(BaseCollector):
    """调用外部 API 获取采集数据的采集器"""

    def __init__(self):
        pass

    def collect(self, source: Any) -> CollectorResult:
        """
        调用外部 API 获取采集数据

        Args:
            source: 监控源对象，应有 config 属性（包含 external_api 配置）

        Returns:
            CollectorResult: 包含 posts、comments、metadata 的结果

        Raises:
            ValueError: 配置错误或 API 调用失败
        """
        config = getattr(source, "config", None) or {}
        config_obj = CollectorConfig.parse(config)
        platform = getattr(source, "platform", "external_api")

        # 验证配置
        is_valid, msg = config_obj.validate_for_collector_type()
        if not is_valid:
            raise ValueError(f"Invalid external_api config: {msg}")

        # 获取 API 配置
        external_api_config = config_obj.external_api
        endpoint = external_api_config.get("endpoint")
        api_key_env = external_api_config.get("api_key_env")
        request_timeout = external_api_config.get("request_timeout", config_obj.timeout_seconds)

        # 从环境变量读取 API 密钥
        api_key = None
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if not api_key:
                raise ValueError(f"API key environment variable '{api_key_env}' not set")

        # 准备请求头
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            # 支持 Authorization Bearer token
            if api_key_env and api_key_env.lower().endswith("_token"):
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                # 或者作为 X-API-Key 头
                headers["X-API-Key"] = api_key

        # 准备请求参数
        payload = {
            "max_posts": config_obj.max_posts,
            "max_comments_per_post": config_obj.max_comments_per_post,
        }

        # 调用 API（带重试机制）
        result_data = self._call_api_with_retry(
            endpoint=endpoint,
            headers=headers,
            payload=payload,
            timeout=request_timeout,
            retry_times=config_obj.retry_times,
            rate_limit_seconds=config_obj.rate_limit_seconds,
        )

        # 解析响应
        return self._parse_api_response(
            result_data,
            platform=platform,
            max_comments_per_post=config_obj.max_comments_per_post,
        )

    def _call_api_with_retry(
        self,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: int,
        retry_times: int,
        rate_limit_seconds: int,
    ) -> dict[str, Any]:
        """
        调用 API，支持重试机制

        Args:
            endpoint: API 端点 URL
            headers: 请求头
            payload: 请求体
            timeout: 请求超时（秒）
            retry_times: 重试次数
            rate_limit_seconds: 请求间隔（秒）

        Returns:
            API 响应数据（JSON）

        Raises:
            Exception: 所有重试均失败
        """
        last_error = None

        for attempt in range(retry_times):
            try:
                # 添加速率限制
                if attempt > 0:
                    time.sleep(rate_limit_seconds)

                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()

                return response.json()

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < retry_times - 1:
                    # 继续重试
                    time.sleep(rate_limit_seconds)
                    continue
                else:
                    # 最后一次重试也失败了
                    raise Exception(
                        f"API call failed after {retry_times} attempts: {str(e)}"
                    ) from e

        # 不应该到达这里，但为了完整性
        raise Exception(f"API call failed: {str(last_error)}")

    def _parse_api_response(
        self,
        data: dict[str, Any],
        platform: str,
        max_comments_per_post: int,
    ) -> CollectorResult:
        """
        解析 API 响应，转换为 CollectorResult

        API 响应格式应该是：
        {
            "posts": [
                {
                    "post_id": "abc123",  // 可选
                    "title": "...",
                    "content": "...",
                    "author_name": "...",
                    ...
                }
            ],
            "comments": [
                {
                    "post_id": "abc123",
                    "comment_id": "cmt456",  // 可选
                    "content": "...",
                    ...
                }
            ]
        }

        Args:
            data: API 响应数据
            platform: 平台名称
            max_comments_per_post: 每条笔记的最多评论数

        Returns:
            CollectorResult: 标准化的采集结果
        """
        posts = []
        comments = []

        # 解析 posts
        posts_data = data.get("posts", [])
        for idx, post_data in enumerate(posts_data):
            try:
                # 生成 post_id（如果缺失）
                post_id = post_data.get("post_id")
                if not post_id:
                    # 根据内容生成 SHA1 作为 ID
                    content_for_id = f"{post_data.get('title', '')}{post_data.get('content', '')}{idx}"
                    post_id = hashlib.sha1(content_for_id.encode()).hexdigest()[:16]

                post = CollectedPost(
                    platform=platform,
                    post_id=post_id,
                    title=post_data.get("title"),
                    content=post_data.get("content"),
                    post_url=post_data.get("post_url"),
                    author_name=post_data.get("author_name"),
                    author_profile_url=post_data.get("author_profile_url"),
                    like_count=int(post_data.get("like_count", 0)),
                    comment_count=int(post_data.get("comment_count", 0)),
                    collect_count=int(post_data.get("collect_count", 0)),
                    publish_time=post_data.get("publish_time"),
                    is_hot=bool(post_data.get("is_hot", False)),
                    raw_data=post_data.get("raw_data"),
                )
                posts.append(post)
            except Exception as e:
                # 单条 post 解析失败，记录错误后继续
                print(f"Warning: Failed to parse post {idx}: {str(e)}")
                continue

        # 解析 comments
        comments_data = data.get("comments", [])
        for idx, comment_data in enumerate(comments_data):
            # 限制评论数量
            if len(comments) >= len(posts) * max_comments_per_post:
                break

            try:
                post_id = comment_data.get("post_id")
                if not post_id:
                    raise ValueError("comment requires post_id")

                # 生成 comment_id（如果缺失）
                comment_id = comment_data.get("comment_id")
                if not comment_id:
                    content_for_id = f"{post_id}{comment_data.get('content', '')}{idx}"
                    comment_id = hashlib.sha1(content_for_id.encode()).hexdigest()[:16]

                comment = CollectedComment(
                    platform=platform,
                    post_id=post_id,
                    comment_id=comment_id,
                    user_name=comment_data.get("user_name"),
                    user_profile_url=comment_data.get("user_profile_url"),
                    content=comment_data.get("content"),
                    like_count=int(comment_data.get("like_count", 0)),
                    publish_time=comment_data.get("publish_time"),
                    raw_data=comment_data.get("raw_data"),
                )
                comments.append(comment)
            except Exception as e:
                # 单条 comment 解析失败，记录错误后继续
                print(f"Warning: Failed to parse comment {idx}: {str(e)}")
                continue

        return CollectorResult(
            posts=posts,
            comments=comments,
            metadata={
                "source": "external_api",
                "total_posts": len(posts),
                "total_comments": len(comments),
            },
        )
