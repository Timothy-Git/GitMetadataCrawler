import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.utils.token_pool import TokenPool
from backend.fetchers.base_graphql_fetcher import BaseGraphQLFetcher


class DummyFetcher(BaseGraphQLFetcher):
    def build_query(self, fetch_settings, fields):
        return ""


@pytest.mark.asyncio
async def test_retry_on_rate_limit(monkeypatch):
    """Test that a token is banned and retried on rate limit error."""
    pool = TokenPool(["token1", "token2"])
    fetcher = DummyFetcher(token_pool=pool)
    fetcher.client = MagicMock()

    # Simulate rate limit error in response
    response_mock = MagicMock()
    response_mock.raise_for_status.return_value = None
    response_mock.json.return_value = {
        "errors": [{"message": "API rate limit exceeded"}]
    }

    fetcher.client.post = AsyncMock(return_value=response_mock)

    with patch.object(fetcher, "_is_retryable_error", return_value=False):
        with pytest.raises(RuntimeError, match="All tokens failed"):
            await fetcher._make_request("url", "query")

    # token1 should be banned, token2 should also be tried and banned
    assert "token1" in pool.banned
    assert "token2" in pool.banned


@pytest.mark.asyncio
async def test_retry_on_auth_error(monkeypatch):
    """Test that a token is banned and retried on authentication error."""
    pool = TokenPool(["tokenA", "tokenB"])
    fetcher = DummyFetcher(token_pool=pool)
    fetcher.client = MagicMock()

    # Simulate authentication error in response
    response_mock = MagicMock()
    response_mock.raise_for_status.return_value = None
    response_mock.json.return_value = {"errors": [{"message": "Authentication failed"}]}

    fetcher.client.post = AsyncMock(return_value=response_mock)

    with patch.object(fetcher, "_is_retryable_error", return_value=False):
        with pytest.raises(RuntimeError, match="All tokens failed"):
            await fetcher._make_request("url", "query")

    assert "tokenA" in pool.banned
    assert "tokenB" in pool.banned


@pytest.mark.asyncio
async def test_no_ban_on_network_error(monkeypatch):
    """Test that a network error does not ban the token, just retries."""
    pool = TokenPool(["tokenX", "tokenY"])
    fetcher = DummyFetcher(token_pool=pool)
    fetcher.client = MagicMock()

    # Simulate network error (e.g. timeout)
    async def raise_network_error(*args, **kwargs):
        raise Exception("Network error")

    fetcher.client.post = AsyncMock(side_effect=raise_network_error)

    with patch.object(fetcher, "_is_retryable_error", return_value=True):
        with pytest.raises(RuntimeError, match="All tokens failed"):
            await fetcher._make_request("url", "query")

    # Tokens should NOT be banned
    assert not pool.banned


@pytest.mark.asyncio
async def test_success_on_second_token(monkeypatch):
    """Test that if the first token fails but the second succeeds, the result is returned."""
    pool = TokenPool(["token1", "token2"])
    fetcher = DummyFetcher(token_pool=pool)
    fetcher.client = MagicMock()

    # First call returns error, second call returns success
    response_error = MagicMock()
    response_error.raise_for_status.return_value = None
    response_error.json.return_value = {
        "errors": [{"message": "API rate limit exceeded"}]
    }

    response_success = MagicMock()
    response_success.raise_for_status.return_value = None
    response_success.json.return_value = {"data": {"ok": True}}

    fetcher.client.post = AsyncMock(side_effect=[response_error, response_success])

    with patch.object(fetcher, "_is_retryable_error", return_value=False):
        result = await fetcher._make_request("url", "query")
        assert result == {"data": {"ok": True}}
        assert "token1" in pool.banned
        assert "token2" not in pool.banned
