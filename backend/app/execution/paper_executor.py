"""Signal -> paper order executor.

The kill switch is consulted before every order: this executor is the
single chokepoint, so a tripped switch blocks all order placement
regardless of what strategies decide.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.exchanges.base import BaseExchange, Order, OrderSide, OrderType
from app.risk.kill_switch import KillSwitch
from app.strategies.base import Signal, SignalSide


@dataclass(frozen=True)
class ExecutionResult:
    signal: Signal
    order: Order | None
    skipped_reason: str | None = None


class PaperExecutor:
    def __init__(
        self,
        exchange: BaseExchange,
        default_qty: float = 1.0,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        self._exchange = exchange
        self._default_qty = default_qty
        self._kill_switch = kill_switch

    async def execute(self, signal: Signal) -> ExecutionResult:
        if self._kill_switch is not None and self._kill_switch.is_active():
            return ExecutionResult(signal=signal, order=None, skipped_reason="kill switch active")
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
