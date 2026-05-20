from app.collectors.page_parsers.base import BasePageParser
from app.collectors.page_parsers.generic import GenericPostParser


class PageParserFactory:
    @staticmethod
    def create(platform: str, max_comments_per_post: int = 50) -> BasePageParser:
        return GenericPostParser(
            platform=platform,
            max_comments_per_post=max_comments_per_post,
        )

