"""Risk rule persistence and kill-switch orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KillSwitchEvent, Position, RiskRule, Strategy, StrategyRun
from app.risk.config import RiskConfig
from app.risk.kill_switch import KillSwitch
from app.strategies.stop import RedisStopController

_GLOBAL = "global"


async def _global_rule(db: AsyncSession, user_id: int) -> RiskRule | None:
    result = await db.execute(
        select(RiskRule).where(RiskRule.user_id == user_id, RiskRule.rule_type == _GLOBAL)
    )
    return result.scalar_one_or_none()


async def get_config(db: AsyncSession, user_id: int) -> RiskConfig:
    rule = await _global_rule(db, user_id)
    if rule is None:
        return RiskConfig()
    return RiskConfig(**rule.params)


async def update_config(db: AsyncSession, user_id: int, config: RiskConfig) -> RiskConfig:
    rule = await _global_rule(db, user_id)
    if rule is None:
        rule = RiskRule(user_id=user_id, rule_type=_GLOBAL, params=config.model_dump())
        db.add(rule)
    else:
        rule.params = config.model_dump()
    await db.commit()
    return config


async def trip_kill_switch(
    db: AsyncSession, user_id: int, reason: str, kill_switch: KillSwitch
) -> KillSwitchEvent:
    """Trip the global switch, log it, and disable the user's strategies."""
    kill_switch.trip(reason)
    event = KillSwitchEvent(user_id=user_id, reason=reason)
    db.add(event)

    result = await db.execute(
        select(StrategyRun)
        .join(Strategy, Strategy.id == StrategyRun.strategy_id)
        .where(Strategy.user_id == user_id, StrategyRun.status == "running")
    )
    for run in result.scalars().all():
        RedisStopController(run.id).request_stop()
        run.status = "stopping"
        run.stopped_at = datetime.now(UTC)

    strategies = await db.execute(
        select(Strategy).where(Strategy.user_id == user_id, Strategy.is_active.is_(True))
    )
    for strategy in strategies.scalars().all():
        strategy.is_active = False

    # Flatten positions: simulated paper positions are cleared directly;
    # live positions are liquidated on-exchange by a worker per account.
    positions = (
        (await db.execute(select(Position).where(Position.user_id == user_id))).scalars().all()
    )
    live_symbols_by_account: dict[int, list[str]] = {}
    for pos in positions:
        if pos.is_paper:
            await db.delete(pos)
        elif pos.exchange_account_id is not None:
            live_symbols_by_account.setdefault(pos.exchange_account_id, []).append(pos.symbol)

    await db.commit()
    await db.refresh(event)

    from app.alerts.rules import Event
    from app.alerts.service import dispatch_event

    await dispatch_event(db, user_id, Event("kill_switch", {"reason": reason}))

    from app.audit.service import record_audit

    await record_audit(
        db,
        user_id=user_id,
        actor="user",
        action="kill_switch.trip",
        target="kill_switch",
        after={"reason": reason},
    )

    if live_symbols_by_account:
        from app.workers.tasks import liquidate_account_task

        for account_id, symbols in live_symbols_by_account.items():
            liquidate_account_task.delay(account_id, symbols)

    return event


async def clear_kill_switch(db: AsyncSession, user_id: int, kill_switch: KillSwitch) -> None:
    kill_switch.clear()
    result = await db.execute(
        select(KillSwitchEvent).where(
            KillSwitchEvent.user_id == user_id,
            KillSwitchEvent.resolved_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for event in result.scalars().all():
        event.resolved_at = now
    await db.commit()
    from app.audit.service import record_audit

    await record_audit(
        db,
        user_id=user_id,
        actor="user",
        action="kill_switch.clear",
        target="kill_switch",
    )


async def list_kill_switch_events(db: AsyncSession, user_id: int) -> list[KillSwitchEvent]:
    result = await db.execute(
        select(KillSwitchEvent)
        .where(KillSwitchEvent.user_id == user_id)
        .order_by(KillSwitchEvent.id.desc())
    )
    return list(result.scalars().all())
