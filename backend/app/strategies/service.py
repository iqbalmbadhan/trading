"""Strategy CRUD and run lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit
from app.db.models import Strategy, StrategyRun
from app.strategies.registry import build_strategy
from app.strategies.stop import RedisStopController


class StrategyError(Exception):
    """Raised for invalid strategy operations (bad params, bad state)."""


async def create_strategy(
    db: AsyncSession,
    user_id: int,
    *,
    name: str,
    type: str,
    params: dict,
    symbol: str,
    timeframe: str,
) -> Strategy:
    # Validate params against the strategy schema before persisting.
    try:
        build_strategy(type, params)
    except Exception as exc:
        raise StrategyError(f"Invalid strategy configuration: {exc}") from exc
    strategy = Strategy(
        user_id=user_id,
        name=name,
        type=type,
        params=params,
        symbol=symbol,
        timeframe=timeframe,
        is_paper=True,
        is_active=False,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return strategy


async def list_strategies(db: AsyncSession, user_id: int) -> list[Strategy]:
    result = await db.execute(select(Strategy).where(Strategy.user_id == user_id))
    return list(result.scalars().all())


async def get_strategy(db: AsyncSession, user_id: int, strategy_id: int) -> Strategy | None:
    s = await db.get(Strategy, strategy_id)
    if s is None or s.user_id != user_id:
        return None
    return s


async def update_strategy(
    db: AsyncSession, strategy: Strategy, *, name: str | None, params: dict | None
) -> Strategy:
    if strategy.is_active:
        raise StrategyError("Stop the strategy before editing it")
    if name is not None:
        strategy.name = name
    if params is not None:
        build_strategy(strategy.type, params)  # validate
        strategy.params = params
        strategy.version += 1
    await db.commit()
    await db.refresh(strategy)
    return strategy


async def delete_strategy(db: AsyncSession, strategy: Strategy) -> None:
    if strategy.is_active:
        raise StrategyError("Stop the strategy before deleting it")
    snapshot = {
        "id": strategy.id,
        "name": strategy.name,
        "type": strategy.type,
        "params": strategy.params,
    }
    user_id = strategy.user_id
    sid = strategy.id
    await db.delete(strategy)
    await db.commit()
    await record_audit(
        db,
        user_id=user_id,
        actor="user",
        action="strategy.delete",
        target=f"strategy:{sid}",
        before=snapshot,
    )


async def clone_strategy(db: AsyncSession, strategy: Strategy) -> Strategy:
    copy = Strategy(
        user_id=strategy.user_id,
        name=f"{strategy.name} (copy)",
        type=strategy.type,
        params=dict(strategy.params),
        symbol=strategy.symbol,
        timeframe=strategy.timeframe,
        is_paper=True,
        is_active=False,
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return copy


async def start_strategy(db: AsyncSession, strategy: Strategy) -> StrategyRun:
    if strategy.is_active:
        raise StrategyError("Strategy is already running")
    run = StrategyRun(strategy_id=strategy.id, status="running")
    db.add(run)
    strategy.is_active = True
    await db.commit()
    await db.refresh(run)
    # Clear any stale stop flag before the worker starts polling.
    RedisStopController(run.id).clear()
    from app.workers.tasks import run_strategy_run

    run_strategy_run.delay(run.id)
    from app.core.metrics import STRATEGY_STARTS

    STRATEGY_STARTS.inc()
    await record_audit(
        db,
        user_id=strategy.user_id,
        actor="user",
        action="strategy.start",
        target=f"strategy:{strategy.id}",
        after={"run_id": run.id},
    )
    return run


async def stop_strategy(db: AsyncSession, strategy: Strategy) -> None:
    result = await db.execute(
        select(StrategyRun)
        .where(StrategyRun.strategy_id == strategy.id, StrategyRun.status == "running")
        .order_by(StrategyRun.id.desc())
    )
    for run in result.scalars().all():
        RedisStopController(run.id).request_stop()
        run.status = "stopping"
        run.stopped_at = datetime.now(UTC)
    strategy.is_active = False
    await db.commit()
    await record_audit(
        db,
        user_id=strategy.user_id,
        actor="user",
        action="strategy.stop",
        target=f"strategy:{strategy.id}",
    )
