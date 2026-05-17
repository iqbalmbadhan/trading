"""Analytics aggregated from finished backtests."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Backtest

_METRIC_KEYS = (
    "sharpe",
    "sortino",
    "calmar",
    "total_return",
    "win_rate",
    "profit_factor",
    "expectancy",
    "max_drawdown",
)


async def _finished(db: AsyncSession, user_id: int) -> list[Backtest]:
    rows = (
        (
            await db.execute(
                select(Backtest).where(Backtest.user_id == user_id, Backtest.status == "finished")
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def strategy_comparison(db: AsyncSession, user_id: int) -> list[dict]:
    """Per-strategy averages across that strategy's finished backtests."""
    by_type: dict[str, list[Backtest]] = {}
    for bt in await _finished(db, user_id):
        by_type.setdefault(bt.type, []).append(bt)

    out: list[dict] = []
    for stype, runs in sorted(by_type.items()):
        agg = {"type": stype, "backtests": len(runs)}
        for key in _METRIC_KEYS:
            vals = [
                float(r.metrics[key])
                for r in runs
                if isinstance(r.metrics, dict) and key in r.metrics
            ]
            agg[key] = sum(vals) / len(vals) if vals else 0.0
        out.append(agg)
    return out


async def overall_metrics(db: AsyncSession, user_id: int) -> dict:
    runs = await _finished(db, user_id)
    if not runs:
        return {"backtests": 0}
    best = max(
        runs,
        key=lambda r: (
            r.metrics.get("sharpe", float("-inf")) if isinstance(r.metrics, dict) else float("-inf")
        ),
    )
    return {
        "backtests": len(runs),
        "best_backtest_id": best.id,
        "best_sharpe": best.metrics.get("sharpe", 0.0),
        "best_type": best.type,
    }


async def equity_and_drawdown(db: AsyncSession, user_id: int, backtest_id: int) -> dict | None:
    bt = await db.get(Backtest, backtest_id)
    if bt is None or bt.user_id != user_id:
        return None
    curve = [(int(ts), float(v)) for ts, v in bt.equity_curve]
    drawdown: list[list[float]] = []
    peak = curve[0][1] if curve else 0.0
    for ts, v in curve:
        peak = max(peak, v)
        dd = (v / peak - 1.0) if peak > 0 else 0.0
        drawdown.append([ts, dd])
    return {
        "equity_curve": [[ts, v] for ts, v in curve],
        "drawdown": drawdown,
        "metrics": bt.metrics,
    }
