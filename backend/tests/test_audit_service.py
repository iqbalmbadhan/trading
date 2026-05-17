"""Phase 13: audit + decision log service."""

import os
import tempfile

import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.audit.service import (
    list_audit,
    list_decisions,
    record_audit,
    record_decision,
)
from app.db.base import Base
from app.db.models import Strategy, StrategyRun, User


@pytest_asyncio.fixture()
async def session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    se = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(se)
    se.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()
    os.unlink(path)


async def test_record_and_filter_audit(session):
    u = User(email="x@x.com", password_hash="h")
    session.add(u)
    await session.commit()
    await record_audit(
        session, user_id=u.id, actor="user", action="strategy.start", target="strategy:1"
    )
    await record_audit(
        session, user_id=u.id, actor="user", action="kill_switch.trip", target="kill_switch"
    )
    assert len(await list_audit(session, u.id)) == 2
    only = await list_audit(session, u.id, action="kill_switch.trip")
    assert len(only) == 1 and only[0].target == "kill_switch"


async def test_decision_ownership(session):
    u1 = User(email="a@a.com", password_hash="h")
    u2 = User(email="b@b.com", password_hash="h")
    session.add_all([u1, u2])
    await session.commit()
    strat = Strategy(
        user_id=u1.id,
        name="s",
        type="ma_crossover",
        params={},
        symbol="BTC/USDT",
        timeframe="1h",
    )
    session.add(strat)
    await session.flush()
    run = StrategyRun(strategy_id=strat.id, status="running")
    session.add(run)
    await session.flush()
    await record_decision(
        session,
        strategy_run_id=run.id,
        ts=1,
        symbol="BTC/USDT",
        decision="buy",
        reasoning={"executed": True},
        indicators={"fast": 1.0},
    )
    await session.commit()

    rows = await list_decisions(session, u1.id, run.id)
    assert rows is not None and len(rows) == 1 and rows[0].decision == "buy"
    # A different user cannot read the run's decisions.
    assert await list_decisions(session, u2.id, run.id) is None
