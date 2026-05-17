"""Global kill switch.

A single Redis flag (`KILL_SWITCH`) that the execution layer consults
before every order. When set, no new orders may be placed. Tripping it is
the lowest-layer safety control and is independent of the UI.
"""

from __future__ import annotations

from typing import Protocol

import redis

from app.core.config import get_settings

KILL_SWITCH_KEY = "KILL_SWITCH"


class FlagStore(Protocol):
    def set(self, key: str, value: str) -> object: ...
    def delete(self, key: str) -> object: ...
    def exists(self, key: str) -> int: ...
    def get(self, key: str) -> object: ...


class KillSwitch:
    def __init__(self, client: FlagStore | None = None) -> None:
        self._client = client or redis.Redis.from_url(get_settings().redis_url)

    def trip(self, reason: str) -> None:
        self._client.set(KILL_SWITCH_KEY, reason)

    def clear(self) -> None:
        self._client.delete(KILL_SWITCH_KEY)

    def is_active(self) -> bool:
        return self._client.exists(KILL_SWITCH_KEY) == 1

    def reason(self) -> str | None:
        raw = self._client.get(KILL_SWITCH_KEY)
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else str(raw)


class KillSwitchActive(Exception):
    """Raised by the execution layer when an order is attempted while tripped."""
