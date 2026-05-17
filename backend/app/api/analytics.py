"""Analytics endpoints: aggregate metrics, per-strategy comparison, curves."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import (
    equity_and_drawdown,
    overall_metrics,
    strategy_comparison,
)
from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/metrics")
async def metrics(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    return await overall_metrics(db, user.id)


@router.get("/strategy-comparison")
async def comparison(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    return await strategy_comparison(db, user.id)


@router.get("/equity-curve/{backtest_id}")
async def equity_curve(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await equity_and_drawdown(db, user.id, backtest_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")
    return data
