"""Phase 12: smart order routing planner and multi-venue execution."""

import pytest

from app.exchanges.base import OrderSide, Ticker
from app.exchanges.paper import PaperExchange
from app.execution.smart_routing import SmartOrderRouter, Venue, plan_route


def test_buy_fills_cheapest_first_and_splits():
    venues = [
        Venue("A", price=101.0, max_qty=5),
        Venue("B", price=100.0, max_qty=3),
        Venue("C", price=102.0, max_qty=10),
    ]
    plan = plan_route(OrderSide.BUY, 6, venues)
    # 3 @100 (B) then 3 @101 (A)
    assert [(a.venue, a.qty) for a in plan.allocations] == [("B", 3), ("A", 3)]
    assert plan.filled_qty == 6
    assert plan.est_avg_price == pytest.approx((3 * 100 + 3 * 101) / 6)
    assert plan.unfilled_qty == 0


def test_sell_fills_highest_bid_first():
    venues = [Venue("A", 99.0, 10), Venue("B", 101.0, 2), Venue("C", 100.0, 10)]
    plan = plan_route(OrderSide.SELL, 3, venues)
    assert plan.allocations[0].venue == "B"  # best bid first
    assert plan.allocations[1].venue == "C"


def test_partial_fill_reports_unfilled():
    plan = plan_route(OrderSide.BUY, 10, [Venue("A", 100.0, 4)])
    assert plan.filled_qty == 4
    assert plan.unfilled_qty == 6


def test_invalid_qty():
    with pytest.raises(ValueError):
        plan_route(OrderSide.BUY, 0, [Venue("A", 100.0, 1)])


def _paper(price: float) -> PaperExchange:
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=price, ask=price, last=price)

    return PaperExchange(_src, starting_cash=1_000_000.0, slippage_bps=0.0)


async def test_router_quote_prefers_cheaper_venue():
    smart = SmartOrderRouter({"cheap": _paper(100.0), "dear": _paper(105.0)}, per_venue_cap=2.0)
    plan = await smart.quote("BTC/USDT", OrderSide.BUY, 3.0)
    assert plan.allocations[0].venue == "cheap"
    assert plan.filled_qty == 3.0


async def test_router_execute_aggregates_fills():
    smart = SmartOrderRouter({"cheap": _paper(100.0), "dear": _paper(110.0)}, per_venue_cap=1.0)
    result = await smart.execute("BTC/USDT", OrderSide.BUY, 2.0)
    assert result["filled_qty"] == 2.0
    assert {f["venue"] for f in result["fills"]} == {"cheap", "dear"}
    assert result["avg_price"] == pytest.approx(105.0)


async def test_router_requires_adapter():
    with pytest.raises(ValueError):
        SmartOrderRouter({})
