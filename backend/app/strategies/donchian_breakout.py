"""Donchian channel breakout (turtle-style) with an opposite-channel exit."""

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
from app.strategies.indicators import atr, donchian


class DonchianBreakoutParams(StrategyParams):
    channel_period: int = Field(default=20, ge=2, le=500)
    exit_period: int = Field(default=10, ge=2, le=500)
    atr_period: int = Field(default=14, ge=2, le=200)
    atr_stop_mult: float = Field(default=2.0, gt=0, le=20)
    trade_qty: float = Field(default=1.0, gt=0)


class DonchianBreakout(BaseStrategy):
    """Go long on a new N-bar high; exit on a new M-bar low."""

    Params = DonchianBreakoutParams
    required_timeframes = ("1h",)
    required_indicators = ("donchian", "atr")
    param_ranges = {
        "channel_period": (10, 40, 10),
        "exit_period": (5, 20, 5),
    }

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.update(highs=[], lows=[], closes=[], long=False)

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: DonchianBreakoutParams = self.params
        h, lo, c = ctx.state["highs"], ctx.state["lows"], ctx.state["closes"]
        h.append(candle.h)
        lo.append(candle.l)
        c.append(candle.c)
        if len(c) <= max(p.channel_period, p.exit_period) + 1:
            return []

        # Use the channel of the *prior* bars so the current bar can break it.
        up_entry = donchian(h[:-1], lo[:-1], p.channel_period)[0][-1]
        low_exit = donchian(h[:-1], lo[:-1], p.exit_period)[1][-1]
        if up_entry is None or low_exit is None:
            return []

        if not ctx.state["long"] and candle.c > up_entry:
            ctx.state["long"] = True
            atr_now = atr(h, lo, c, p.atr_period)[-1]
            stop = candle.c - p.atr_stop_mult * atr_now if atr_now else None
            return [
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.BUY,
                    qty=p.trade_qty,
                    stop_price=stop,
                    metadata={"breakout": up_entry},
                )
            ]
        if ctx.state["long"] and candle.c < low_exit:
            ctx.state["long"] = False
            return [
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.SELL,
                    qty=p.trade_qty,
                    metadata={"exit": low_exit},
                )
            ]
        return []
