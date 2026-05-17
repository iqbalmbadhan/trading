"""Phase 5: execute_run persists signals and finalizes the run."""

import os
import tempfile

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Signal as SignalRow
from app.db.models import Strategy, StrategyRun
from app.exchanges.base import Ticker
from app.exchanges.paper import PaperExchange
from app.strategies.run import execute_run


class FakeDataExchange:
    def __init__(self, closes):
        self.rows = [[i * 60_000, c, c + 1, c - 1, c, 1.0] for i, c in enumerate(closes)]

    async def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return list(self.rows)

    async def close(self):
        return None


def _price(p: float):
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=p, ask=p, last=p)

    return _src


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


async def _seed_run(session_factory) -> int:
    async with session_factory() as s:
        strat = Strategy(
            user_id=1,
            name="ma",
            type="ma_crossover",
            params={
                "fast_period": 2,
                "slow_period": 3,
                "atr_period": 2,
                "atr_stop_mult": 2.0,
                "trade_qty": 1.0,
            },
            symbol="BTC/USDT",
            timeframe="1m",
            is_active=True,
        )
        s.add(strat)
        await s.flush()
        run = StrategyRun(strategy_id=strat.id, status="running")
        s.add(run)
        await s.commit()
        return run.id


@pytest.mark.asyncio
async def test_execute_run_persists_signals_and_finalizes(session_factory):
    run_id = await _seed_run(session_factory)
    closes = [10, 10, 10, 10, 20, 20, 20, 20, 10, 10, 10, 10]
    data = FakeDataExchange(closes)
    trade = PaperExchange(_price(15.0), starting_cash=10_000.0, slippage_bps=0.0)

    await execute_run(
        session_factory=session_factory,
        run_id=run_id,
        data_exchange=data,
        trade_exchange=trade,
        max_cycles=1,
    )

    async with session_factory() as s:
        signals = (
            (await s.execute(select(SignalRow).where(SignalRow.strategy_run_id == run_id)))
            .scalars()
            .all()
        )
        assert [sig.side for sig in signals] == ["buy", "sell"]
        run = await s.get(StrategyRun, run_id)
        assert run.status == "stopped"
        assert run.stopped_at is not None and run.error is None
        strat = await s.get(Strategy, run.strategy_id)
        assert strat.is_active is False


@pytest.mark.asyncio
async def test_execute_run_records_errors(session_factory):
    run_id = await _seed_run(session_factory)

    class Boom:
        async def fetch_ohlcv(self, *a, **k):
            raise RuntimeError("exchange down")

        async def close(self):
            return None

    trade = PaperExchange(_price(15.0), starting_cash=1000.0)
    await execute_run(
        session_factory=session_factory,
        run_id=run_id,
        data_exchange=Boom(),
        trade_exchange=trade,
        max_cycles=1,
    )
    async with session_factory() as s:
        run = await s.get(StrategyRun, run_id)
        assert run.status == "error"
        assert "exchange down" in run.error
