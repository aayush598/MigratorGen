"""
Redis caching utilities for MigratorGen platform.
Provides get/set, TTL, JSON serialization, and migration result caching.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis

    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis
        from redis import Redis  # noqa: F401

        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Async Redis cache manager with JSON serialization and common patterns.

    Args:
        redis_url: Redis connection URL
        default_ttl: Default TTL in seconds (3600)
        json_serialize: If True, auto-serialize/deserialize JSON
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,
        json_serialize: bool = True,
        prefix: str = "migrator",
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.json_serialize = json_serialize
        self.prefix = prefix
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Get or create Redis client."""
        if self._client is None:
            if not REDIS_AVAILABLE:
                raise ImportError("redis package is required for caching")
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._client

    def _make_key(self, *parts: str) -> str:
        """Build a prefixed cache key from parts."""
        return self.prefix + ":" + ":".join(str(p) for p in parts)

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            if self.json_serialize:
                return json.loads(value)
            return value
        except Exception as e:
            logger.warning("cache_get_error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if not provided)

        Returns:
            True if successful
        """
        try:
            if self.json_serialize:
                value = json.dumps(value)
            ttl = ttl if ttl is not None else self.default_ttl
            await self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning("cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.warning("cache_delete_error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.warning("cache_exists_error", key=key, error=str(e))
            return False

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple keys at once."""
        if not keys:
            return {}
        try:
            values = await self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    if self.json_serialize:
                        result[key] = json.loads(value)
                    else:
                        result[key] = value
            return result
        except Exception as e:
            logger.warning("cache_get_many_error", error=str(e))
            return {}

    async def set_many(
        self,
        mapping: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple keys at once using pipeline."""
        if not mapping:
            return True
        try:
            ttl = ttl if ttl is not None else self.default_ttl
            pipe = self.client.pipeline()
            for key, value in mapping.items():
                if self.json_serialize:
                    value = json.dumps(value)
                pipe.setex(key, ttl, value)
            await pipe.execute()
            return True
        except Exception as e:
            logger.warning("cache_set_many_error", error=str(e))
            return False

    async def increment(self, key: str, amount: int = 1) -> int | None:
        """Increment a counter."""
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.warning("cache_increment_error", key=key, error=str(e))
            return None

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: int | None = None,
    ) -> Any:
        """
        Get from cache or compute and cache.

        Args:
            key: Cache key
            factory: Async function to compute value if not cached
            ttl: TTL in seconds

        Returns:
            Cached or computed value
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory() if callable(factory) else factory
        await self.set(key, value, ttl)
        return value

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "migration:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("cache_clear_pattern_error", pattern=pattern, error=str(e))
            return 0

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Get JSON value, returning None on parse error."""
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Set JSON value."""
        return await self.set(key, value, ttl)

    async def cache_migration_result(
        self,
        key: str,
        result: dict[str, Any],
        ttl: int = 300,
    ) -> bool:
        """Cache a migration result with a 5-minute TTL."""
        return await self.set(f"migration:result:{key}", result, ttl)

    async def get_migration_result(self, key: str) -> dict[str, Any] | None:
        """Get a cached migration result."""
        return await self.get(f"migration:result:{key}")

    async def cache_rule_fingerprint(
        self,
        key: str,
        fingerprint: str,
        ttl: int = 3600,
    ) -> bool:
        """Cache a rule fingerprint."""
        return await self.set(f"rules:fingerprint:{key}", fingerprint, ttl)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self.client.ping()
        except Exception:
            return False


# Global cache instance (lazy-initialized)
_cache: CacheManager | None = None


def get_cache(
    redis_url: str | None = None,
    default_ttl: int = 3600,
) -> CacheManager:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        import os

        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _cache = CacheManager(url, default_ttl)
    return _cache
