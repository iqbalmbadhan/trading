"""Drives a strategy over candles and routes its signals to execution."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Protocol

from app.exchanges.base import BaseExchange
from app.execution.paper_executor import ExecutionResult, PaperExecutor
from app.strategies.base import BaseStrategy, Candle, StrategyContext


class StopController(Protocol):
    def is_stopped(self) -> bool: ...


class NeverStop:
    def is_stopped(self) -> bool:
        return False


class StrategyRunner:
    """Feeds candles into a strategy and executes the resulting signals.

    The same object is used for deterministic replay (``run_candles``) and
    for the live polling loop (``run_polling``) so paper and live share one
    code path.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        ctx: StrategyContext,
        executor: PaperExecutor,
    ) -> None:
        self._strategy = strategy
        self._ctx = ctx
        self._executor = executor

    async def run_candles(self, candles: Iterable[Candle]) -> list[ExecutionResult]:
        await self._strategy.on_start(self._ctx)
        results: list[ExecutionResult] = []
        for candle in candles:
            for signal in await self._strategy.on_candle(self._ctx, candle):
                results.append(await self._executor.execute(signal))
        await self._strategy.on_stop(self._ctx)
        return results

    async def run_polling(
        self,
        exchange: BaseExchange,
        exchange_symbol: str,
        timeframe: str,
        stop: StopController | None = None,
        poll_interval_s: float = 1.0,
        max_cycles: int | None = None,
    ) -> list[ExecutionResult]:
        """Poll OHLCV, feed only newly-closed candles, until stopped.

        ``max_cycles`` bounds the loop for tests; production passes None and
        relies on the stop controller (kill switch / manual stop).
        """
        stop = stop or NeverStop()
        await self._strategy.on_start(self._ctx)
        results: list[ExecutionResult] = []
        last_ts = -1
        cycles = 0
        while not stop.is_stopped():
            if max_cycles is not None and cycles >= max_cycles:
                break
            cycles += 1
            raw = await exchange.fetch_ohlcv(exchange_symbol, timeframe, limit=200)
            for row in raw:
                ts = int(row[0]) // 1000
                if ts <= last_ts:
                    continue
                last_ts = ts
                candle = Candle(
                    ts=ts,
                    o=float(row[1]),
                    h=float(row[2]),
                    l=float(row[3]),
                    c=float(row[4]),
                    v=float(row[5]),
                )
                for signal in await self._strategy.on_candle(self._ctx, candle):
                    results.append(await self._executor.execute(signal))
            if stop.is_stopped():
                break
            await asyncio.sleep(poll_interval_s)
        await self._strategy.on_stop(self._ctx)
        return results
