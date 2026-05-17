"""Phase 5: strategy runner (replay + polling) and stop control."""

from app.exchanges.base import Ticker
from app.exchanges.paper import PaperExchange
from app.execution.paper_executor import PaperExecutor
from app.strategies.base import BaseStrategy, Candle, Signal, SignalSide, StrategyContext
from app.strategies.runner import StrategyRunner


class EveryCandleBuyer(BaseStrategy):
    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        return [Signal(ts=candle.ts, symbol=ctx.symbol, side=SignalSide.BUY, qty=1.0)]


class CountingStop:
    def __init__(self, stop_after: int) -> None:
        self.calls = 0
        self._stop_after = stop_after

    def is_stopped(self) -> bool:
        self.calls += 1
        return self.calls > self._stop_after


def _price(p: float):
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=p, ask=p, last=p)

    return _src


async def test_run_candles_executes_each_signal():
    ex = PaperExchange(_price(10.0), starting_cash=1000.0, slippage_bps=0.0)
    runner = StrategyRunner(
        EveryCandleBuyer(EveryCandleBuyer.default_params()),
        StrategyContext(symbol="BTC/USDT", timeframe="1h"),
        PaperExecutor(ex),
    )
    candles = [Candle(ts=i, o=10, h=10, l=10, c=10, v=1) for i in range(3)]
    results = await runner.run_candles(candles)
    assert len(results) == 3
    assert (await ex.fetch_balance())["BTC"] == 3.0


class FakeDataExchange:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    async def fetch_ohlcv(self, symbol, timeframe, limit=200):
        self.calls += 1
        return list(self.rows)

    async def close(self):
        return None


async def test_run_polling_dedups_and_respects_stop():
    rows = [[i * 60_000, 10, 10, 10, 10, 1] for i in range(4)]
    data = FakeDataExchange(rows)
    ex = PaperExchange(_price(10.0), starting_cash=1000.0, slippage_bps=0.0)
    runner = StrategyRunner(
        EveryCandleBuyer(EveryCandleBuyer.default_params()),
        StrategyContext(symbol="BTC/USDT", timeframe="1m"),
        PaperExecutor(ex),
    )
    results = await runner.run_polling(
        data, "BTC/USDT", "1m", stop=CountingStop(stop_after=2), poll_interval_s=0.0
    )
    # 4 candles only processed once despite repeated polls.
    assert len(results) == 4
    assert data.calls >= 1


async def test_run_polling_max_cycles_bounds_loop():
    data = FakeDataExchange([[0, 10, 10, 10, 10, 1]])
    ex = PaperExchange(_price(10.0), starting_cash=1000.0, slippage_bps=0.0)
    runner = StrategyRunner(
        EveryCandleBuyer(EveryCandleBuyer.default_params()),
        StrategyContext(symbol="BTC/USDT", timeframe="1m"),
        PaperExecutor(ex),
    )
    results = await runner.run_polling(data, "BTC/USDT", "1m", poll_interval_s=0.0, max_cycles=3)
    assert len(results) == 1
    assert data.calls == 3
