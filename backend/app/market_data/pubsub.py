"""Thin Redis pub/sub wrapper for in-process market-data consumers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings


def channel(kind: str, symbol: str) -> str:
    return f"md:{kind}:{symbol}"


class MarketDataBus:
    def __init__(self, client: redis.Redis | None = None) -> None:
        self._client = client or redis.from_url(get_settings().redis_url)

    async def publish(self, kind: str, symbol: str, payload: dict[str, Any]) -> None:
        await self._client.publish(channel(kind, symbol), json.dumps(payload))

    async def subscribe(self, kind: str, symbol: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel(kind, symbol))
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(channel(kind, symbol))
            await pubsub.aclose()

    async def close(self) -> None:
        await self._client.aclose()
