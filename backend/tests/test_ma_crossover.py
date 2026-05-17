"""Phase 5: MA crossover signal generation (deterministic)."""

import pytest

from app.strategies.base import Candle, SignalSide, StrategyContext
from app.strategies.ma_crossover import MACrossover, MACrossoverParams


def _ctx() -> StrategyContext:
    return StrategyContext(symbol="BTC/USDT", timeframe="1h")


async def _run(closes: list[float]) -> list:
    strat = MACrossover(
        MACrossoverParams(
            fast_period=2, slow_period=3, atr_period=2, atr_stop_mult=2.0, trade_qty=1.0
        )
    )
    ctx = _ctx()
    await strat.on_start(ctx)
    signals = []
    for i, c in enumerate(closes):
        candle = Candle(ts=i * 3600, o=c, h=c + 1, l=c - 1, c=c, v=1.0)
        signals.extend(await strat.on_candle(ctx, candle))
    return signals


async def test_buy_then_sell_crossovers():
    closes = [10, 10, 10, 10, 20, 20, 20, 20, 10, 10, 10, 10]
    signals = await _run(closes)

    assert [s.side for s in signals] == [SignalSide.BUY, SignalSide.SELL]
    buy, sell = signals
    assert buy.ts == 4 * 3600
    assert sell.ts == 8 * 3600
    # ATR stop sits below entry for longs, above entry for shorts.
    assert buy.stop_price is not None and buy.stop_price < buy.metadata["close"]
    assert sell.stop_price is not None and sell.stop_price > sell.metadata["close"]
    assert buy.qty == 1.0


async def test_no_signal_without_enough_history():
    assert await _run([10, 11, 12]) == []


def test_fast_must_be_below_slow():
    with pytest.raises(ValueError):
        MACrossover(MACrossoverParams(fast_period=30, slow_period=10))


def test_default_params_and_metadata():
    assert MACrossover.default_params().fast_period == 10
    assert "sma" in MACrossover.required_indicators
    assert MACrossover.param_ranges["fast_period"] == (5, 50, 5)
