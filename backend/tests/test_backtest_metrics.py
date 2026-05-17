"""Phase 8: performance metrics."""

import pytest

from app.backtest.metrics import compute_metrics


def test_basic_metrics_on_known_curve():
    curve = [(0, 100.0), (1, 110.0), (2, 105.0), (3, 120.0)]
    trades = [10.0, -5.0, 15.0]
    m = compute_metrics(curve, trades, periods_per_year=252, traded_notional=300.0)

    assert m["total_return"] == pytest.approx(0.2)
    assert m["max_drawdown"] < 0  # 110 -> 105 drawdown
    assert m["win_rate"] == pytest.approx(2 / 3)
    assert m["profit_factor"] == pytest.approx(25.0 / 5.0)
    assert m["expectancy"] == pytest.approx((2 / 3) * 12.5 + (1 / 3) * (-5.0))
    assert m["trades"] == 3.0


def test_flat_curve_has_zero_sharpe():
    curve = [(0, 100.0), (1, 100.0), (2, 100.0)]
    m = compute_metrics(curve, [], periods_per_year=252)
    assert m["sharpe"] == 0.0
    assert m["total_return"] == 0.0


def test_drawdown_value():
    curve = [(0, 100.0), (1, 50.0), (2, 75.0)]
    m = compute_metrics(curve, [], periods_per_year=252)
    assert m["max_drawdown"] == pytest.approx(-0.5)
