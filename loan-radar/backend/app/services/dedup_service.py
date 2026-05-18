from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.lead import Lead
from app.models.post import Post

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.8


def compute_content_hash(content: str | None) -> str:
    if not content:
        return ""
    normalized = content.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def compute_similarity(text_a: str | None, text_b: str | None) -> float:
    if not text_a or not text_b:
        return 0.0
    return SequenceMatcher(None, text_a.strip().lower(), text_b.strip().lower()).ratio()


def check_lead_duplicate(
    db: Session,
    platform: str,
    user_profile_url: str | None,
    content: str | None,
) -> tuple[bool, str | None, str | None]:
    if not user_profile_url and not content:
        return False, None, None

    content_hash = compute_content_hash(content)

    if user_profile_url:
        candidates = db.query(Lead).filter(
            Lead.platform == platform,
            Lead.user_profile_url == user_profile_url,
        ).all()

        for candidate in candidates:
            if not candidate.content:
                continue
            similarity = compute_similarity(content, candidate.content)
            if similarity >= SIMILARITY_THRESHOLD:
                group_id = candidate.duplicate_group_id or f"dup-{uuid.uuid4().hex[:12]}"
                reason = f"同用户相似评论(相似度{similarity:.0%})"
                if not candidate.duplicate_group_id:
                    candidate.duplicate_group_id = group_id
                    db.add(candidate)
                    logger.info(
                        "assigned existing lead #%d to duplicate group %s (primary)",
                        candidate.id, group_id,
                    )
                return True, group_id, reason

    if content_hash:
        exact_dup = db.query(Lead).filter(
            Lead.platform == platform,
            Lead.content_hash == content_hash,
        ).first()

        if exact_dup:
            group_id = exact_dup.duplicate_group_id or f"dup-{uuid.uuid4().hex[:12]}"
            reason = "相同内容重复"
            if not exact_dup.duplicate_group_id:
                exact_dup.duplicate_group_id = group_id
                db.add(exact_dup)
                logger.info(
                    "assigned existing lead #%d to duplicate group %s (primary, exact content)",
                    exact_dup.id, group_id,
                )
            return True, group_id, reason

    return False, None, None


@dataclass
class DedupResult:
    new_posts: list = field(default_factory=list)
    dup_post_ids: set = field(default_factory=set)
    updated_posts: list = field(default_factory=list)
    new_comments: list = field(default_factory=list)
    dup_comment_ids: set = field(default_factory=set)
    dup_post_count: int = 0
    dup_comment_count: int = 0
    updated_post_count: int = 0


def batch_dedup_posts(
    db: Session,
    platform: str,
    collected_posts: list,
) -> tuple[list, list, set, int, int]:
    if not collected_posts:
        return [], [], set(), 0, 0

    post_ids = [p.post_id for p in collected_posts if p.post_id]
    content_hashes = []
    post_hash_map: dict[str, object] = {}
    for p in collected_posts:
        if not p.post_id:
            continue
        h = compute_content_hash(p.content)
        if h:
            content_hashes.append(h)
            post_hash_map[h] = p

    existing_by_post_id: dict[str, Post] = {}
    if post_ids:
        rows = db.query(Post).filter(
            Post.platform == platform,
            Post.post_id.in_(post_ids),
        ).all()
        existing_by_post_id = {row.post_id: row for row in rows}

    existing_by_hash: dict[str, Post] = {}
    if content_hashes:
        rows = db.query(Post).filter(
            Post.platform == platform,
            Post.content_hash.in_(content_hashes),
        ).all()
        for row in rows:
            if row.content_hash:
                existing_by_hash[row.content_hash] = row

    new_posts = []
    updated_posts = []
    dup_post_ids: set[str] = set()
    dup_count = 0
    updated_count = 0

    for collected in collected_posts:
        if not collected.post_id:
            continue

        if collected.post_id in existing_by_post_id:
            dup_post_ids.add(collected.post_id)
            existing = existing_by_post_id[collected.post_id]
            _update_post_stats(existing, collected)
            updated_posts.append((existing, collected))
            updated_count += 1
            continue

        content_hash = compute_content_hash(collected.content)
        if content_hash and content_hash in existing_by_hash:
            dup_post_ids.add(collected.post_id)
            existing = existing_by_hash[content_hash]
            _update_post_stats(existing, collected)
            updated_posts.append((existing, collected))
            updated_count += 1
            continue

        new_posts.append(collected)

    return new_posts, updated_posts, dup_post_ids, dup_count + len(dup_post_ids) - updated_count, updated_count


def batch_dedup_comments(
    db: Session,
    platform: str,
    collected_comments: list,
    dup_post_ids: set[str],
) -> tuple[list, int]:
    if not collected_comments:
        return [], 0

    comment_ids = [c.comment_id for c in collected_comments if c.comment_id]
    content_hashes = []
    for c in collected_comments:
        if not c.comment_id:
            continue
        h = compute_content_hash(c.content)
        if h:
            content_hashes.append(h)

    existing_by_comment_id: dict[str, Comment] = {}
    if comment_ids:
        rows = db.query(Comment).filter(
            Comment.platform == platform,
            Comment.comment_id.in_(comment_ids),
        ).all()
        existing_by_comment_id = {row.comment_id: row for row in rows}

    existing_by_hash: dict[str, Comment] = {}
    if content_hashes:
        rows = db.query(Comment).filter(
            Comment.platform == platform,
            Comment.content_hash.in_(content_hashes),
        ).all()
        for row in rows:
            if row.content_hash:
                existing_by_hash[row.content_hash] = row

    new_comments = []
    dup_count = 0

    for collected in collected_comments:
        if not collected.comment_id:
            continue

        if collected.comment_id in existing_by_comment_id:
            dup_count += 1
            continue

        if collected.post_id in dup_post_ids:
            dup_count += 1
            continue

        content_hash = compute_content_hash(collected.content)
        if content_hash and content_hash in existing_by_hash:
            dup_count += 1
            continue

        new_comments.append(collected)

    return new_comments, dup_count


def _update_post_stats(existing: Post, collected) -> None:
    changed = False
    if collected.like_count is not None and collected.like_count != existing.like_count:
        existing.like_count = collected.like_count
        changed = True
    if collected.comment_count is not None and collected.comment_count != existing.comment_count:
        existing.comment_count = collected.comment_count
        changed = True
    if collected.collect_count is not None and collected.collect_count != existing.collect_count:
        existing.collect_count = collected.collect_count
        changed = True
    if collected.title and not existing.title:
        existing.title = collected.title
        changed = True
    if collected.content and not existing.content:
        existing.content = collected.content
        changed = True
    if collected.post_url and not existing.post_url:
        existing.post_url = collected.post_url
        changed = True
    if not changed:
        return
    logger.debug("updated post %s stats on platform %s", existing.post_id, existing.platform)
