"""Historical candle fetcher: backfills gaps and dedups before persisting."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Candle
from app.exchanges.base import BaseExchange
from app.market_data.gaps import find_gaps
from app.market_data.normalizer import normalize_ohlcv
from app.market_data.timeframes import timeframe_seconds


class CandleFetcher:
    """Fetches OHLCV via an exchange adapter and stores new candles only.

    Existing candles are never overwritten; only timestamps missing from the
    requested window are fetched, so re-runs are idempotent.
    """

    def __init__(self, exchange: BaseExchange, db: AsyncSession, page_limit: int = 500) -> None:
        self._exchange = exchange
        self._db = db
        self._page_limit = page_limit

    async def _existing_ts(self, symbol_id: int, timeframe: str, start: int, end: int) -> set[int]:
        result = await self._db.execute(
            select(Candle.ts).where(
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.ts >= start,
                Candle.ts <= end,
            )
        )
        return set(result.scalars().all())

    async def backfill(
        self,
        symbol_id: int,
        exchange_symbol: str,
        timeframe: str,
        start: int,
        end: int,
    ) -> int:
        """Fetch and persist any candles missing in [start, end]. Returns count."""
        step = timeframe_seconds(timeframe)
        existing = await self._existing_ts(symbol_id, timeframe, start, end)
        gaps = find_gaps(start, end, timeframe, existing)
        inserted = 0
        for gap_start, gap_end in gaps:
            cursor = gap_start
            while cursor <= gap_end:
                raw = await self._exchange.fetch_ohlcv(
                    exchange_symbol, timeframe, limit=self._page_limit
                )
                candles = [
                    c
                    for c in normalize_ohlcv(raw)
                    if gap_start <= c["ts"] <= gap_end and c["ts"] not in existing
                ]
                if not candles:
                    break
                for c in candles:
                    self._db.add(
                        Candle(
                            symbol_id=symbol_id,
                            timeframe=timeframe,
                            ts=c["ts"],
                            o=c["o"],
                            h=c["h"],
                            l=c["l"],
                            c=c["c"],
                            v=c["v"],
                        )
                    )
                    existing.add(c["ts"])
                    inserted += 1
                cursor = max(c["ts"] for c in candles) + step
        if inserted:
            await self._db.commit()
        return inserted
