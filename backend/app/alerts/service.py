"""Notification rule persistence and event dispatch."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.channels import get_channel
from app.alerts.rules import Event, format_message, rule_matches
from app.db.models import Notification, NotificationLog


async def list_rules(db: AsyncSession, user_id: int) -> list[Notification]:
    rows = (
        (await db.execute(select(Notification).where(Notification.user_id == user_id)))
        .scalars()
        .all()
    )
    return list(rows)


async def create_rule(
    db: AsyncSession,
    user_id: int,
    *,
    channel: str,
    event_type: str,
    rule: dict,
    config: dict,
) -> Notification:
    get_channel(channel)  # validate channel name
    n = Notification(
        user_id=user_id,
        channel=channel,
        event_type=event_type,
        rule=rule,
        config=config,
        is_enabled=True,
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


async def get_rule(db: AsyncSession, user_id: int, rule_id: int) -> Notification | None:
    n = await db.get(Notification, rule_id)
    if n is None or n.user_id != user_id:
        return None
    return n


async def delete_rule(db: AsyncSession, n: Notification) -> None:
    await db.delete(n)
    await db.commit()


async def update_rule(
    db: AsyncSession,
    n: Notification,
    *,
    rule: dict | None,
    config: dict | None,
    is_enabled: bool | None,
) -> Notification:
    if rule is not None:
        n.rule = rule
    if config is not None:
        n.config = config
    if is_enabled is not None:
        n.is_enabled = is_enabled
    await db.commit()
    await db.refresh(n)
    return n


async def _deliver(
    db: AsyncSession,
    n: Notification,
    message: str,
    event_type: str,
) -> bool:
    status, error = "sent", None
    try:
        await get_channel(n.channel).send(message, n.config)
    except Exception as exc:
        status, error = "failed", str(exc)[:512]
    db.add(
        NotificationLog(
            user_id=n.user_id,
            notification_id=n.id,
            event_type=event_type,
            channel=n.channel,
            message=message[:1024],
            status=status,
            error=error,
        )
    )
    await db.commit()
    return status == "sent"


async def send_test(db: AsyncSession, n: Notification) -> bool:
    return await _deliver(db, n, "Test alert from Trading Bot Platform", "test")


async def dispatch_event(db: AsyncSession, user_id: int, event: Event) -> int:
    """Deliver an event to every matching enabled rule. Returns sent count.

    Best-effort: channel failures are logged, never raised, so trading
    paths that emit events are not disrupted.
    """
    try:
        rows = (
            (
                await db.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.event_type == event.type,
                        Notification.is_enabled.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
    except Exception:
        return 0
    message = format_message(event)
    sent = 0
    for n in rows:
        if rule_matches(event, n.rule) and await _deliver(db, n, message, event.type):
            sent += 1
    return sent


async def history(db: AsyncSession, user_id: int, limit: int = 100) -> list[NotificationLog]:
    rows = (
        (
            await db.execute(
                select(NotificationLog)
                .where(NotificationLog.user_id == user_id)
                .order_by(NotificationLog.id.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)
