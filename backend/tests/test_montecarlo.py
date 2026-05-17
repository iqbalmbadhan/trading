"""Phase 8: Monte Carlo trade resampling."""

from app.backtest.montecarlo import monte_carlo


def test_deterministic_with_seed():
    pnls = [10.0, -5.0, 8.0, -3.0, 12.0]
    a = monte_carlo(pnls, 1000.0, iterations=200, seed=1)
    b = monte_carlo(pnls, 1000.0, iterations=200, seed=1)
    assert a == b


def test_percentiles_ordered():
    pnls = [10.0, -5.0, 8.0, -3.0, 12.0]
    r = monte_carlo(pnls, 1000.0, iterations=500, seed=7)
    assert r["total_return_p05"] <= r["total_return_p50"] <= r["total_return_p95"]
    assert r["max_drawdown_p05"] <= r["max_drawdown_p95"]


def test_empty_trades_returns_zeros():
    r = monte_carlo([], 1000.0)
    assert all(v == 0.0 for v in r.values())
