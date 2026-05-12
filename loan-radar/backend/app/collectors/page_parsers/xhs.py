"""小红书页面解析器 - 解析小红书笔记和评论"""

from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

from app.collectors.base import CollectedComment, CollectedPost, CollectorResult
from app.collectors.page_parsers.base import BasePageParser


class XhsPageParser(BasePageParser):
    """
    小红书页面解析器 - 支持解析小红书笔记列表和详情页面
    
    处理小红书特定的数据结构和反爬虫限制
    """

    # 小红书常用 CSS 选择器
    DEFAULT_SELECTORS = {
        "note_container": "div[class*='feed-item'], article, div[data-testid='feed-item'], div[class*='note-item']",
        "title": "h2, h3, .title, a[class*='title'], span[class*='title']",
        "content": "p, div[class*='desc'], div[class*='content'], span[class*='content']",
        "author": ".author, .user-name, span[class*='author'], a[class*='user']",
        "publish_time": "span[class*='time'], time, .publish-time",
        "comment_item": "div[class*='comment'], .comment-item, div[data-testid='comment']",
    }

    def __init__(
        self,
        platform: str = "xhs",
        max_comments_per_post: int = 50,
        selectors: dict[str, str] | None = None,
        max_posts: int = 20,
    ) -> None:
        self.platform = platform
        self.max_comments_per_post = max(0, min(max_comments_per_post, 100))
        # 合并自定义选择器和默认选择器
        self.selectors = {**self.DEFAULT_SELECTORS}
        if selectors:
            self.selectors.update(selectors)
        self.max_posts = max_posts

    async def parse(
        self,
        page: Any,
        source_url: str,
        platform: str,
        browser_channel: str,
        cookies: str | None = None,
        max_posts: int = 20,
        max_comments_per_post: int = 50,
    ) -> CollectorResult:
        """
        解析小红书页面内容
        
        Args:
            page: Playwright 页面对象
            source_url: 页面 URL
            platform: 平台名称
            browser_channel: 浏览器类型
            cookies: 小红书 cookie（用于认证）
            max_posts: 最大笔记数
            max_comments_per_post: 每条笔记最大评论数
            
        Returns:
            CollectorResult
        """
        now = datetime.now(timezone.utc)
        
        # 使用默认或自定义选择器
        used_selectors = {**self.DEFAULT_SELECTORS}
        if self.selectors:
            used_selectors.update(self.selectors)
        
        posts = []
        comments_list = []
        
        # 获取所有笔记容器
        note_selector = used_selectors.get("note_container", "div[class*='feed-item']")
        note_selectors = [s.strip() for s in note_selector.split(",")]
        
        post_count = 0
        
        for container_selector in note_selectors:
            if post_count >= max_posts:
                break
            
            try:
                elements = page.locator(container_selector)
                count = await elements.count()
                
                if count == 0:
                    continue
                
                for index in range(min(count, max_posts - post_count)):
                    try:
                        element = elements.nth(index)
                        
                        # 提取标题
                        title = await self._extract_text_from_element(
                            element,
                            used_selectors.get("title", "h2"),
                        )
                        
                        # 提取内容
                        content = await self._extract_text_from_element(
                            element,
                            used_selectors.get("content", "p"),
                        )
                        
                        # 提取作者
                        author = await self._extract_text_from_element(
                            element,
                            used_selectors.get("author", ".author"),
                        )
                        
                        # 提取发布时间（如果可用）
                        publish_time_str = await self._extract_text_from_element(
                            element,
                            used_selectors.get("publish_time", "span[class*='time']"),
                        )
                        
                        # 跳过空笔记
                        if not title and not content:
                            continue
                        
                        # 生成 post_id（基于 URL 和索引）
                        post_id = f"xhs-{sha1((source_url + str(index)).encode('utf-8')).hexdigest()[:16]}"
                        
                        raw_data = {
                            "collector": "xhs",
                            "source_url": source_url,
                            "parser": self.__class__.__name__,
                            "browser_channel": browser_channel,
                            "container_selector": container_selector,
                            "cookies_used": bool(cookies),
                        }
                        
                        post = CollectedPost(
                            platform=platform,
                            post_id=post_id,
                            title=title or "Untitled",
                            content=content or "",
                            post_url=source_url,
                            author_name=author or "Unknown",
                            publish_time=now,
                            raw_data=raw_data,
                        )
                        posts.append(post)
                        post_count += 1
                        
                        # 提取该笔记的评论
                        comments = await self._extract_comments_from_element(
                            element,
                            post_id,
                            platform,
                            used_selectors.get("comment_item", "div[class*='comment']"),
                            max_comments_per_post,
                            raw_data,
                            now,
                        )
                        comments_list.extend(comments)
                        
                        if post_count >= max_posts:
                            break
                    except Exception:
                        continue
            except Exception:
                continue
        
        if not posts:
            raise RuntimeError(
                "no posts extracted from xiaohongshu page; check selectors, cookies, or page content"
            )
        
        return CollectorResult(
            posts=posts,
            comments=comments_list,
            metadata={
                "source": "xhs",
                "total_posts": len(posts),
                "total_comments": len(comments_list),
                "selectors_used": used_selectors,
                "cookies_provided": bool(cookies),
            },
        )

    async def _extract_text_from_element(
        self,
        element: Any,
        selectors_str: str,
    ) -> str | None:
        """从元素中提取文本"""
        selectors = [s.strip() for s in selectors_str.split(",")]
        
        for selector in selectors:
            try:
                locator = element.locator(selector).first
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
                comment_elements = element.locator(selector)
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


# 为了向后兼容，导出别名
XhsPostParser = XhsPageParser
