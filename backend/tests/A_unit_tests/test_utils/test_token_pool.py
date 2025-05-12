import time
from backend.utils.token_pool import TokenPool


def test_token_pool_ban_and_cooldown():
    """Test that a banned token is not returned until the cooldown expires."""
    pool = TokenPool(["a", "b", "c"])
    pool.cooldown = 1

    # Tokens are returned in round-robin order
    assert pool.get_token() == "a"
    assert pool.get_token() == "b"
    assert pool.get_token() == "c"
    assert pool.get_token() == "a"

    # Ban token "b" and check it is not returned
    pool.ban_token("b")
    tokens = [pool.get_token() for _ in range(5)]
    assert "b" not in tokens

    # After cooldown: "b" should be available again
    time.sleep(1.1)
    tokens_after_cooldown = [pool.get_token() for _ in range(6)]
    assert "b" in tokens_after_cooldown


def test_token_pool_all_banned():
    """Test that if all tokens are banned, None is returned and after cooldown the token is available again."""
    pool = TokenPool(["x"])
    pool.cooldown = 1
    pool.ban_token("x")
    assert pool.get_token() is None
    time.sleep(1.1)
    assert pool.get_token() == "x"


def test_token_pool_round_robin():
    """Test that tokens are returned in round-robin order if none are banned."""
    pool = TokenPool(["a", "b"])
    assert pool.get_token() == "a"
    assert pool.get_token() == "b"
    assert pool.get_token() == "a"
    assert pool.get_token() == "b"


def test_token_pool_ban_nonexistent_token():
    """Test that banning a token not in the pool does not cause errors and does not affect the pool."""
    pool = TokenPool(["a", "b"])
    pool.ban_token("c")
    assert set([pool.get_token(), pool.get_token()]) == {"a", "b"}


def test_token_pool_multiple_bans_and_releases():
    """Test banning all tokens, waiting for cooldown, and then all tokens are available again."""
    pool = TokenPool(["a", "b", "c"])
    pool.cooldown = 1
    pool.ban_token("a")
    pool.ban_token("b")
    assert pool.get_token() == "c"
    assert pool.get_token() == "c"
    pool.ban_token("c")
    assert pool.get_token() is None
    time.sleep(1.1)
    tokens = [pool.get_token() for _ in range(3)]
    assert set(tokens) == {"a", "b", "c"}


def test_token_pool_no_tokens():
    """Test that if the pool is empty."""
    pool = TokenPool([])
    assert pool.get_token() is None
    pool.ban_token("any")
