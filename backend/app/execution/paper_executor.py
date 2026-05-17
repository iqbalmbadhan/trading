"""Minimal signal -> paper order executor.

Phase 5 only routes paper orders. Risk checks (Phase 6) and live routing
with idempotency/retries (Phase 7) wrap this same interface later.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.exchanges.base import BaseExchange, Order, OrderSide, OrderType
from app.strategies.base import Signal, SignalSide


@dataclass(frozen=True)
class ExecutionResult:
    signal: Signal
    order: Order | None
    skipped_reason: str | None = None


class PaperExecutor:
    def __init__(self, exchange: BaseExchange, default_qty: float = 1.0) -> None:
        self._exchange = exchange
        self._default_qty = default_qty

    async def execute(self, signal: Signal) -> ExecutionResult:
        if signal.side is SignalSide.FLAT:
            return ExecutionResult(signal=signal, order=None, skipped_reason="flat signal")
        side = OrderSide.BUY if signal.side is SignalSide.BUY else OrderSide.SELL
        qty = signal.qty if signal.qty is not None else self._default_qty
        order = await self._exchange.place_order(
            symbol=signal.symbol,
            side=side,
            type=OrderType.MARKET,
            qty=qty,
        )
        return ExecutionResult(signal=signal, order=order)
