"""Market data read endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Symbol, User
from app.db.session import get_db
from app.market_data.service import query_candles

router = APIRouter(prefix="/api/v1/markets", tags=["markets"])


class SymbolOut(BaseModel):
    id: int
    exchange: str
    symbol: str
    base: str
    quote: str
    contract_type: str


class CandleOut(BaseModel):
    ts: int
    o: float
    h: float
    l: float
    c: float
    v: float


@router.get("/symbols", response_model=list[SymbolOut])
async def list_symbols(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[SymbolOut]:
    rows = (await db.execute(select(Symbol))).scalars().all()
    return [
        SymbolOut(
            id=s.id,
            exchange=s.exchange,
            symbol=s.symbol,
            base=s.base,
            quote=s.quote,
            contract_type=s.contract_type,
        )
        for s in rows
    ]


@router.get("/candles", response_model=list[CandleOut])
async def get_candles(
    symbol_id: int,
    timeframe: str = "1m",
    start: int | None = Query(default=None),
    end: int | None = Query(default=None),
    limit: int = Query(default=1000, le=5000),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CandleOut]:
    candles = await query_candles(db, symbol_id, timeframe, start, end, limit)
    return [CandleOut(ts=c.ts, o=c.o, h=c.h, l=c.l, c=c.c, v=c.v) for c in candles]
