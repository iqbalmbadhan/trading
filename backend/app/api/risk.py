"""Risk rules and global kill-switch endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.risk import service
from app.risk.config import RiskConfig
from app.risk.kill_switch import KillSwitch

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


def get_kill_switch() -> KillSwitch:
    return KillSwitch()


class TripRequest(BaseModel):
    reason: str = "manual"


class KillSwitchStatus(BaseModel):
    active: bool
    reason: str | None = None


class KillSwitchEventOut(BaseModel):
    id: int
    reason: str
    triggered_at: str
    resolved_at: str | None


@router.get("/rules", response_model=RiskConfig)
async def get_rules(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> RiskConfig:
    return await service.get_config(db, user.id)


@router.put("/rules", response_model=RiskConfig)
async def update_rules(
    config: RiskConfig,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskConfig:
    return await service.update_config(db, user.id, config)


@router.get("/kill-switch-status", response_model=KillSwitchStatus)
async def kill_switch_status(
    _: User = Depends(get_current_user),
    ks: KillSwitch = Depends(get_kill_switch),
) -> KillSwitchStatus:
    return KillSwitchStatus(active=ks.is_active(), reason=ks.reason())


@router.post("/kill-switch", response_model=KillSwitchStatus)
async def trip_kill_switch(
    payload: TripRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ks: KillSwitch = Depends(get_kill_switch),
) -> KillSwitchStatus:
    await service.trip_kill_switch(db, user.id, payload.reason, ks)
    return KillSwitchStatus(active=True, reason=payload.reason)


@router.post("/kill-switch/clear", response_model=KillSwitchStatus)
async def clear_kill_switch(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ks: KillSwitch = Depends(get_kill_switch),
) -> KillSwitchStatus:
    await service.clear_kill_switch(db, user.id, ks)
    return KillSwitchStatus(active=False, reason=None)


@router.get("/kill-switch/events", response_model=list[KillSwitchEventOut])
async def kill_switch_events(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[KillSwitchEventOut]:
    events = await service.list_kill_switch_events(db, user.id)
    return [
        KillSwitchEventOut(
            id=e.id,
            reason=e.reason,
            triggered_at=e.triggered_at.isoformat(),
            resolved_at=e.resolved_at.isoformat() if e.resolved_at else None,
        )
        for e in events
    ]
