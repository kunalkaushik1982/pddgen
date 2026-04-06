r"""Redis implementation of `DistributedLockPort` (decoupled from Celery result backend)."""

from __future__ import annotations

import redis

from app.core.config import Settings
from app.portability.job_messaging.protocols import DistributedLockPort


class RedisDistributedLockAdapter(DistributedLockPort):
    __slots__ = ("_client",)

    def __init__(self, *, redis_client: redis.Redis) -> None:
        self._client = redis_client

    def try_acquire(self, key: str, *, ttl_seconds: int) -> bool:
        return bool(self._client.set(key, "1", nx=True, ex=ttl_seconds))

    def release(self, key: str) -> None:
        self._client.delete(key)

    @staticmethod
    def redis_client_from_settings(settings: Settings) -> redis.Redis:
        url = (settings.lock_redis_url or settings.redis_url).strip()
        return redis.from_url(url, decode_responses=True)


def build_redis_distributed_lock(settings: Settings) -> RedisDistributedLockAdapter:
    return RedisDistributedLockAdapter(redis_client=RedisDistributedLockAdapter.redis_client_from_settings(settings))
