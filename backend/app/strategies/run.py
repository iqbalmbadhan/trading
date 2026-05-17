"""Execute a persisted StrategyRun: load, drive, persist signals, finalize."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.audit.service import record_decision
from app.db.models import Signal as SignalRow
from app.db.models import Strategy, StrategyRun
from app.exchanges.base import BaseExchange
from app.execution.paper_executor import PaperExecutor
from app.strategies.base import StrategyContext
from app.strategies.registry import build_strategy
from app.strategies.runner import NeverStop, StopController, StrategyRunner


async def execute_run(
    *,
    session_factory: async_sessionmaker,
    run_id: int,
    data_exchange: BaseExchange,
    trade_exchange: BaseExchange,
    stop: StopController | None = None,
    max_cycles: int | None = None,
    poll_interval_s: float = 1.0,
) -> None:
    stop = stop or NeverStop()
    async with session_factory() as session:
        run = await session.get(StrategyRun, run_id)
        if run is None:
            raise ValueError(f"StrategyRun {run_id} not found")
        strategy_row = await session.get(Strategy, run.strategy_id)
        if strategy_row is None:
            raise ValueError(f"Strategy {run.strategy_id} not found")
        symbol = strategy_row.symbol
        timeframe = strategy_row.timeframe
        strategy = build_strategy(strategy_row.type, strategy_row.params)

    ctx = StrategyContext(symbol=symbol, timeframe=timeframe)
    executor = PaperExecutor(trade_exchange)
    runner = StrategyRunner(strategy, ctx, executor)

    status = "stopped"
    error: str | None = None
    results = []
    try:
        results = await runner.run_polling(
            data_exchange,
            symbol,
            timeframe,
            stop=stop,
            poll_interval_s=poll_interval_s,
            max_cycles=max_cycles,
        )
    except Exception as exc:
        status = "error"
        error = str(exc)
    finally:
        await data_exchange.close()
        await trade_exchange.close()

    async with session_factory() as session:
        for result in results:
            sig = result.signal
            session.add(
                SignalRow(
                    strategy_run_id=run_id,
                    ts=sig.ts,
                    symbol=sig.symbol,
                    side=str(sig.side),
                    confidence=sig.confidence,
                    stop_price=sig.stop_price,
                    meta=sig.metadata,
                )
            )
            await record_decision(
                session,
                strategy_run_id=run_id,
                ts=sig.ts,
                symbol=sig.symbol,
                decision=str(sig.side),
                reasoning={
                    "executed": result.order is not None,
                    "skipped_reason": result.skipped_reason,
                },
                indicators=sig.metadata,
            )
        run = await session.get(StrategyRun, run_id)
        run.status = status
        run.error = error
        run.stopped_at = datetime.now(UTC)
        strategy_row = await session.get(Strategy, run.strategy_id)
        strategy_row.is_active = False
        await session.commit()
