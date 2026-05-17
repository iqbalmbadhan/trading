"""Alert rule endpoints: CRUD, test send, delivery history."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts import service
from app.alerts.rules import EVENT_TYPES
from app.api.deps import get_current_user
from app.db.models import Notification, User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class RuleCreate(BaseModel):
    channel: str
    event_type: str
    rule: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)


class RuleUpdate(BaseModel):
    rule: dict | None = None
    config: dict | None = None
    is_enabled: bool | None = None


class RuleOut(BaseModel):
    id: int
    channel: str
    event_type: str
    rule: dict
    is_enabled: bool


class LogOut(BaseModel):
    id: int
    event_type: str
    channel: str
    message: str
    status: str
    error: str | None


def _out(n: Notification) -> RuleOut:
    return RuleOut(
        id=n.id,
        channel=n.channel,
        event_type=n.event_type,
        rule=n.rule,
        is_enabled=n.is_enabled,
    )


async def _require(rule_id: int, user: User, db: AsyncSession) -> Notification:
    n = await service.get_rule(db, user.id, rule_id)
    if n is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return n


@router.get("", response_model=list[RuleOut])
async def list_rules(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[RuleOut]:
    return [_out(n) for n in await service.list_rules(db, user.id)]


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: RuleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RuleOut:
    if payload.event_type not in EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event_type. Valid: {', '.join(EVENT_TYPES)}",
        )
    try:
        n = await service.create_rule(
            db,
            user.id,
            channel=payload.channel,
            event_type=payload.event_type,
            rule=payload.rule,
            config=payload.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _out(n)


@router.patch("/{rule_id}", response_model=RuleOut)
async def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RuleOut:
    n = await _require(rule_id, user, db)
    n = await service.update_rule(
        db, n, rule=payload.rule, config=payload.config, is_enabled=payload.is_enabled
    )
    return _out(n)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    n = await _require(rule_id, user, db)
    await service.delete_rule(db, n)
    return None


@router.post("/{rule_id}/test")
async def test_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    n = await _require(rule_id, user, db)
    ok = await service.send_test(db, n)
    return {"sent": ok}


@router.get("/history", response_model=list[LogOut])
async def alert_history(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[LogOut]:
    return [
        LogOut(
            id=log.id,
            event_type=log.event_type,
            channel=log.channel,
            message=log.message,
            status=log.status,
            error=log.error,
        )
        for log in await service.history(db, user.id)
    ]
