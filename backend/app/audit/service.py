"""Append-only audit log and strategy decision log."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, Decision, Strategy, StrategyRun


async def record_audit(
    db: AsyncSession,
    *,
    user_id: int | None,
    actor: str,
    action: str,
    target: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Append an audit row in its own commit (never blocks the caller).

    The audit log is append-only: callers must not update or delete rows;
    a deletion elsewhere is recorded here as a tombstone (action=*.delete
    with the prior state in `before`).
    """
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                actor=actor,
                action=action,
                target=target,
                before=before,
                after=after,
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()


async def list_audit(
    db: AsyncSession,
    user_id: int,
    *,
    action: str | None = None,
    target: str | None = None,
    limit: int = 200,
) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target:
        stmt = stmt.where(AuditLog.target == target)
    stmt = stmt.order_by(AuditLog.id.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def record_decision(
    db: AsyncSession,
    *,
    strategy_run_id: int,
    ts: int,
    symbol: str,
    decision: str,
    reasoning: dict,
    indicators: dict,
) -> None:
    db.add(
        Decision(
            strategy_run_id=strategy_run_id,
            ts=ts,
            symbol=symbol,
            decision=decision,
            reasoning=reasoning,
            indicators=indicators,
        )
    )


async def list_decisions(
    db: AsyncSession, user_id: int, strategy_run_id: int, limit: int = 500
) -> list[Decision] | None:
    """Decisions for a run, but only if the run belongs to the user."""
    owned = (
        await db.execute(
            select(StrategyRun.id)
            .join(Strategy, Strategy.id == StrategyRun.strategy_id)
            .where(StrategyRun.id == strategy_run_id, Strategy.user_id == user_id)
        )
    ).scalar_one_or_none()
    if owned is None:
        return None
    rows = (
        (
            await db.execute(
                select(Decision)
                .where(Decision.strategy_run_id == strategy_run_id)
                .order_by(Decision.id)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)
