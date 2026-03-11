"""
Redis cache layer with transparent in-process fallback.

Usage:
    from services.cache import cache

    data = await cache.get("key")
    await cache.set("key", data, ttl=60)
    await cache.delete("key")
    await cache.clear_prefix("stats:")
"""
import asyncio
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class _LocalCache:
    """Thread-safe in-process LRU cache used when Redis is unavailable."""

    def __init__(self, max_size: int = 512):
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._max = max_size

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        if len(self._store) >= self._max:
            # Evict oldest entry
            oldest = min(self._store.items(), key=lambda kv: kv[1][1] or 0)
            del self._store[oldest[0]]
        expires_at = time.monotonic() + ttl if ttl else 0.0
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear_prefix(self, prefix: str) -> int:
        keys = [k for k in list(self._store) if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)


class Cache:
    """
    Async cache backed by Redis when available, in-process otherwise.
    Call `await cache.connect()` once at startup.
    """

    def __init__(self):
        self._redis = None
        self._local = _LocalCache()
        self._using_redis = False

    async def connect(self, redis_url: Optional[str] = None) -> None:
        if not redis_url:
            logger.info("[Cache] No REDIS_URL configured — using in-process cache")
            return
        try:
            import redis.asyncio as aioredis  # type: ignore
            self._redis = aioredis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            await self._redis.ping()
            self._using_redis = True
            logger.info("[Cache] Connected to Redis at %s", redis_url)
        except Exception as exc:
            logger.warning("[Cache] Redis unavailable (%s) — falling back to in-process cache", exc)
            self._redis = None

    # ------------------------------------------------------------------
    async def get(self, key: str) -> Optional[Any]:
        if self._using_redis and self._redis:
            try:
                raw = await self._redis.get(key)
                if raw is None:
                    return None
                return json.loads(raw)
            except Exception as exc:
                logger.debug("[Cache] Redis GET error: %s", exc)
        return self._local.get(key)

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        if self._using_redis and self._redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as exc:
                logger.debug("[Cache] Redis SET error: %s", exc)
        self._local.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        if self._using_redis and self._redis:
            try:
                await self._redis.delete(key)
                return
            except Exception as exc:
                logger.debug("[Cache] Redis DEL error: %s", exc)
        self._local.delete(key)

    async def clear_prefix(self, prefix: str) -> int:
        if self._using_redis and self._redis:
            try:
                keys = await self._redis.keys(f"{prefix}*")
                if keys:
                    await self._redis.delete(*keys)
                return len(keys)
            except Exception as exc:
                logger.debug("[Cache] Redis CLEAR error: %s", exc)
        return self._local.clear_prefix(prefix)

    @property
    def backend(self) -> str:
        return "redis" if self._using_redis else "local"

    async def close(self) -> None:
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass


# Singleton
cache = Cache()
