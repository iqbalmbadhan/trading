"""Phase 8: backtest fill simulation and PnL booking."""

import pytest

from app.backtest.exchange import BacktestExchange
from app.exchanges.base import OrderSide, OrderType
from app.strategies.base import Candle


def _c(price: float) -> Candle:
    return Candle(ts=0, o=price, h=price, l=price, c=price, v=1.0)


async def test_long_round_trip_books_pnl():
    ex = BacktestExchange(starting_cash=10_000.0, fee_bps=0.0, slippage_bps=0.0)
    ex.set_candle(_c(100.0))
    await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 1.0)
    assert ex.has_position
    assert ex.equity(100.0) == pytest.approx(10_000.0)

    ex.set_candle(_c(110.0))
    await ex.place_order("BTC/USDT", OrderSide.SELL, OrderType.MARKET, 1.0)
    assert not ex.has_position
    assert ex.closed_trades == [pytest.approx(10.0)]
    assert ex.equity(110.0) == pytest.approx(10_010.0)


async def test_fee_and_slippage_reduce_equity():
    ex = BacktestExchange(starting_cash=1_000.0, fee_bps=10.0, slippage_bps=10.0)
    ex.set_candle(_c(100.0))
    await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 1.0)
    # buy fills at 100*(1+0.001)=100.1, fee 0.1001 -> equity below 1000
    assert ex.equity(100.0) < 1_000.0


async def test_short_then_cover():
    ex = BacktestExchange(starting_cash=10_000.0, fee_bps=0.0, slippage_bps=0.0)
    ex.set_candle(_c(100.0))
    await ex.place_order("BTC/USDT", OrderSide.SELL, OrderType.MARKET, 1.0)
    ex.set_candle(_c(90.0))
    await ex.place_order("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 1.0)
    assert ex.closed_trades == [pytest.approx(10.0)]
    assert not ex.has_position
