"""Celery tasks that run strategies out-of-process."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import ExchangeAccount
from app.exchanges.ccxt_adapter import CCXTExchange
from app.exchanges.paper import PaperExchange
from app.exchanges.service import build_adapter_for
from app.execution.liquidation import liquidate
from app.strategies.run import execute_run
from app.strategies.stop import RedisStopController
from app.workers.celery_app import celery_app


@celery_app.task(name="strategies.run")
def run_strategy_run(run_id: int, data_exchange_id: str = "binance") -> None:
    """Run a paper strategy: live data from a public exchange, paper fills."""

    async def _run() -> None:
        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        data_exchange = CCXTExchange(data_exchange_id, "", "")
        trade_exchange = PaperExchange(price_source=data_exchange.fetch_ticker)
        try:
            await execute_run(
                session_factory=session_factory,
                run_id=run_id,
                data_exchange=data_exchange,
                trade_exchange=trade_exchange,
                stop=RedisStopController(run_id),
            )
        finally:
            await engine.dispose()

    asyncio.run(_run())


@celery_app.task(name="execution.liquidate_account")
def liquidate_account_task(exchange_account_id: int, symbols: list[str]) -> None:
    """Cancel open orders and flatten positions for one live account."""

    async def _run() -> None:
        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as session:
                account = await session.get(ExchangeAccount, exchange_account_id)
                if account is None:
                    return
                adapter = build_adapter_for(account)
            try:
                await liquidate(adapter, symbols)
            finally:
                await adapter.close()
        finally:
            await engine.dispose()

    asyncio.run(_run())
