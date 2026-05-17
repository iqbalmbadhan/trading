"""Event-driven backtest: replay candles through an unchanged strategy."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.backtest.exchange import BacktestExchange
from app.backtest.metrics import compute_metrics
from app.execution.paper_executor import PaperExecutor
from app.market_data.timeframes import timeframe_seconds
from app.strategies.base import BaseStrategy, Candle, StrategyContext

_SECONDS_PER_YEAR = 365 * 24 * 60 * 60


@dataclass
class BacktestConfig:
    symbol: str
    timeframe: str
    starting_cash: float = 10_000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0


@dataclass
class BacktestResult:
    equity_curve: list[tuple[int, float]]
    trade_pnls: list[float]
    metrics: dict[str, float]
    final_equity: float = field(default=0.0)


async def run_backtest_engine(
    strategy: BaseStrategy, candles: list[Candle], config: BacktestConfig
) -> BacktestResult:
    ex = BacktestExchange(
        starting_cash=config.starting_cash,
        fee_bps=config.fee_bps,
        slippage_bps=config.slippage_bps,
    )
    executor = PaperExecutor(ex)
    ctx = StrategyContext(symbol=config.symbol, timeframe=config.timeframe)

    await strategy.on_start(ctx)
    equity_curve: list[tuple[int, float]] = []
    exposure_flags: list[bool] = []
    for candle in candles:
        ex.set_candle(candle)
        for signal in await strategy.on_candle(ctx, candle):
            await executor.execute(signal)
        equity_curve.append((candle.ts, ex.equity(candle.c)))
        exposure_flags.append(ex.has_position)
    await strategy.on_stop(ctx)

    ppy = _SECONDS_PER_YEAR / timeframe_seconds(config.timeframe)
    metrics = compute_metrics(
        equity_curve,
        ex.closed_trades,
        periods_per_year=ppy,
        exposure_flags=exposure_flags,
        traded_notional=ex.traded_notional,
    )
    return BacktestResult(
        equity_curve=equity_curve,
        trade_pnls=ex.closed_trades,
        metrics=metrics,
        final_equity=equity_curve[-1][1] if equity_curve else config.starting_cash,
    )
