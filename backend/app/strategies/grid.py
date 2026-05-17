"""Grid trading with auto-detected range.

The range is taken from the rolling high/low over a lookback window and
divided into evenly spaced bands. Crossing down a band buys; crossing up a
band sells — mean-reverting accumulation within a range.
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


class GridParams(StrategyParams):
    levels: int = Field(default=5, ge=2, le=50)
    range_lookback: int = Field(default=50, ge=5, le=1000)
    trade_qty: float = Field(default=1.0, gt=0)


class GridTrading(BaseStrategy):
    Params = GridParams
    required_timeframes = ("1h",)
    required_indicators = ()
    param_ranges = {"levels": (3, 10, 1), "range_lookback": (20, 100, 20)}

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.update(highs=[], lows=[], closes=[], band=None)

    def _band_index(self, price: float, lower: float, step: float, levels: int) -> int:
        if step <= 0:
            return 0
        idx = int((price - lower) // step)
        return max(0, min(levels - 1, idx))

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: GridParams = self.params
        h, lo, c = ctx.state["highs"], ctx.state["lows"], ctx.state["closes"]
        h.append(candle.h)
        lo.append(candle.l)
        c.append(candle.c)
        if len(c) < p.range_lookback:
            return []

        window_hi = max(h[-p.range_lookback :])
        window_lo = min(lo[-p.range_lookback :])
        rng = window_hi - window_lo
        if rng <= 0:
            return []
        step = rng / p.levels
        idx = self._band_index(candle.c, window_lo, step, p.levels)
        prev = ctx.state["band"]
        ctx.state["band"] = idx
        if prev is None or idx == prev:
            return []

        moved = abs(idx - prev)
        side = SignalSide.BUY if idx < prev else SignalSide.SELL
        return [
            Signal(
                ts=candle.ts,
                symbol=ctx.symbol,
                side=side,
                qty=p.trade_qty * moved,
                metadata={"band": idx, "prev_band": prev},
            )
        ]
