"""Redis-backed stop control for running strategies.

A strategy run is stopped by setting a Redis key the runner polls. This is
the same mechanism the global kill switch (Phase 6) will trip.
"""

from __future__ import annotations

import redis

from app.core.config import get_settings


def _run_key(run_id: int) -> str:
    return f"strategy:stop:{run_id}"


class RedisStopController:
    def __init__(self, run_id: int, client: redis.Redis | None = None) -> None:
        self._run_id = run_id
        self._client = client or redis.Redis.from_url(get_settings().redis_url)

    def request_stop(self) -> None:
        self._client.set(_run_key(self._run_id), "1")

    def clear(self) -> None:
        self._client.delete(_run_key(self._run_id))

    def is_stopped(self) -> bool:
        return self._client.exists(_run_key(self._run_id)) == 1
