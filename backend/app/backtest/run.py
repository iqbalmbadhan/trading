"""Load a persisted Backtest, run the engine + Monte Carlo, store results."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.backtest.engine import BacktestConfig, run_backtest_engine
from app.backtest.montecarlo import monte_carlo
from app.db.models import Backtest, Candle, Symbol
from app.strategies.base import Candle as StratCandle
from app.strategies.registry import build_strategy


async def _load_candles(session, symbol: str, timeframe: str, start, end) -> list[StratCandle]:
    sym = (await session.execute(select(Symbol).where(Symbol.symbol == symbol))).scalars().first()
    if sym is None:
        return []
    stmt = select(Candle).where(Candle.symbol_id == sym.id, Candle.timeframe == timeframe)
    if start is not None:
        stmt = stmt.where(Candle.ts >= start)
    if end is not None:
        stmt = stmt.where(Candle.ts <= end)
    rows = (await session.execute(stmt.order_by(Candle.ts))).scalars().all()
    return [StratCandle(ts=r.ts, o=r.o, h=r.h, l=r.l, c=r.c, v=r.v) for r in rows]


async def run_backtest(session_factory: async_sessionmaker, backtest_id: int) -> None:
    async with session_factory() as session:
        bt = await session.get(Backtest, backtest_id)
        if bt is None:
            raise ValueError(f"Backtest {backtest_id} not found")
        bt.status = "running"
        await session.commit()
        candles = await _load_candles(session, bt.symbol, bt.timeframe, bt.start_ts, bt.end_ts)
        params = dict(bt.params)
        strategy_type = bt.type
        symbol = bt.symbol
        timeframe = bt.timeframe
        starting_cash = bt.starting_cash

    status, error = "finished", None
    metrics: dict = {}
    mc: dict = {}
    equity: list = []
    trades: list = []
    try:
        if len(candles) < 2:
            raise ValueError("no candle data for the requested symbol/timeframe/range")
        strategy = build_strategy(strategy_type, params)
        result = await run_backtest_engine(
            strategy,
            candles,
            BacktestConfig(symbol=symbol, timeframe=timeframe, starting_cash=starting_cash),
        )
        metrics = result.metrics
        equity = [[ts, val] for ts, val in result.equity_curve]
        trades = result.trade_pnls
        mc = monte_carlo(trades, starting_cash)
    except Exception as exc:
        status, error = "error", str(exc)

    async with session_factory() as session:
        bt = await session.get(Backtest, backtest_id)
        bt.status = status
        bt.error = error
        bt.metrics = metrics
        bt.monte_carlo = mc
        bt.equity_curve = equity
        bt.trade_pnls = trades
        bt.finished_at = datetime.now(UTC)
        await session.commit()
