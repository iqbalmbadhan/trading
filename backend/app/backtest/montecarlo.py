"""Monte Carlo resampling of the trade sequence for confidence intervals."""

from __future__ import annotations

import random


def _percentile(sorted_xs: list[float], p: float) -> float:
    if not sorted_xs:
        return 0.0
    k = (len(sorted_xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_xs) - 1)
    frac = k - lo
    return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac


def monte_carlo(
    trade_pnls: list[float],
    starting_equity: float,
    *,
    iterations: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Resample trades with replacement; return return/drawdown percentiles."""
    if not trade_pnls or starting_equity <= 0:
        return {
            "total_return_p05": 0.0,
            "total_return_p50": 0.0,
            "total_return_p95": 0.0,
            "max_drawdown_p05": 0.0,
            "max_drawdown_p95": 0.0,
        }

    rng = random.Random(seed)
    returns: list[float] = []
    drawdowns: list[float] = []
    n = len(trade_pnls)
    for _ in range(iterations):
        sample = [trade_pnls[rng.randrange(n)] for _ in range(n)]
        equity = starting_equity
        peak = starting_equity
        mdd = 0.0
        for pnl in sample:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                mdd = min(mdd, equity / peak - 1.0)
        returns.append(equity / starting_equity - 1.0)
        drawdowns.append(mdd)

    returns.sort()
    drawdowns.sort()
    return {
        "total_return_p05": _percentile(returns, 0.05),
        "total_return_p50": _percentile(returns, 0.50),
        "total_return_p95": _percentile(returns, 0.95),
        "max_drawdown_p05": _percentile(drawdowns, 0.05),
        "max_drawdown_p95": _percentile(drawdowns, 0.95),
    }
