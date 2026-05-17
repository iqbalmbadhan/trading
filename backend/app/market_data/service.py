"""Symbol registry and candle queries."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Candle, Symbol


async def get_or_create_symbol(
    db: AsyncSession,
    exchange: str,
    symbol: str,
    *,
    contract_type: str = "spot",
) -> Symbol:
    result = await db.execute(
        select(Symbol).where(Symbol.exchange == exchange, Symbol.symbol == symbol)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing
    base, _, quote = symbol.partition("/")
    row = Symbol(
        exchange=exchange,
        symbol=symbol,
        base=base or symbol,
        quote=quote or "",
        contract_type=contract_type,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def query_candles(
    db: AsyncSession,
    symbol_id: int,
    timeframe: str,
    start: int | None = None,
    end: int | None = None,
    limit: int = 1000,
) -> list[Candle]:
    stmt = select(Candle).where(Candle.symbol_id == symbol_id, Candle.timeframe == timeframe)
    if start is not None:
        stmt = stmt.where(Candle.ts >= start)
    if end is not None:
        stmt = stmt.where(Candle.ts <= end)
    stmt = stmt.order_by(Candle.ts).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
