"""Dollar-cost averaging with optional dip-buying."""

from __future__ import annotations

from pydantic import Field

from app.strategies.base import (
    BaseStrategy,
    Candle,
    Signal,
    SignalSide,
    StrategyContext,
    StrategyParams,
)


class DCAParams(StrategyParams):
    interval_candles: int = Field(default=24, ge=1, le=10_000)
    base_qty: float = Field(default=1.0, gt=0)
    dip_pct: float = Field(default=0.0, ge=0, le=0.9)
    dip_extra_qty: float = Field(default=0.0, ge=0)


class DCA(BaseStrategy):
    """Buy a fixed size every N candles; optionally buy extra on dips."""

    Params = DCAParams
    required_timeframes = ("1h",)
    required_indicators = ()
    param_ranges = {"interval_candles": (6, 48, 6)}

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.update(count=0, last_buy_price=None)

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: DCAParams = self.params
        ctx.state["count"] += 1
        signals: list[Signal] = []

        if ctx.state["count"] % p.interval_candles == 0:
            signals.append(
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.BUY,
                    qty=p.base_qty,
                    metadata={"kind": "scheduled"},
                )
            )

        last = ctx.state["last_buy_price"]
        if (
            p.dip_pct > 0
            and p.dip_extra_qty > 0
            and last is not None
            and candle.c <= last * (1 - p.dip_pct)
        ):
            signals.append(
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.BUY,
                    qty=p.dip_extra_qty,
                    metadata={"kind": "dip"},
                )
            )

        if signals:
            ctx.state["last_buy_price"] = candle.c
        return signals
