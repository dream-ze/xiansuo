from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

from app.collectors.base import CollectedComment, CollectedPost, CollectorResult
from app.collectors.page_parsers.base import BasePageParser


class GenericPageParser(BasePageParser):
    """
    通用页面解析器 - 支持自定义 CSS 选择器的页面内容提取
    
    默认选择器适配常见网页结构，但用户可以提供自定义的选择器映射。
    """

    DEFAULT_SELECTORS = {
        "post_container": "article, [data-testid='post'], .post, [class*='post']",
        "title": "h1, h2, [data-testid='title'], .title, [class*='title']",
        "content": "article, main article, [data-testid='content'], .content, main, p",
        "author": "[data-testid='author'], [rel='author'], .author, .user-name, [class*='author']",
        "comment_item": "[data-testid='comment'], .comment-item, .comment, [class*='comment']",
    }

    def __init__(
        self,
        platform: str = "other",
        max_comments_per_post: int = 50,
        selectors: dict[str, str] | None = None,
        max_posts: int = 10,
        max_comments: int = 50,
    ) -> None:
        self.platform = platform
        self.max_comments_per_post = max(0, min(max_comments_per_post, 100))
        # 支持新的初始化参数
        self.selectors = selectors or self.DEFAULT_SELECTORS
        self.max_posts = max_posts
        self.max_comments = max_comments

    async def parse(
        self,
        page: Any,
        source_url: str,
        platform: str,
        browser_channel: str,
        selectors: dict[str, str] | None = None,
        max_posts: int = 10,
        max_comments_per_post: int = 50,
    ) -> CollectorResult:
        """
        解析页面内容
        
        Args:
            page: Playwright 页面对象
            source_url: 页面 URL
            platform: 平台名称
            browser_channel: 浏览器类型
            selectors: 自定义 CSS 选择器映射
            max_posts: 最大笔记数
            max_comments_per_post: 每条笔记的最大评论数
            
        Returns:
            CollectorResult
        """
        now = datetime.now(timezone.utc)
        
        # 合并用户提供的选择器和默认选择器
        custom_selectors = selectors or {}
        used_selectors = {**self.DEFAULT_SELECTORS}
        used_selectors.update(custom_selectors)
        
        posts = []
        comments_list = []

        # 检查是否有多个 post 容器
        post_containers = used_selectors.get("post_container", "article").split(",")
        post_count = 0

        for container_selector in post_containers:
            if post_count >= max_posts:
                break
                
            container_selector = container_selector.strip()
            try:
                elements = page.locator(container_selector)
                count = await elements.count()
                
                if count == 0:
                    continue

                for index in range(min(count, max_posts - post_count)):
                    element = elements.nth(index)
                    
                    # 提取 title
                    title = await self._extract_text_from_element(
                        element,
                        used_selectors.get("title", "h1"),
                        fallback_root=page,
                    )
                    
                    # 提取 content
                    content = await self._extract_text_from_element(
                        element,
                        used_selectors.get("content", "article, main"),
                        fallback_root=page,
                    )
                    
                    # 提取 author
                    author = await self._extract_text_from_element(
                        element,
                        used_selectors.get("author", ".author"),
                        fallback_root=page,
                    )
                    
                    # 跳过空白 post
                    if not title and not content:
                        continue

                    # 生成 post_id
                    post_id = f"generic-{sha1((source_url + str(index)).encode('utf-8')).hexdigest()[:16]}"
                    
                    raw_data = {
                        "collector": "generic_web",
                        "source_url": source_url,
                        "parser": self.__class__.__name__,
                        "browser_channel": browser_channel,
                        "container_selector": container_selector,
                    }
                    
                    post = CollectedPost(
                        platform=platform,
                        post_id=post_id,
                        title=title,
                        content=content,
                        post_url=source_url,
                        author_name=author,
                        publish_time=now,
                        raw_data=raw_data,
                    )
                    posts.append(post)
                    post_count += 1

                    # 提取这个 post 的评论
                    comments = await self._extract_comments_from_element(
                        page,
                        element,
                        post_id,
                        platform,
                        used_selectors.get("comment_item", ".comment"),
                        max_comments_per_post,
                        raw_data,
                        now,
                    )
                    post.comment_count = len(comments)
                    comments_list.extend(comments)
                    
                    if post_count >= max_posts:
                        break

            except Exception:
                continue

        if not posts:
            raise RuntimeError("no posts extracted from page; check selectors or page content")

        return CollectorResult(
            posts=posts,
            comments=comments_list,
            metadata={
                "source": "generic_web",
                "total_posts": len(posts),
                "total_comments": len(comments_list),
                "selectors_used": used_selectors,
            },
        )

    async def _extract_text_from_element(
        self,
        element: Any,
        selectors_str: str,
        fallback_root: Any | None = None,
    ) -> str | None:
        """从元素中提取文本"""
        selectors = [s.strip() for s in selectors_str.split(",")]
        
        for selector in selectors:
            try:
                if hasattr(element, "locator"):
                    locator = element.locator(selector).first
                elif fallback_root is not None and hasattr(fallback_root, "locator"):
                    locator = fallback_root.locator(selector).first
                else:
                    continue
                count = await locator.count()
                if count == 0:
                    continue
                    
                text = (await locator.inner_text()).strip()
                if text:
                    return text[:2000]
            except Exception:
                continue
        
        return None

    async def _extract_comments_from_element(
        self,
        page: Any,
        element: Any,
        post_id: str,
        platform: str,
        comment_selector: str,
        max_comments: int,
        raw_data: dict,
        now: datetime,
    ) -> list[CollectedComment]:
        """从元素中提取评论"""
        comments: list[CollectedComment] = []
        seen: set[str] = set()

        selectors = [s.strip() for s in comment_selector.split(",")]
        
        for selector in selectors:
            try:
                if hasattr(element, "locator"):
                    comment_elements = element.locator(selector)
                elif hasattr(page, "locator"):
                    comment_elements = page.locator(selector)
                else:
                    continue
                count = await comment_elements.count()
                
                if count == 0:
                    continue

                limit = min(count, max_comments)
                for index in range(limit):
                    try:
                        raw_text = await comment_elements.nth(index).inner_text()
                        text = (raw_text or "").strip().replace("\n", " ")
                        
                        if not text or text in seen or len(text) < 2:
                            continue
                        
                        seen.add(text)
                        comment_id = f"{post_id}-c-{len(comments) + 1}"
                        
                        comment = CollectedComment(
                            platform=platform,
                            post_id=post_id,
                            comment_id=comment_id,
                            content=text[:1000],
                            publish_time=now,
                            raw_data=raw_data,
                        )
                        comments.append(comment)
                        
                        if len(comments) >= max_comments:
                            break
                    except Exception:
                        continue

                if comments:
                    break

            except Exception:
                continue

        return comments


# 向后兼容性别名
GenericPostParser = GenericPageParser

