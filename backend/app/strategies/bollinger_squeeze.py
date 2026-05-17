"""Bollinger squeeze breakout: low-volatility coil, then trade the break."""

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
from app.strategies.indicators import atr, bollinger


class BollingerSqueezeParams(StrategyParams):
    bb_period: int = Field(default=20, ge=5, le=200)
    bb_std: float = Field(default=2.0, gt=0.5, le=5)
    squeeze_lookback: int = Field(default=50, ge=5, le=500)
    atr_period: int = Field(default=14, ge=2, le=200)
    atr_stop_mult: float = Field(default=2.0, gt=0, le=20)
    trade_qty: float = Field(default=1.0, gt=0)


class BollingerSqueeze(BaseStrategy):
    """Long when price breaks above the upper band after a volatility squeeze."""

    Params = BollingerSqueezeParams
    required_timeframes = ("1h",)
    required_indicators = ("bollinger", "atr")
    param_ranges = {
        "bb_period": (10, 30, 10),
        "bb_std": (1.5, 3.0, 0.5),
    }

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.update(highs=[], lows=[], closes=[], bandwidths=[], long=False)

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: BollingerSqueezeParams = self.params
        h, lo, c = ctx.state["highs"], ctx.state["lows"], ctx.state["closes"]
        h.append(candle.h)
        lo.append(candle.l)
        c.append(candle.c)
        if len(c) < p.bb_period:
            return []

        mid, upper, lower = bollinger(c, p.bb_period, p.bb_std)
        m, u, low = mid[-1], upper[-1], lower[-1]
        if m is None or m == 0:
            return []
        bandwidth = (u - low) / m
        bws: list[float] = ctx.state["bandwidths"]
        bws.append(bandwidth)

        if not ctx.state["long"]:
            window = bws[-p.squeeze_lookback :]
            was_squeezed = len(window) >= p.squeeze_lookback and bandwidth <= min(window)
            if was_squeezed and candle.c > u:
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
                        metadata={"bandwidth": bandwidth, "upper": u},
                    )
                ]
        elif candle.c < m:
            ctx.state["long"] = False
            return [
                Signal(
                    ts=candle.ts,
                    symbol=ctx.symbol,
                    side=SignalSide.SELL,
                    qty=p.trade_qty,
                    metadata={"mid": m},
                )
            ]
        return []
