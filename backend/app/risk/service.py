"""Risk rule persistence and kill-switch orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KillSwitchEvent, RiskRule, Strategy, StrategyRun
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

    await db.commit()
    await db.refresh(event)
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


async def list_kill_switch_events(db: AsyncSession, user_id: int) -> list[KillSwitchEvent]:
    result = await db.execute(
        select(KillSwitchEvent)
        .where(KillSwitchEvent.user_id == user_id)
        .order_by(KillSwitchEvent.id.desc())
    )
    return list(result.scalars().all())
