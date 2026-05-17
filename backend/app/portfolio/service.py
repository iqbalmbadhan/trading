"""Portfolio aggregation: holdings, allocation, exposure, correlation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Candle, Position, Symbol
from app.portfolio.correlation import correlation_matrix, returns_from_closes
from app.portfolio.valuation import (
    allocation,
    exposure_by_base,
    total_value_usd,
    value_holdings,
)

PriceProvider = Callable[[str], Awaitable[float]]


async def _positions(db: AsyncSession, user_id: int) -> list[dict]:
    rows = (await db.execute(select(Position).where(Position.user_id == user_id))).scalars().all()
    return [
        {"symbol": p.symbol, "qty": p.qty, "side": p.side, "is_paper": p.is_paper} for p in rows
    ]


async def portfolio_summary(db: AsyncSession, user_id: int, price_provider: PriceProvider) -> dict:
    positions = await _positions(db, user_id)
    prices: dict[str, float] = {}
    for p in positions:
        if p["symbol"] not in prices:
            try:
                prices[p["symbol"]] = await price_provider(p["symbol"])
            except Exception:
                prices[p["symbol"]] = 0.0
    holdings = value_holdings(positions, prices)
    return {
        "total_value_usd": total_value_usd(holdings),
        "holdings": [
            {
                "symbol": h.symbol,
                "base": h.base,
                "qty": h.qty,
                "price_usd": h.price_usd,
                "value_usd": h.value_usd,
                "is_paper": h.is_paper,
            }
            for h in holdings
        ],
        "allocation": allocation(holdings),
        "exposure_by_base": exposure_by_base(holdings),
    }


async def portfolio_correlation(
    db: AsyncSession, user_id: int, *, timeframe: str = "1h", lookback: int = 200
) -> dict[str, dict[str, float | None]]:
    positions = await _positions(db, user_id)
    symbols = sorted({p["symbol"] for p in positions})
    returns: dict[str, list[float]] = {}
    for sym in symbols:
        s = (await db.execute(select(Symbol).where(Symbol.symbol == sym))).scalars().first()
        if s is None:
            continue
        rows = (
            (
                await db.execute(
                    select(Candle)
                    .where(Candle.symbol_id == s.id, Candle.timeframe == timeframe)
                    .order_by(Candle.ts.desc())
                    .limit(lookback)
                )
            )
            .scalars()
            .all()
        )
        closes = [r.c for r in reversed(rows)]
        if len(closes) >= 2:
            returns[sym] = returns_from_closes(closes)
    return correlation_matrix(returns)
