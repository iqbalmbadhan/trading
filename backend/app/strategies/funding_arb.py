"""Single-exchange funding-rate arbitrage (perp vs spot).

When the perpetual funding rate is sufficiently positive, shorts are paid;
this strategy goes short the perp (the long-spot leg is assumed to hedge it
delta-neutral off-strategy) and unwinds when funding normalizes. The current
funding rate is supplied by the data layer via ``ctx.state['funding_rate']``.
"""

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


class FundingArbParams(StrategyParams):
    entry_rate: float = Field(default=0.0005, gt=0, le=1)
    exit_rate: float = Field(default=0.0, ge=-1, le=1)
    trade_qty: float = Field(default=1.0, gt=0)


class FundingArb(BaseStrategy):
    Params = FundingArbParams
    required_timeframes = ("1h",)
    required_indicators = ()
    param_ranges = {"entry_rate": (0.0002, 0.001, 0.0002)}

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.setdefault("funding_rate", 0.0)
        ctx.state["short"] = False

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: FundingArbParams = self.params
        rate = float(ctx.state.get("funding_rate", 0.0))

        if not ctx.state["short"] and rate >= p.entry_rate:
            ctx.state["short"] = True
            return [
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.SELL,
                    qty=p.trade_qty,
                    metadata={"funding_rate": rate, "leg": "open_short_perp"},
                )
            ]
        if ctx.state["short"] and rate <= p.exit_rate:
            ctx.state["short"] = False
            return [
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.BUY,
                    qty=p.trade_qty,
                    metadata={"funding_rate": rate, "leg": "close_short_perp"},
                )
            ]
        return []
