"""Portfolio endpoints: summary, allocation, correlation."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.portfolio.service import PriceProvider, portfolio_correlation, portfolio_summary

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


def get_price_provider() -> PriceProvider:
    """Default price source: public CCXT ticker (last price)."""

    async def _price(symbol: str) -> float:
        from app.exchanges.ccxt_adapter import CCXTExchange

        ex = CCXTExchange("binance", "", "")
        try:
            return (await ex.fetch_ticker(symbol)).last
        finally:
            await ex.close()

    return _price


@router.get("/summary")
async def summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    price_provider: PriceProvider = Depends(get_price_provider),
) -> dict:
    return await portfolio_summary(db, user.id, price_provider)


@router.get("/allocation")
async def allocation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    price_provider: PriceProvider = Depends(get_price_provider),
) -> dict:
    data = await portfolio_summary(db, user.id, price_provider)
    return {
        "allocation": data["allocation"],
        "exposure_by_base": data["exposure_by_base"],
    }


@router.get("/correlation")
async def correlation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"matrix": await portfolio_correlation(db, user.id)}
