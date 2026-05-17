"""RSI mean reversion with a trend (regime) filter."""

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
from app.strategies.indicators import atr, rsi, sma


class RSIMeanReversionParams(StrategyParams):
    rsi_period: int = Field(default=14, ge=2, le=100)
    oversold: float = Field(default=30.0, ge=1, le=49)
    overbought: float = Field(default=70.0, ge=51, le=99)
    trend_period: int = Field(default=200, ge=10, le=1000)
    atr_period: int = Field(default=14, ge=2, le=200)
    atr_stop_mult: float = Field(default=2.0, gt=0, le=20)
    trade_qty: float = Field(default=1.0, gt=0)


class RSIMeanReversion(BaseStrategy):
    """Buy oversold dips only while price is above its long trend SMA."""

    Params = RSIMeanReversionParams
    required_timeframes = ("1h",)
    required_indicators = ("rsi", "sma", "atr")
    param_ranges = {
        "rsi_period": (7, 21, 7),
        "oversold": (20, 35, 5),
        "overbought": (65, 80, 5),
    }

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.update(highs=[], lows=[], closes=[], long=False)

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: RSIMeanReversionParams = self.params
        h, lo, c = ctx.state["highs"], ctx.state["lows"], ctx.state["closes"]
        h.append(candle.h)
        lo.append(candle.l)
        c.append(candle.c)
        if len(c) <= max(p.rsi_period, p.trend_period):
            return []

        r = rsi(c, p.rsi_period)
        trend = sma(c, p.trend_period)
        r_now, r_prev = r[-1], r[-2]
        trend_now = trend[-1]
        if r_now is None or r_prev is None or trend_now is None:
            return []

        in_uptrend = candle.c > trend_now
        if not ctx.state["long"]:
            crossed_up_from_oversold = r_prev <= p.oversold < r_now
            if in_uptrend and crossed_up_from_oversold:
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
                        metadata={"rsi": r_now, "trend": trend_now},
                    )
                ]
        elif r_now >= p.overbought or not in_uptrend:
            ctx.state["long"] = False
            return [
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.SELL,
                    qty=p.trade_qty,
                    metadata={"rsi": r_now},
                )
            ]
        return []
