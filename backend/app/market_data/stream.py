"""Live market-data streaming, normalized into the internal format.

Message parsing is kept pure (``parse_binance_kline``) so it is unit-tested
without a network connection. The streamer publishes normalized candles onto
the Redis market-data bus for in-process consumers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from abc import ABC, abstractmethod

import websockets

from app.market_data.pubsub import MarketDataBus


def parse_binance_kline(message: str | dict) -> dict | None:
    """Return a normalized candle dict, or None if the kline is unfinished.

    Binance only-final candles are published; in-progress klines (``x`` is
    False) are ignored so downstream consumers see immutable bars.
    """
    data = json.loads(message) if isinstance(message, str) else message
    k = data.get("k")
    if not k or not k.get("x"):
        return None
    return {
        "symbol": data.get("s", ""),
        "ts": int(k["t"]) // 1000,
        "o": float(k["o"]),
        "h": float(k["h"]),
        "l": float(k["l"]),
        "c": float(k["c"]),
        "v": float(k["v"]),
    }


class MarketDataStream(ABC):
    @abstractmethod
    async def run(self, symbol: str, timeframe: str) -> None:
        """Connect, parse messages, and publish normalized candles."""


class BinanceKlineStream(MarketDataStream):
    BASE = "wss://stream.binance.com:9443/ws"

    def __init__(self, bus: MarketDataBus | None = None) -> None:
        self._bus = bus or MarketDataBus()
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self, symbol: str, timeframe: str) -> None:
        stream = f"{symbol.replace('/', '').lower()}@kline_{timeframe}"
        async with websockets.connect(f"{self.BASE}/{stream}") as ws:
            while not self._stop.is_set():
                with contextlib.suppress(asyncio.TimeoutError):
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    candle = parse_binance_kline(raw)
                    if candle is not None:
                        await self._bus.publish("candle", symbol, candle)
