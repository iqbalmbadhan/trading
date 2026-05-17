"""Smart order routing endpoints (split across venues by best price)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.exchanges.base import BaseExchange, OrderSide
from app.exchanges.ccxt_adapter import CCXTExchange
from app.exchanges.paper import PaperExchange
from app.exchanges.service import build_adapter_for, list_accounts
from app.execution.smart_routing import SmartOrderRouter

router = APIRouter(prefix="/api/v1/routing", tags=["routing"])


async def build_routing_adapters(db: AsyncSession, user_id: int) -> dict[str, BaseExchange]:
    """One adapter per active connected exchange; paper fallback if none."""
    accounts = [a for a in await list_accounts(db, user_id) if a.is_active]
    if accounts:
        return {a.exchange: build_adapter_for(a) for a in accounts}
    data = CCXTExchange("binance", "", "")
    return {"paper": PaperExchange(price_source=data.fetch_ticker)}


class RouteRequest(BaseModel):
    symbol: str
    side: OrderSide
    qty: float = Field(gt=0)
    per_venue_cap: float = Field(default=1e9, gt=0)


@router.post("/quote")
async def smart_quote(
    payload: RouteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    adapters = await build_routing_adapters(db, user.id)
    try:
        smart = SmartOrderRouter(adapters, per_venue_cap=payload.per_venue_cap)
        plan = await smart.quote(payload.symbol, payload.side, payload.qty)
    finally:
        for ex in adapters.values():
            await ex.close()
    return {
        "filled_qty": plan.filled_qty,
        "unfilled_qty": plan.unfilled_qty,
        "est_avg_price": plan.est_avg_price,
        "allocations": [
            {"venue": a.venue, "qty": a.qty, "price": a.price} for a in plan.allocations
        ],
    }


@router.post("/execute")
async def smart_execute(
    payload: RouteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    adapters = await build_routing_adapters(db, user.id)
    # This optional path executes on paper venues only.
    if any(not isinstance(ex, PaperExchange) for ex in adapters.values()):
        for ex in adapters.values():
            await ex.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Smart execute is paper-only in this build",
        )
    try:
        smart = SmartOrderRouter(adapters, per_venue_cap=payload.per_venue_cap)
        return await smart.execute(payload.symbol, payload.side, payload.qty)
    finally:
        for ex in adapters.values():
            await ex.close()
