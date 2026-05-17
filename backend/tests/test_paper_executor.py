"""Phase 5: signal -> paper order executor."""

from app.exchanges.base import Ticker
from app.exchanges.paper import PaperExchange
from app.execution.paper_executor import PaperExecutor
from app.strategies.base import Signal, SignalSide


def _source(price: float):
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=price, ask=price, last=price)

    return _src


async def test_buy_signal_places_market_order():
    ex = PaperExchange(_source(100.0), starting_cash=1000.0, slippage_bps=0.0)
    ex_executor = PaperExecutor(ex)
    result = await ex_executor.execute(
        Signal(ts=1, symbol="BTC/USDT", side=SignalSide.BUY, qty=2.0)
    )
    assert result.order is not None and result.order.status == "closed"
    assert (await ex.fetch_balance())["BTC"] == 2.0


async def test_flat_signal_skipped():
    ex = PaperExchange(_source(100.0), starting_cash=1000.0)
    result = await PaperExecutor(ex).execute(Signal(ts=1, symbol="BTC/USDT", side=SignalSide.FLAT))
    assert result.order is None and result.skipped_reason == "flat signal"


async def test_default_qty_used_when_signal_has_none():
    ex = PaperExchange(_source(50.0), starting_cash=1000.0, slippage_bps=0.0)
    result = await PaperExecutor(ex, default_qty=3.0).execute(
        Signal(ts=1, symbol="ETH/USDT", side=SignalSide.BUY)
    )
    assert result.order is not None
    assert (await ex.fetch_balance())["ETH"] == 3.0
