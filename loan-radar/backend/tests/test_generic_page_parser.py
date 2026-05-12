import asyncio

from app.collectors.page_parsers.generic import GenericPostParser


class FakeLocator:
    def __init__(self, texts):
        self.texts = texts
        self.first = self

    async def count(self):
        return len(self.texts)

    def nth(self, index):
        return FakeLocator([self.texts[index]])

    async def inner_text(self):
        return self.texts[0]


class FakeMouse:
    async def wheel(self, _x, _y):
        return None


class FakePage:
    def __init__(self, comments=None):
        self.mouse = FakeMouse()
        self.selectors = {
            "h1": ["真实帖子标题"],
            "article": ["急用 5 万，征信花了还能贷吗？"],
            "[data-testid='author']": ["真实作者"],
            "[data-testid='comment']": comments if comments is not None else ["急用 5 万怎么办", "同行广告百分百下款"],
        }

    def locator(self, selector):
        return FakeLocator(self.selectors.get(selector, []))

    async def wait_for_timeout(self, _timeout):
        return None


def test_generic_parser_extracts_post_and_comments():
    parser = GenericPostParser(max_comments_per_post=10)

    result = asyncio.run(
        parser.parse(
            page=FakePage(),
            source_url="https://example.com/post/1",
            platform="xhs",
            browser_channel="chromium",
        )
    )

    assert len(result.posts) == 1
    assert result.posts[0].title == "真实帖子标题"
    assert result.posts[0].content == "急用 5 万，征信花了还能贷吗？"
    assert result.posts[0].author_name == "真实作者"
    assert result.posts[0].comment_count == 2
    assert [comment.content for comment in result.comments] == ["急用 5 万怎么办", "同行广告百分百下款"]


def test_generic_parser_allows_public_post_without_comments():
    parser = GenericPostParser(max_comments_per_post=10)

    result = asyncio.run(
        parser.parse(
            page=FakePage(comments=[]),
            source_url="https://example.com/post/1",
            platform="xhs",
            browser_channel="chromium",
        )
    )

    assert len(result.posts) == 1
    assert result.posts[0].comment_count == 0
    assert result.comments == []
