"""
Tests for the Redis cache service (services/cache.py).
All tests use the in-process fallback — no real Redis required.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.cache import Cache, _LocalCache


# ── _LocalCache unit tests ────────────────────────────────────────────────────

class TestLocalCache:
    def test_set_and_get(self):
        c = _LocalCache()
        c.set("k", {"x": 1}, ttl=60)
        assert c.get("k") == {"x": 1}

    def test_miss_returns_none(self):
        c = _LocalCache()
        assert c.get("missing") is None

    def test_ttl_expiry(self):
        import time
        c = _LocalCache()
        # Manually insert an entry with an already-past expiry
        c._store["k"] = ("v", time.monotonic() - 0.001)
        assert c.get("k") is None

    def test_delete(self):
        c = _LocalCache()
        c.set("k", "v", ttl=60)
        c.delete("k")
        assert c.get("k") is None

    def test_clear_prefix(self):
        c = _LocalCache()
        c.set("stats:a", 1, ttl=60)
        c.set("stats:b", 2, ttl=60)
        c.set("other:c", 3, ttl=60)
        removed = c.clear_prefix("stats:")
        assert removed == 2
        assert c.get("stats:a") is None
        assert c.get("other:c") == 3

    def test_max_size_eviction(self):
        c = _LocalCache(max_size=3)
        c.set("a", 1, ttl=60)
        c.set("b", 2, ttl=60)
        c.set("c", 3, ttl=60)
        c.set("d", 4, ttl=60)       # triggers eviction of oldest
        assert len(c._store) == 3


# ── Cache (async wrapper) tests ───────────────────────────────────────────────

class TestCacheAsyncLocalFallback:
    """Tests using in-process cache (no Redis)."""

    @pytest.fixture
    def cache(self):
        return Cache()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        await cache.set("hello", {"v": 42}, ttl=60)
        result = await cache.get("hello")
        assert result == {"v": 42}

    @pytest.mark.asyncio
    async def test_miss_returns_none(self, cache):
        assert await cache.get("nope") is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        await cache.set("k", "v", ttl=60)
        await cache.delete("k")
        assert await cache.get("k") is None

    @pytest.mark.asyncio
    async def test_clear_prefix(self, cache):
        await cache.set("stats:24", {"pass": 10}, ttl=60)
        await cache.set("stats:7",  {"pass": 5},  ttl=60)
        await cache.set("trends:24", [1, 2, 3],    ttl=60)
        count = await cache.clear_prefix("stats:")
        assert count == 2
        assert await cache.get("stats:24") is None
        assert await cache.get("trends:24") == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_connect_no_url_uses_local(self, cache):
        await cache.connect(None)
        assert cache.backend == "local"
        assert not cache._using_redis

    @pytest.mark.asyncio
    async def test_connect_bad_url_falls_back(self, cache):
        """A bad Redis URL should fall back to local without raising."""
        await cache.connect("redis://localhost:1")   # port 1 — nothing listening
        assert cache.backend == "local"

    @pytest.mark.asyncio
    async def test_close_noop_without_redis(self, cache):
        await cache.close()   # should not raise


class TestCacheRedisPath:
    """Test the Redis code path with a mocked aioredis client."""

    @pytest.mark.asyncio
    async def test_redis_get_hit(self):
        cache = Cache()
        import json
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps({"x": 1}))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await cache.connect("redis://fake:6379/0")

        cache._using_redis = True
        cache._redis = mock_redis
        result = await cache.get("mykey")
        assert result == {"x": 1}

    @pytest.mark.asyncio
    async def test_redis_set(self):
        cache = Cache()
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        cache._using_redis = True
        cache._redis = mock_redis

        await cache.set("k", {"v": 99}, ttl=30)
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "k"
        assert args[1] == 30

    @pytest.mark.asyncio
    async def test_redis_error_falls_back_to_local(self):
        """If Redis raises, should fall back to local silently."""
        cache = Cache()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("connection lost"))
        cache._using_redis = True
        cache._redis = mock_redis

        # Pre-populate local cache
        cache._local.set("k", "local_val", ttl=60)
        result = await cache.get("k")
        assert result == "local_val"
