import pytest

from app.collectors.base import CollectionAuthError
from app.collectors.xhs_provider import XhsProvider


def test_xhs_provider_requires_cookies(monkeypatch):
    monkeypatch.delenv("XHS_COOKIES", raising=False)

    with pytest.raises(CollectionAuthError, match="XHS_COOKIES"):
        XhsProvider()
