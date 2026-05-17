"""Order and position endpoints, including manual order placement."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.risk import get_kill_switch
from app.db.models import Order, Position, User
from app.db.session import get_db
from app.exchanges.base import OrderSide, OrderType
from app.execution.errors import KillSwitchEngaged, RiskRejected
from app.execution.factory import build_execution_exchange
from app.execution.router import LiveOrderRouter, OrderRequest
from app.risk import service as risk_service
from app.risk.config import AccountState
from app.risk.kill_switch import KillSwitch
from app.risk.manager import RiskManager

router = APIRouter(prefix="/api/v1", tags=["orders"])


class ManualOrder(BaseModel):
    symbol: str
    side: OrderSide
    type: OrderType = OrderType.MARKET
    qty: float = Field(gt=0)
    price: float | None = None
    stop_price: float | None = None
    live: bool = False
    exchange_account_id: int | None = None


class OrderOut(BaseModel):
    id: int
    client_order_id: str
    symbol: str
    side: str
    type: str
    qty: float
    price: float | None
    status: str
    filled_qty: float
    avg_fill: float | None
    fees: float
    slippage_bps: float | None
    is_paper: bool


class PositionOut(BaseModel):
    id: int
    symbol: str
    side: str
    qty: float
    avg_entry: float
    unrealized_pnl: float
    is_paper: bool


def _order_out(o: Order) -> OrderOut:
    return OrderOut(
        id=o.id,
        client_order_id=o.client_order_id,
        symbol=o.symbol,
        side=o.side,
        type=o.type,
        qty=o.qty,
        price=o.price,
        status=o.status,
        filled_qty=o.filled_qty,
        avg_fill=o.avg_fill,
        fees=o.fees,
        slippage_bps=o.slippage_bps,
        is_paper=o.is_paper,
    )


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(
    is_paper: bool | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderOut]:
    stmt = select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())
    if is_paper is not None:
        stmt = stmt.where(Order.is_paper == is_paper)
    rows = (await db.execute(stmt)).scalars().all()
    return [_order_out(o) for o in rows]


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    o = await db.get(Order, order_id)
    if o is None or o.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return _order_out(o)


@router.post("/orders/manual-place", response_model=OrderOut, status_code=201)
async def manual_place(
    payload: ManualOrder,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ks: KillSwitch = Depends(get_kill_switch),
) -> OrderOut:
    if payload.live and not user.live_trading_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live trading is not enabled. Enable it from the account page first.",
        )
    is_paper = not payload.live
    try:
        exchange = await build_execution_exchange(
            db,
            user.id,
            is_paper=is_paper,
            exchange_account_id=payload.exchange_account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    config = await risk_service.get_config(db, user.id)
    quote = payload.symbol.partition("/")[2] or "USDT"
    try:
        balances = await exchange.fetch_balance()
    except Exception:
        balances = {}
    state = AccountState(equity=float(balances.get(quote, 0.0)))

    router_ = LiveOrderRouter(
        db,
        exchange,
        user.id,
        kill_switch=ks,
        risk_manager=RiskManager(config),
        account_state=state,
    )
    try:
        order = await router_.place(
            OrderRequest(
                symbol=payload.symbol,
                side=payload.side,
                type=payload.type,
                qty=payload.qty,
                price=payload.price,
                stop_price=payload.stop_price,
                exchange_account_id=payload.exchange_account_id,
                is_paper=is_paper,
            )
        )
    except KillSwitchEngaged as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RiskRejected as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Risk rejected: {exc}",
        ) from exc
    finally:
        await exchange.close()
    return _order_out(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    o = await db.get(Order, order_id)
    if o is None or o.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if o.status in ("closed", "canceled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Order is already {o.status}"
        )
    o.status = "canceled"
    await db.commit()
    await db.refresh(o)
    return _order_out(o)


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PositionOut]:
    rows = (await db.execute(select(Position).where(Position.user_id == user.id))).scalars().all()
    return [
        PositionOut(
            id=p.id,
            symbol=p.symbol,
            side=p.side,
            qty=p.qty,
            avg_entry=p.avg_entry,
            unrealized_pnl=p.unrealized_pnl,
            is_paper=p.is_paper,
        )
        for p in rows
    ]


@router.post("/positions/{position_id}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_position(
    position_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    p = await db.get(Position, position_id)
    if p is None or p.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    await db.delete(p)
    await db.commit()
    return None
