"""Two-step live-trading enablement.

Enabling live trading requires typing the exact confirmation phrase. The
platform defaults to paper; this is the only switch that lets a live order
through (see orders API).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.audit.service import record_audit
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/account", tags=["account"])

CONFIRM_PHRASE = "I UNDERSTAND I CAN LOSE MONEY"


class LiveEnableRequest(BaseModel):
    confirm_phrase: str


class LiveStatus(BaseModel):
    live_trading_enabled: bool
    live_enabled_at: str | None = None


@router.get("/live-trading", response_model=LiveStatus)
async def live_status(user: User = Depends(get_current_user)) -> LiveStatus:
    return LiveStatus(
        live_trading_enabled=user.live_trading_enabled,
        live_enabled_at=user.live_enabled_at.isoformat() if user.live_enabled_at else None,
    )


@router.post("/live-trading", response_model=LiveStatus)
async def enable_live(
    payload: LiveEnableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LiveStatus:
    if payload.confirm_phrase != CONFIRM_PHRASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Confirmation phrase must be exactly: "{CONFIRM_PHRASE}"',
        )
    user.live_trading_enabled = True
    user.live_enabled_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    await record_audit(
        db,
        user_id=user.id,
        actor="user",
        action="live_trading.enable",
        target=f"user:{user.id}",
        after={"live_trading_enabled": True},
    )
    return LiveStatus(
        live_trading_enabled=True,
        live_enabled_at=user.live_enabled_at.isoformat(),
    )


@router.delete("/live-trading", response_model=LiveStatus)
async def disable_live(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LiveStatus:
    user.live_trading_enabled = False
    await db.commit()
    await record_audit(
        db,
        user_id=user.id,
        actor="user",
        action="live_trading.disable",
        target=f"user:{user.id}",
        after={"live_trading_enabled": False},
    )
    return LiveStatus(live_trading_enabled=False, live_enabled_at=None)
