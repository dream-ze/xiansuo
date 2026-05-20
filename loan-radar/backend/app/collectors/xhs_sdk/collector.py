from __future__ import annotations

import logging
from typing import Any

from app.adapters.xhs.pc_api_adapter import XhsPcApiAdapter
from app.collectors.base import (
    BaseCollector,
    CollectedComment,
    CollectedPost,
    CollectorResult,
)
from app.collectors.config import CollectorConfig

logger = logging.getLogger(__name__)


class XhsSdkCollector(BaseCollector):
    def collect(self, source: Any) -> CollectorResult:
        config = CollectorConfig.parse(getattr(source, "config", None) or {})
        cookies = config.cookies or ""
        if not cookies:
            logger.warning("XhsSdkCollector: no cookies configured, collection may fail")

        adapter = XhsPcApiAdapter(cookies)
        posts: list[CollectedPost] = []
        comments: list[CollectedComment] = []

        source_type = getattr(source, "source_type", "keyword")
        source_value = getattr(source, "source_value", "")

        if source_type == "keyword":
            posts, comments = self._collect_keyword(adapter, source_value, config)
        elif source_type == "manual_post":
            posts, comments = self._collect_single_post(adapter, source_value, config)
        else:
            logger.warning("XhsSdkCollector: unsupported source_type=%s", source_type)

        return CollectorResult(posts=posts, comments=comments, metadata={"collector": "xhs_sdk"})

    def _collect_keyword(
        self, adapter: XhsPcApiAdapter, keyword: str, config: CollectorConfig
    ) -> tuple[list[CollectedPost], list[CollectedComment]]:
        posts: list[CollectedPost] = []
        comments: list[CollectedComment] = []
        max_posts = config.get_effective_max_posts()

        try:
            result = adapter.search_note(keyword=keyword, page=1)
            items = self._extract_search_items(result)
        except Exception as exc:
            logger.error("XhsSdkCollector search failed: %s", exc)
            return posts, comments

        for item in items[:max_posts]:
            post = self._map_search_item_to_post(item)
            if post:
                posts.append(post)

            if config.enable_comments and post and post.post_url:
                try:
                    comment_result = adapter.get_note_comments(post.post_url)
                    comment_items = self._extract_comment_items(comment_result)
                    for c in comment_items[: (config.max_comments_per_post or 50)]:
                        comment = self._map_comment(c, post.post_id)
                        if comment:
                            comments.append(comment)
                except Exception as exc:
                    logger.warning("XhsSdkCollector comments failed for %s: %s", post.post_id, exc)

        return posts, comments

    def _collect_single_post(
        self, adapter: XhsPcApiAdapter, url: str, config: CollectorConfig
    ) -> tuple[list[CollectedPost], list[CollectedComment]]:
        posts: list[CollectedPost] = []
        comments: list[CollectedComment] = []

        try:
            result = adapter.get_note_info(url)
            post = self._map_note_info_to_post(result)
            if post:
                posts.append(post)
        except Exception as exc:
            logger.error("XhsSdkCollector get_note_info failed: %s", exc)
            return posts, comments

        if config.enable_comments and url:
            try:
                comment_result = adapter.get_note_comments(url)
                comment_items = self._extract_comment_items(comment_result)
                for c in comment_items[: (config.max_comments_per_post or 50)]:
                    comment = self._map_comment(c, posts[0].post_id if posts else "")
                    if comment:
                        comments.append(comment)
            except Exception as exc:
                logger.warning("XhsSdkCollector comments failed: %s", exc)

        return posts, comments

    @staticmethod
    def _extract_search_items(result: Any) -> list[dict]:
        if isinstance(result, dict):
            items = result.get("items") or result.get("data") or []
            if isinstance(items, list):
                return items
        if isinstance(result, (list, tuple)):
            return list(result)
        return []

    @staticmethod
    def _extract_comment_items(result: Any) -> list[dict]:
        if isinstance(result, dict):
            items = result.get("comments") or result.get("data") or []
            if isinstance(items, list):
                return items
        if isinstance(result, (list, tuple)):
            return list(result)
        return []

    @staticmethod
    def _map_search_item_to_post(item: Any) -> CollectedPost | None:
        if not isinstance(item, dict):
            return None
        note = item.get("note_card") or item.get("noteCard") or item
        return CollectedPost(
            platform="xhs",
            post_id=str(note.get("note_id") or note.get("noteId") or ""),
            title=note.get("display_title") or note.get("title") or "",
            content=note.get("desc") or "",
            post_url=note.get("url") or "",
            author_name=(note.get("user") or {}).get("nickname") or "",
            author_profile_url=(note.get("user") or {}).get("url") or "",
            like_count=note.get("interact_info", {}).get("liked_count", 0) if isinstance(note.get("interact_info"), dict) else 0,
            comment_count=note.get("interact_info", {}).get("comment_count", 0) if isinstance(note.get("interact_info"), dict) else 0,
            collect_count=note.get("interact_info", {}).get("collected_count", 0) if isinstance(note.get("interact_info"), dict) else 0,
            raw_data=item,
        )

    @staticmethod
    def _map_note_info_to_post(result: Any) -> CollectedPost | None:
        if not isinstance(result, dict):
            return None
        data = result.get("data") or result
        return CollectedPost(
            platform="xhs",
            post_id=str(data.get("note_id") or data.get("noteId") or ""),
            title=data.get("title") or data.get("display_title") or "",
            content=data.get("desc") or "",
            post_url=data.get("url") or "",
            author_name=(data.get("user") or {}).get("nickname") or "",
            author_profile_url=(data.get("user") or {}).get("url") or "",
            like_count=data.get("interact_info", {}).get("liked_count", 0) if isinstance(data.get("interact_info"), dict) else 0,
            comment_count=data.get("interact_info", {}).get("comment_count", 0) if isinstance(data.get("interact_info"), dict) else 0,
            collect_count=data.get("interact_info", {}).get("collected_count", 0) if isinstance(data.get("interact_info"), dict) else 0,
            raw_data=result,
        )

    @staticmethod
    def _map_comment(item: Any, post_id: str) -> CollectedComment | None:
        if not isinstance(item, dict):
            return None
        return CollectedComment(
            platform="xhs",
            post_id=post_id,
            comment_id=str(item.get("comment_id") or item.get("id") or ""),
            user_name=(item.get("user_info") or item.get("user") or {}).get("nickname") or "",
            content=item.get("content") or "",
            like_count=item.get("like_count") or item.get("liked_count") or 0,
            raw_data=item,
        )
