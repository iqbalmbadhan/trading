"""Phase 8: walk-forward optimization."""

import pytest

from app.backtest.engine import BacktestConfig
from app.backtest.walkforward import walk_forward
from app.strategies.base import Candle


def _candles(n: int) -> list[Candle]:
    closes = []
    for i in range(n):
        # Alternating regime so crossovers actually occur.
        closes.append(10.0 + (10.0 if (i // 6) % 2 else 0.0))
    return [Candle(ts=i * 3600, o=c, h=c + 1, l=c - 1, c=c, v=1.0) for i, c in enumerate(closes)]


async def test_walk_forward_folds_and_params():
    candles = _candles(60)
    config = BacktestConfig(symbol="BTC/USDT", timeframe="1h", slippage_bps=0.0)
    folds = await walk_forward("ma_crossover", {"trade_qty": 1.0}, candles, config, folds=3)
    assert len(folds) == 3
    for fr in folds:
        assert "fast_period" in fr.best_params
        assert "sharpe" in fr.out_of_sample
        assert isinstance(fr.in_sample_metric, float)


async def test_walk_forward_needs_enough_data():
    with pytest.raises(ValueError):
        await walk_forward(
            "ma_crossover",
            {},
            _candles(4),
            BacktestConfig(symbol="BTC/USDT", timeframe="1h"),
            folds=4,
        )
