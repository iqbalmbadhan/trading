"""Phase 8: event-driven engine runs the real strategy unchanged."""

from app.backtest.engine import BacktestConfig, run_backtest_engine
from app.strategies.base import Candle
from app.strategies.ma_crossover import MACrossover, MACrossoverParams


def _candles(closes: list[float]) -> list[Candle]:
    return [Candle(ts=i * 3600, o=c, h=c + 1, l=c - 1, c=c, v=1.0) for i, c in enumerate(closes)]


async def test_ma_crossover_backtest_produces_curve_and_trades():
    closes = [10, 10, 10, 10, 20, 20, 20, 20, 10, 10, 10, 10]
    strat = MACrossover(
        MACrossoverParams(fast_period=2, slow_period=3, atr_period=2, trade_qty=1.0)
    )
    result = await run_backtest_engine(
        strat,
        _candles(closes),
        BacktestConfig(symbol="BTC/USDT", timeframe="1h", slippage_bps=0.0, fee_bps=0.0),
    )
    assert len(result.equity_curve) == len(closes)
    # BUY at idx4 then SELL at idx8 -> exactly one closed round-trip.
    assert result.metrics["trades"] == 1.0
    assert "sharpe" in result.metrics
    assert result.final_equity == result.equity_curve[-1][1]


async def test_no_trades_flat_metrics():
    strat = MACrossover(MACrossoverParams(fast_period=2, slow_period=3))
    result = await run_backtest_engine(
        strat,
        _candles([10, 11, 12]),
        BacktestConfig(symbol="BTC/USDT", timeframe="1h"),
    )
    assert result.trade_pnls == []
