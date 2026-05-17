"""Phase 3: paper exchange fill simulation tests."""

import pytest

from app.exchanges.base import OrderSide, OrderType, Ticker
from app.exchanges.errors import OrderError
from app.exchanges.paper import PaperExchange


def _source(bid: float, ask: float):
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=bid, ask=ask, last=(bid + ask) / 2)

    return _src


async def test_market_buy_applies_slippage_and_updates_state():
    ex = PaperExchange(_source(99.0, 100.0), starting_cash=1000.0, slippage_bps=10.0)
    order = await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=1.0)

    assert order.status == "closed"
    assert order.avg_fill_price == pytest.approx(100.0 * 1.001)  # 10 bps above ask
    balances = await ex.fetch_balance()
    assert balances["USDT"] == pytest.approx(1000.0 - 100.1)
    assert balances["BTC"] == pytest.approx(1.0)

    pos = await ex.fetch_position("BTC/USDT")
    assert pos is not None and pos.side is OrderSide.BUY and pos.qty == pytest.approx(1.0)


async def test_insufficient_balance_rejected():
    ex = PaperExchange(_source(99.0, 100.0), starting_cash=50.0)
    with pytest.raises(OrderError):
        await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=1.0)


async def test_resting_limit_order_then_cancel():
    ex = PaperExchange(_source(99.0, 100.0), starting_cash=1000.0)
    order = await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.LIMIT, qty=1.0, price=90.0)
    assert order.status == "open"
    assert [o.id for o in await ex.fetch_open_orders()] == [order.id]

    await ex.cancel_order(order.id, "BTC/USDT")
    assert await ex.fetch_open_orders() == []
    with pytest.raises(OrderError):
        await ex.cancel_order(order.id, "BTC/USDT")


async def test_marketable_limit_fills_immediately():
    ex = PaperExchange(_source(99.0, 100.0), starting_cash=1000.0)
    order = await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.LIMIT, qty=1.0, price=101.0)
    assert order.status == "closed"
    assert order.avg_fill_price == 101.0


async def test_buy_then_sell_closes_position():
    ex = PaperExchange(_source(100.0, 100.0), starting_cash=1000.0, slippage_bps=0.0)
    await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=2.0)
    await ex.place_order("BTC/USDT", OrderSide.SELL, OrderType.MARKET, qty=2.0)
    assert await ex.fetch_position("BTC/USDT") is None
    balances = await ex.fetch_balance()
    assert balances["USDT"] == pytest.approx(1000.0)


async def test_reset_restores_starting_state():
    ex = PaperExchange(_source(100.0, 100.0), starting_cash=500.0, slippage_bps=0.0)
    await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=1.0)
    ex.reset()
    assert await ex.fetch_balance() == {"USDT": 500.0}
    assert await ex.fetch_position("BTC/USDT") is None
