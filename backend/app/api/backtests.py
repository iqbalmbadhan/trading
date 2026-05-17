"""Backtest endpoints: create (async), inspect, and export artifacts."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.backtest.report import html_report, trades_csv
from app.db.models import Backtest, User
from app.db.session import get_db
from app.strategies.registry import STRATEGIES

router = APIRouter(prefix="/api/v1/backtests", tags=["backtests"])


class BacktestCreate(BaseModel):
    type: str
    params: dict = Field(default_factory=dict)
    symbol: str
    timeframe: str = "1h"
    start_ts: int | None = None
    end_ts: int | None = None
    starting_cash: float = Field(default=10_000.0, gt=0)


class BacktestOut(BaseModel):
    id: int
    type: str
    symbol: str
    timeframe: str
    status: str
    error: str | None
    metrics: dict
    monte_carlo: dict


def _out(b: Backtest) -> BacktestOut:
    return BacktestOut(
        id=b.id,
        type=b.type,
        symbol=b.symbol,
        timeframe=b.timeframe,
        status=b.status,
        error=b.error,
        metrics=b.metrics,
        monte_carlo=b.monte_carlo,
    )


async def _require(backtest_id: int, user: User, db: AsyncSession) -> Backtest:
    b = await db.get(Backtest, backtest_id)
    if b is None or b.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")
    return b


@router.post("", response_model=BacktestOut, status_code=status.HTTP_202_ACCEPTED)
async def create_backtest(
    payload: BacktestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestOut:
    if payload.type not in STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown strategy type '{payload.type}'",
        )
    bt = Backtest(
        user_id=user.id,
        type=payload.type,
        params=payload.params,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        start_ts=payload.start_ts,
        end_ts=payload.end_ts,
        starting_cash=payload.starting_cash,
        status="queued",
    )
    db.add(bt)
    await db.commit()
    await db.refresh(bt)

    from app.workers.tasks import run_backtest_task

    run_backtest_task.delay(bt.id)
    return _out(bt)


@router.get("", response_model=list[BacktestOut])
async def list_backtests(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[BacktestOut]:
    rows = (
        (
            await db.execute(
                select(Backtest).where(Backtest.user_id == user.id).order_by(Backtest.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_out(b) for b in rows]


@router.get("/{backtest_id}", response_model=BacktestOut)
async def get_backtest(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestOut:
    return _out(await _require(backtest_id, user, db))


@router.get("/{backtest_id}/equity")
async def get_equity(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await _require(backtest_id, user, db)
    return {"equity_curve": b.equity_curve, "trade_pnls": b.trade_pnls}


@router.get("/{backtest_id}/report", response_class=HTMLResponse)
async def get_report(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    b = await _require(backtest_id, user, db)
    curve = [(int(ts), float(v)) for ts, v in b.equity_curve]
    return HTMLResponse(
        html_report(f"Backtest #{b.id} — {b.type} {b.symbol}", b.metrics, b.monte_carlo, curve)
    )


@router.get("/{backtest_id}/trades.csv", response_class=PlainTextResponse)
async def get_trades_csv(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    b = await _require(backtest_id, user, db)
    return PlainTextResponse(trades_csv(list(b.trade_pnls)), media_type="text/csv")


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_backtest(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    b = await _require(backtest_id, user, db)
    if b.status in ("queued", "running"):
        b.status = "canceled"
        await db.commit()
    return None
