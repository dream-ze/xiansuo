from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.collectors.base import CollectedComment, CollectedPost


SUPPORTED_PLATFORMS = {
    "xhs",
    "douyin",
    "zhihu",
    # Future: kuaishou, bilibili, weibo, tieba
}

PLATFORM_LABELS = {
    "xhs": "小红书",
    "douyin": "抖音",
    "zhihu": "知乎",
    # Future: kuaishou -> 快手, bilibili -> B站, weibo -> 微博, tieba -> 贴吧
}


def _pick(source: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        for candidate in (normalized, normalized.replace("/", "-")):
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
    return None


def _is_hot(like_count: int, comment_count: int, collect_count: int) -> bool:
    interaction_score = like_count + comment_count * 3 + collect_count * 2
    return interaction_score >= 100 or like_count >= 80 or comment_count >= 20


def _author_profile_url(platform: str, author_id: str | None, raw_user: dict[str, Any]) -> str | None:
    explicit = _pick(raw_user, "profile_url", "user_page_url", "url", "home_url")
    if explicit:
        return str(explicit)
    if not author_id:
        return None
    url_templates = {
        "xhs": "https://www.xiaohongshu.com/user/profile/{id}",
        "douyin": "https://www.douyin.com/user/{id}",
        "zhihu": "https://www.zhihu.com/people/{id}",
        # Future: bilibili, weibo, kuaishou, tieba
        "bilibili": "https://space.bilibili.com/{id}",
        "weibo": "https://weibo.com/u/{id}",
        "kuaishou": "https://www.kuaishou.com/profile/{id}",
        "tieba": "https://tieba.baidu.com/home/main?un={id}",
    }
    template = url_templates.get(platform, "")
    if template:
        return template.format(id=author_id)
    return None


def _build_post_url(platform: str, post_id: str, raw_data: dict[str, Any]) -> str | None:
    explicit = _pick(raw_data, "url", "post_url", "note_url", "share_info.share_url")
    if explicit:
        return str(explicit)

    url_templates = {
        "xhs": "https://www.xiaohongshu.com/explore/{id}",
        "douyin": "https://www.douyin.com/video/{id}",
        "zhihu": "https://www.zhihu.com/question/{id}",
        # Future: bilibili, weibo, kuaishou, tieba
        "bilibili": "https://www.bilibili.com/video/{id}",
        "weibo": "https://weibo.com/detail/{id}",
        "kuaishou": "https://www.kuaishou.com/short-video/{id}",
        "tieba": "https://tieba.baidu.com/p/{id}",
    }
    template = url_templates.get(platform, "")
    if template and post_id:
        return template.format(id=post_id)
    return None


def map_platform_data(
    raw_data: dict[str, Any],
    platform: str,
) -> tuple[list[CollectedPost], list[CollectedComment]]:
    posts: list[CollectedPost] = []
    comments: list[CollectedComment] = []

    raw_posts = raw_data.get("posts", [])
    raw_comments = raw_data.get("comments", [])

    mapper = _PLATFORM_MAPPERS.get(platform, _map_generic_post)

    for raw_post in raw_posts:
        if not isinstance(raw_post, dict):
            continue
        post = mapper(raw_post, platform)
        if post and post.post_id:
            posts.append(post)

    for raw_comment in raw_comments:
        if not isinstance(raw_comment, dict):
            continue
        comment = _map_generic_comment(raw_comment, platform)
        if comment and comment.comment_id:
            comments.append(comment)

    return posts, comments


def _map_xhs_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    note = raw_note.get("note_card") if isinstance(raw_note.get("note_card"), dict) else raw_note
    interact_info = note.get("interact_info") or raw_note.get("interact_info") or {}
    user = note.get("user") or raw_note.get("user") or note.get("author") or {}

    post_id = str(_pick(note, "note_id", "id") or _pick(raw_note, "note_id", "id") or "")
    if not post_id:
        return None

    title = _pick(note, "title", "display_title")
    content = _pick(note, "desc", "content", "note_text")
    author_id = str(_pick(user, "user_id", "id") or "")

    like_count = _as_int(_pick(interact_info, "liked_count", "like_count"))
    comment_count = _as_int(_pick(interact_info, "comment_count", "comments_count"))
    collect_count = _as_int(_pick(interact_info, "collected_count", "collect_count"))

    post_url = _build_post_url(platform, post_id, raw_note)
    xsec_token = _pick(raw_note, "xsec_token")
    if post_url and xsec_token and "xsec_token=" not in post_url:
        sep = "&" if "?" in post_url else "?"
        post_url = f"{post_url}{sep}xsec_token={xsec_token}&xsec_source=pc_search"

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=str(post_url) if post_url else None,
        author_name=str(_pick(user, "nickname", "nick_name", "name")) if _pick(user, "nickname", "nick_name", "name") else None,
        author_profile_url=_author_profile_url(platform, author_id, user),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(note, "time", "publish_time", "last_update_time", "create_time")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_douyin_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    aweme = raw_note.get("aweme_detail") if isinstance(raw_note.get("aweme_detail"), dict) else raw_note
    author_info = aweme.get("author_info") or aweme.get("author") or {}
    stats = aweme.get("stats") or aweme.get("statistics") or raw_note.get("stats") or {}

    post_id = str(_pick(aweme, "aweme_id", "id", "aweme_id_str") or "")
    if not post_id:
        return None

    title = _pick(aweme, "desc", "title", "content")
    author_id = str(_pick(author_info, "uid", "user_id", "id") or "")

    like_count = _as_int(_pick(stats, "digg_count", "like_count", "liked_count"))
    comment_count = _as_int(_pick(stats, "comment_count", "comments_count"))
    collect_count = _as_int(_pick(stats, "collect_count", "favorite_count"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(title) if title else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(author_info, "nickname", "name")) if _pick(author_info, "nickname", "name") else None,
        author_profile_url=_author_profile_url(platform, author_id, author_info),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(aweme, "create_time", "publish_time")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_bilibili_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    video_info = raw_note.get("View") or raw_note.get("video_info") or raw_note
    owner = video_info.get("owner") or video_info.get("author_info") or {}
    stat = video_info.get("stat") or raw_note.get("stat") or {}

    post_id = str(_pick(video_info, "bvid", "aid", "id") or "")
    if not post_id:
        return None

    title = _pick(video_info, "title")
    content = _pick(video_info, "desc", "description")
    author_id = str(_pick(owner, "mid", "user_id", "id") or "")

    like_count = _as_int(_pick(stat, "like", "like_count", "likes"))
    comment_count = _as_int(_pick(stat, "reply", "comment_count", "comments"))
    collect_count = _as_int(_pick(stat, "favorite", "collect_count", "favorites"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(owner, "name", "nickname", "author")) if _pick(owner, "name", "nickname", "author") else None,
        author_profile_url=_author_profile_url(platform, author_id, owner),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(video_info, "pubdate", "publish_time", "created")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_weibo_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    mblog = raw_note.get("mblog") or raw_note
    user = mblog.get("user") or raw_note.get("user") or {}

    post_id = str(_pick(mblog, "id", "mid", "bid") or "")
    if not post_id:
        return None

    title = _pick(mblog, "status_title", "topic_title")
    content = _pick(mblog, "text_raw", "text", "content")
    author_id = str(_pick(user, "id", "idstr", "uid") or "")

    like_count = _as_int(_pick(mblog, "attitudes_count", "like_count"))
    comment_count = _as_int(_pick(mblog, "comments_count", "comment_count"))
    collect_count = _as_int(_pick(mblog, "reposts_count", "repost_count"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(user, "screen_name", "name", "nickname")) if _pick(user, "screen_name", "name", "nickname") else None,
        author_profile_url=_author_profile_url(platform, author_id, user),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(mblog, "created_at", "publish_time", "created_time")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_kuaishou_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    video = raw_note.get("photo") or raw_note.get("video") or raw_note
    author_info = video.get("author") or raw_note.get("author") or {}

    post_id = str(_pick(video, "id", "photo_id", "short_id") or "")
    if not post_id:
        return None

    title = _pick(video, "caption", "title", "desc")
    author_id = str(_pick(author_info, "id", "user_id", "kwai_id") or "")

    like_count = _as_int(_pick(video, "likeCount", "like_count", "liked_count"))
    comment_count = _as_int(_pick(video, "commentCount", "comment_count"))
    collect_count = _as_int(_pick(video, "favoriteCount", "collect_count"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(title) if title else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(author_info, "name", "nickname", "user_name")) if _pick(author_info, "name", "nickname", "user_name") else None,
        author_profile_url=_author_profile_url(platform, author_id, author_info),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(video, "timestamp", "publish_time", "create_time")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_zhihu_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    question = raw_note.get("question") or raw_note.get("target") or raw_note
    author_info = question.get("author") or raw_note.get("author") or {}

    post_id = str(_pick(question, "id", "question_id") or "")
    if not post_id:
        return None

    title = _pick(question, "title", "name")
    content = _pick(question, "excerpt", "content", "detail")
    author_id = str(_pick(author_info, "id", "url_token") or "")

    like_count = _as_int(_pick(question, "voteup_count", "like_count", "liking_count"))
    comment_count = _as_int(_pick(question, "comment_count", "answer_count"))
    collect_count = _as_int(_pick(question, "follower_count", "collect_count"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(author_info, "name", "nickname")) if _pick(author_info, "name", "nickname") else None,
        author_profile_url=_author_profile_url(platform, author_id, author_info),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(question, "created_time", "publish_time", "created")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_tieba_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    thread = raw_note.get("thread") or raw_note

    post_id = str(_pick(thread, "id", "tid", "thread_id") or "")
    if not post_id:
        return None

    title = _pick(thread, "title", "subject")
    content = _pick(thread, "content", "abstract", "first_post_content")
    author_info = thread.get("author") or {}
    author_id = str(_pick(author_info, "id", "name", "user_id") or _pick(thread, "author_name", "") or "")

    like_count = _as_int(_pick(thread, "like_count", "agree_count"))
    comment_count = _as_int(_pick(thread, "reply_num", "comment_count", "reply_count"))
    collect_count = _as_int(_pick(thread, "collect_count", "share_count"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(author_info, "name", "nickname", "author_name")) if _pick(author_info, "name", "nickname", "author_name") else None,
        author_profile_url=_author_profile_url(platform, author_id, author_info),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(thread, "create_time", "publish_time", "created_time")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_generic_post(raw_note: dict[str, Any], platform: str) -> CollectedPost | None:
    post_id = str(_pick(raw_note, "id", "note_id", "post_id", "aweme_id", "bvid") or "")
    if not post_id:
        return None

    title = _pick(raw_note, "title", "display_title", "desc", "subject")
    content = _pick(raw_note, "content", "desc", "text", "note_text")
    user = raw_note.get("user") or raw_note.get("author") or raw_note.get("author_info") or {}
    author_id = str(_pick(user, "id", "user_id", "uid", "mid") or "")

    like_count = _as_int(_pick(raw_note, "like_count", "liked_count", "digg_count", "likes"))
    comment_count = _as_int(_pick(raw_note, "comment_count", "comments_count", "reply_num"))
    collect_count = _as_int(_pick(raw_note, "collect_count", "collected_count", "favorite_count"))

    return CollectedPost(
        platform=platform,
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=_build_post_url(platform, post_id, raw_note),
        author_name=str(_pick(user, "nickname", "name", "screen_name")) if _pick(user, "nickname", "name", "screen_name") else None,
        author_profile_url=_author_profile_url(platform, author_id, user),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(raw_note, "publish_time", "create_time", "created_at")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def _map_generic_comment(raw_comment: dict[str, Any], platform: str) -> CollectedComment | None:
    comment_id = str(_pick(raw_comment, "id", "comment_id") or "")
    if not comment_id:
        return None

    post_id = str(_pick(raw_comment, "note_id", "post_id", "target_id", "aweme_id") or "")
    user = raw_comment.get("user_info") or raw_comment.get("user") or raw_comment.get("author") or {}
    user_id = str(_pick(user, "user_id", "id", "uid", "mid") or "")

    content = _pick(raw_comment, "content", "text", "text_raw", "message")

    return CollectedComment(
        platform=platform,
        post_id=post_id,
        comment_id=comment_id,
        user_name=str(_pick(user, "nickname", "name", "screen_name")) if _pick(user, "nickname", "name", "screen_name") else None,
        user_profile_url=_author_profile_url(platform, user_id, user),
        content=str(content) if content else None,
        like_count=_as_int(_pick(raw_comment, "like_count", "liked_count", "digg_count")),
        publish_time=_parse_datetime(_pick(raw_comment, "create_time", "publish_time", "created_at")),
        raw_data=raw_comment,
    )


_PLATFORM_MAPPERS: dict[str, Any] = {
    "xhs": _map_xhs_post,
    "douyin": _map_douyin_post,
    "zhihu": _map_zhihu_post,
    # Future: bilibili, weibo, kuaishou, tieba (mappers kept for forward compatibility)
    "bilibili": _map_bilibili_post,
    "weibo": _map_weibo_post,
    "kuaishou": _map_kuaishou_post,
    "tieba": _map_tieba_post,
}
