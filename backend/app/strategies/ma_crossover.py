"""Moving-average crossover strategy with ATR-based protective stops."""

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
from app.strategies.indicators import atr, sma


class MACrossoverParams(StrategyParams):
    fast_period: int = Field(default=10, ge=2, le=400)
    slow_period: int = Field(default=30, ge=3, le=1000)
    atr_period: int = Field(default=14, ge=2, le=200)
    atr_stop_mult: float = Field(default=2.0, gt=0, le=20)
    trade_qty: float = Field(default=1.0, gt=0)


class MACrossover(BaseStrategy):
    """Long when fast SMA crosses above slow SMA, exit/short on the reverse.

    Each entry signal carries an ATR-derived protective stop in
    ``stop_price`` so the risk layer can enforce a mandatory stop.
    """

    Params = MACrossoverParams
    required_timeframes = ("1h",)
    required_indicators = ("sma", "atr")
    param_ranges = {
        "fast_period": (5, 50, 5),
        "slow_period": (20, 200, 10),
        "atr_stop_mult": (1.0, 4.0, 0.5),
    }

    def __init__(self, params: MACrossoverParams) -> None:
        if params.fast_period >= params.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        super().__init__(params)

    async def on_start(self, ctx: StrategyContext) -> None:
        ctx.state.update(highs=[], lows=[], closes=[], position=SignalSide.FLAT)

    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        p: MACrossoverParams = self.params
        highs: list[float] = ctx.state["highs"]
        lows: list[float] = ctx.state["lows"]
        closes: list[float] = ctx.state["closes"]
        highs.append(candle.h)
        lows.append(candle.l)
        closes.append(candle.c)

        if len(closes) <= p.slow_period:
            return []

        fast = sma(closes, p.fast_period)
        slow = sma(closes, p.slow_period)
        fast_now, fast_prev = fast[-1], fast[-2]
        slow_now, slow_prev = slow[-1], slow[-2]
        if None in (fast_now, fast_prev, slow_now, slow_prev):
            return []

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now
        if not (crossed_up or crossed_down):
            return []

        atr_series = atr(highs, lows, closes, p.atr_period)
        atr_now = atr_series[-1]
        side = SignalSide.BUY if crossed_up else SignalSide.SELL
        ctx.state["position"] = side

        stop_price: float | None = None
        if atr_now is not None:
            offset = p.atr_stop_mult * atr_now
            stop_price = candle.c - offset if side is SignalSide.BUY else candle.c + offset

        return [
            Signal(
                ts=candle.ts,
                symbol=ctx.symbol,
                side=side,
                qty=p.trade_qty,
                stop_price=stop_price,
                metadata={
                    "fast": fast_now,
                    "slow": slow_now,
                    "atr": atr_now,
                    "close": candle.c,
                },
            )
        ]
