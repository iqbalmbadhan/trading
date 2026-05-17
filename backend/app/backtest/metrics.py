"""Backtest performance metrics computed from an equity curve and trades."""

from __future__ import annotations

import math


def _returns(equity: list[float]) -> list[float]:
    out = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        out.append((equity[i] - prev) / prev if prev else 0.0)
    return out


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1.0)
    return mdd  # negative or zero


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def compute_metrics(
    equity_curve: list[tuple[int, float]],
    trade_pnls: list[float],
    *,
    periods_per_year: float,
    exposure_flags: list[bool] | None = None,
    traded_notional: float = 0.0,
) -> dict[str, float]:
    if len(equity_curve) < 2:
        return {"total_return": 0.0, "trades": float(len(trade_pnls))}

    equity = [e for _, e in equity_curve]
    start, end = equity[0], equity[-1]
    n = len(equity) - 1
    rets = _returns(equity)

    total_return = end / start - 1.0 if start else 0.0
    cagr = (end / start) ** (periods_per_year / n) - 1.0 if start > 0 and end > 0 else 0.0

    mean_r = sum(rets) / len(rets) if rets else 0.0
    sd = _std(rets)
    sharpe = (mean_r / sd) * math.sqrt(periods_per_year) if sd > 0 else 0.0
    downside = _std([r for r in rets if r < 0])
    sortino = (mean_r / downside) * math.sqrt(periods_per_year) if downside > 0 else 0.0

    mdd = _max_drawdown(equity)
    calmar = cagr / abs(mdd) if mdd < 0 else 0.0

    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    n_trades = len(trade_pnls)
    win_rate = len(wins) / n_trades if n_trades else 0.0
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else 0.0
    avg_win = gross_win / len(wins) if wins else 0.0
    avg_loss = -gross_loss / len(losses) if losses else 0.0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

    exposure = sum(1 for f in exposure_flags if f) / len(exposure_flags) if exposure_flags else 0.0
    avg_equity = sum(equity) / len(equity)
    turnover = traded_notional / avg_equity if avg_equity > 0 else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": mdd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "exposure": exposure,
        "turnover": turnover,
        "trades": float(n_trades),
    }
