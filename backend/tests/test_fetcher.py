"""Phase 4: candle backfill is correct and idempotent."""

from app.market_data.fetcher import CandleFetcher
from app.market_data.service import get_or_create_symbol, query_candles


class FakeExchange:
    """Returns a fixed 1m OHLCV page (timestamps in milliseconds)."""

    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = rows
        self.calls = 0

    async def fetch_ohlcv(self, symbol, timeframe, limit=500):
        self.calls += 1
        return list(self.rows)


def _rows(n: int) -> list[list[float]]:
    return [[i * 60_000, 1.0, 2.0, 0.5, 1.5, float(i)] for i in range(n)]


async def test_backfill_inserts_then_is_idempotent(db_session):
    sym = await get_or_create_symbol(db_session, "binance", "BTC/USDT")
    ex = FakeExchange(_rows(5))  # ts 0,60,120,180,240
    fetcher = CandleFetcher(ex, db_session)

    inserted = await fetcher.backfill(sym.id, "BTC/USDT", "1m", 0, 240)
    assert inserted == 5
    stored = await query_candles(db_session, sym.id, "1m", 0, 240)
    assert [c.ts for c in stored] == [0, 60, 120, 180, 240]

    # Re-running fetches nothing new.
    again = await fetcher.backfill(sym.id, "BTC/USDT", "1m", 0, 240)
    assert again == 0
    assert len(await query_candles(db_session, sym.id, "1m", 0, 240)) == 5


async def test_backfill_only_fills_missing(db_session):
    sym = await get_or_create_symbol(db_session, "binance", "ETH/USDT")
    ex = FakeExchange(_rows(4))  # ts 0,60,120,180
    fetcher = CandleFetcher(ex, db_session)

    assert await fetcher.backfill(sym.id, "ETH/USDT", "1m", 0, 60) == 2
    # Extending the window backfills only the new region.
    assert await fetcher.backfill(sym.id, "ETH/USDT", "1m", 0, 180) == 2
    stored = await query_candles(db_session, sym.id, "1m", 0, 180)
    assert [c.ts for c in stored] == [0, 60, 120, 180]


async def test_get_or_create_symbol_is_stable(db_session):
    a = await get_or_create_symbol(db_session, "binance", "BTC/USDT")
    b = await get_or_create_symbol(db_session, "binance", "BTC/USDT")
    assert a.id == b.id
    assert a.base == "BTC" and a.quote == "USDT"
