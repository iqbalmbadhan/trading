"""Phase 9: the six additional strategies."""

import math

import pytest

from app.backtest.engine import BacktestConfig, run_backtest_engine
from app.strategies.base import Candle, SignalSide, StrategyContext
from app.strategies.dca import DCA, DCAParams
from app.strategies.funding_arb import FundingArb, FundingArbParams
from app.strategies.grid import GridParams, GridTrading
from app.strategies.registry import STRATEGIES, build_strategy


def _candle(i: int, c: float) -> Candle:
    return Candle(ts=i * 3600, o=c, h=c + 1, l=c - 1, c=c, v=1.0)


async def test_dca_buys_on_schedule_and_on_dip():
    strat = DCA(DCAParams(interval_candles=2, base_qty=1.0, dip_pct=0.1, dip_extra_qty=0.5))
    ctx = StrategyContext(symbol="BTC/USDT", timeframe="1h")
    await strat.on_start(ctx)
    out = []
    prices = [100, 100, 100, 80]  # 4th candle is a >10% dip from last buy (ts2 @100)
    for i, pr in enumerate(prices):
        out.append(await strat.on_candle(ctx, _candle(i, pr)))
    assert out[0] == []  # count 1
    assert [s.side for s in out[1]] == [SignalSide.BUY]  # scheduled at count 2
    assert out[2] == []  # count 3
    kinds = sorted(s.metadata["kind"] for s in out[3])  # count 4: scheduled + dip
    assert kinds == ["dip", "scheduled"]


async def test_funding_arb_opens_short_and_closes():
    strat = FundingArb(FundingArbParams(entry_rate=0.0005, exit_rate=0.0))
    ctx = StrategyContext(symbol="BTC/USDT:USDT", timeframe="1h")
    await strat.on_start(ctx)

    ctx.state["funding_rate"] = 0.001
    s1 = await strat.on_candle(ctx, _candle(0, 100))
    assert [s.side for s in s1] == [SignalSide.SELL]

    ctx.state["funding_rate"] = 0.001  # already short -> no new signal
    assert await strat.on_candle(ctx, _candle(1, 100)) == []

    ctx.state["funding_rate"] = -0.0001  # funding flipped -> unwind
    s3 = await strat.on_candle(ctx, _candle(2, 100))
    assert [s.side for s in s3] == [SignalSide.BUY]


async def test_grid_buys_lower_band_sells_higher_band():
    strat = GridTrading(GridParams(levels=4, range_lookback=5, trade_qty=1.0))
    ctx = StrategyContext(symbol="BTC/USDT", timeframe="1h")
    await strat.on_start(ctx)
    # Establish a ~0..40 range, then move down a band then up several bands.
    seq = [40, 0, 40, 0, 20, 4, 38]
    sides = []
    for i, pr in enumerate(seq):
        for s in await strat.on_candle(ctx, _candle(i, pr)):
            sides.append(s.side)
    assert SignalSide.BUY in sides and SignalSide.SELL in sides


@pytest.mark.parametrize("name", sorted(STRATEGIES))
async def test_every_strategy_runs_in_backtest(name):
    # Oscillating series long enough for default lookbacks (trend=200 etc).
    closes = [100 + 20 * math.sin(i / 9.0) for i in range(320)]
    candles = [_candle(i, c) for i, c in enumerate(closes)]
    strat = build_strategy(name, {})
    result = await run_backtest_engine(
        strat, candles, BacktestConfig(symbol="BTC/USDT", timeframe="1h")
    )
    assert len(result.equity_curve) == len(candles)
    assert "sharpe" in result.metrics


def test_all_strategies_have_default_params_and_ranges():
    for name, klass in STRATEGIES.items():
        params = klass.default_params()
        assert params is not None
        # default params must construct a working strategy
        build_strategy(name, params.model_dump())
