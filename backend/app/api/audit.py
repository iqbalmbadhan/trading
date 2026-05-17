"""Audit log and strategy decision log endpoints (read-only)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.audit import service
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditOut(BaseModel):
    id: int
    ts: str
    actor: str
    action: str
    target: str
    before: dict | None
    after: dict | None


class DecisionOut(BaseModel):
    id: int
    ts: int
    symbol: str
    decision: str
    reasoning: dict
    indicators: dict


@router.get("", response_model=list[AuditOut])
async def list_audit(
    action: str | None = Query(default=None),
    target: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AuditOut]:
    rows = await service.list_audit(db, user.id, action=action, target=target)
    return [
        AuditOut(
            id=r.id,
            ts=r.ts.isoformat(),
            actor=r.actor,
            action=r.action,
            target=r.target,
            before=r.before,
            after=r.after,
        )
        for r in rows
    ]


@router.get("/decisions/{strategy_run_id}", response_model=list[DecisionOut])
async def list_decisions(
    strategy_run_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DecisionOut]:
    rows = await service.list_decisions(db, user.id, strategy_run_id)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy run not found")
    return [
        DecisionOut(
            id=d.id,
            ts=d.ts,
            symbol=d.symbol,
            decision=d.decision,
            reasoning=d.reasoning,
            indicators=d.indicators,
        )
        for d in rows
    ]
