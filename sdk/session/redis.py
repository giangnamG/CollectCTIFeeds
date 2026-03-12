"""Redis-backed bot session store for multi-worker deployments."""

from __future__ import annotations

from dataclasses import asdict
import json

from sdk.botkit.models import BotSession


class RedisSessionStore:
    """Store BotSession records in Redis using JSON serialization."""

    def __init__(
        self,
        redis_url: str,
        *,
        key_prefix: str = "telegram-sdk:bot-session",
        ttl_seconds: int | None = None,
    ) -> None:
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "RedisSessionStore requires the 'redis' package to be installed."
            ) from exc

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> BotSession | None:
        payload = self._client.get(self._namespaced(key))
        if payload is None:
            return None
        data = json.loads(payload)
        return BotSession(**data)

    def save(self, key: str, session: BotSession) -> None:
        payload = json.dumps(asdict(session))
        namespaced = self._namespaced(key)
        if self._ttl_seconds is None:
            self._client.set(namespaced, payload)
            return
        self._client.setex(namespaced, self._ttl_seconds, payload)

    def delete(self, key: str) -> None:
        self._client.delete(self._namespaced(key))

    def _namespaced(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"
