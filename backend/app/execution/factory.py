"""Builds the exchange adapter used for order execution.

Isolated so tests can substitute a deterministic adapter instead of a
network-backed one.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.exchanges.base import BaseExchange
from app.exchanges.ccxt_adapter import CCXTExchange
from app.exchanges.paper import PaperExchange
from app.exchanges.service import build_adapter_for, get_account


async def build_execution_exchange(
    db: AsyncSession,
    user_id: int,
    *,
    is_paper: bool,
    exchange_account_id: int | None,
    data_exchange_id: str = "binance",
) -> BaseExchange:
    if is_paper:
        data = CCXTExchange(data_exchange_id, "", "")
        return PaperExchange(price_source=data.fetch_ticker)
    if exchange_account_id is None:
        raise ValueError("exchange_account_id required for live orders")
    account = await get_account(db, user_id, exchange_account_id)
    if account is None:
        raise ValueError("exchange account not found")
    return build_adapter_for(account)
