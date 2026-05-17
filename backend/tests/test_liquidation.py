"""Phase 7: kill-switch liquidation flattens orders and positions."""

from app.exchanges.base import OrderSide, OrderType, Ticker
from app.exchanges.paper import PaperExchange
from app.execution.liquidation import liquidate


def _src(bid: float, ask: float):
    async def _s(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=bid, ask=ask, last=(bid + ask) / 2)

    return _s


async def test_liquidate_cancels_orders_and_closes_position():
    ex = PaperExchange(_src(99.0, 100.0), starting_cash=10_000.0, slippage_bps=0.0)
    # Open a long position and leave a resting limit order.
    await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=2.0)
    resting = await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.LIMIT, qty=1.0, price=50.0)
    assert (await ex.fetch_position("BTC/USDT")).qty == 2.0

    result = await liquidate(ex, ["BTC/USDT"])

    assert resting.id in result.cancelled_orders
    assert "BTC/USDT" in result.closed_positions
    assert await ex.fetch_open_orders() == []
    assert await ex.fetch_position("BTC/USDT") is None


async def test_liquidate_is_noop_when_flat():
    ex = PaperExchange(_src(99.0, 100.0), starting_cash=1000.0)
    result = await liquidate(ex, ["BTC/USDT"])
    assert result.cancelled_orders == []
    assert result.closed_positions == []
