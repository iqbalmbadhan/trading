"""Phase 8: run_backtest persistence."""

import os
import tempfile

import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.backtest.run import run_backtest
from app.db.base import Base
from app.db.models import Backtest, Candle, Symbol


@pytest_asyncio.fixture()
async def session_factory():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    sync_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
    os.unlink(path)


_CLOSES = [10, 10, 10, 10, 20, 20, 20, 20, 10, 10, 10, 10]


async def _seed(session_factory, *, with_candles: bool) -> int:
    async with session_factory() as s:
        if with_candles:
            sym = Symbol(
                exchange="binance",
                symbol="BTC/USDT",
                base="BTC",
                quote="USDT",
            )
            s.add(sym)
            await s.flush()
            for i, c in enumerate(_CLOSES):
                s.add(
                    Candle(
                        symbol_id=sym.id,
                        timeframe="1h",
                        ts=i * 3600,
                        o=c,
                        h=c + 1,
                        l=c - 1,
                        c=c,
                        v=1.0,
                    )
                )
        bt = Backtest(
            user_id=1,
            type="ma_crossover",
            params={"fast_period": 2, "slow_period": 3, "atr_period": 2, "trade_qty": 1.0},
            symbol="BTC/USDT",
            timeframe="1h",
            starting_cash=10_000.0,
        )
        s.add(bt)
        await s.commit()
        return bt.id


async def test_run_backtest_finishes_with_metrics(session_factory):
    bt_id = await _seed(session_factory, with_candles=True)
    await run_backtest(session_factory, bt_id)
    async with session_factory() as s:
        bt = await s.get(Backtest, bt_id)
        assert bt.status == "finished"
        assert bt.error is None
        assert bt.metrics["trades"] == 1.0
        assert len(bt.equity_curve) == len(_CLOSES)
        assert "total_return_p50" in bt.monte_carlo


async def test_run_backtest_errors_without_data(session_factory):
    bt_id = await _seed(session_factory, with_candles=False)
    await run_backtest(session_factory, bt_id)
    async with session_factory() as s:
        bt = await s.get(Backtest, bt_id)
        assert bt.status == "error"
        assert "no candle data" in bt.error
