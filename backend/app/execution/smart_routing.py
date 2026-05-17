"""Smart order routing: split an order across venues by best price.

The planner is pure (no I/O) so it is fully unit-tested. The router fetches
top-of-book quotes from several adapters, plans the split, and places child
orders, aggregating the fills into one synthetic result.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.exchanges.base import BaseExchange, OrderSide, OrderType


@dataclass(frozen=True)
class Venue:
    name: str
    price: float  # ask for BUY, bid for SELL
    max_qty: float  # available liquidity at this price


@dataclass(frozen=True)
class Allocation:
    venue: str
    qty: float
    price: float


@dataclass(frozen=True)
class RoutePlan:
    allocations: list[Allocation]
    filled_qty: float
    est_avg_price: float
    unfilled_qty: float


def plan_route(side: OrderSide, qty: float, venues: list[Venue]) -> RoutePlan:
    """Greedily fill `qty` from the best-priced venues first.

    BUY consumes the lowest asks first; SELL consumes the highest bids
    first. Each venue contributes at most its `max_qty`. Any quantity that
    cannot be filled is reported as `unfilled_qty`.
    """
    if qty <= 0:
        raise ValueError("qty must be positive")
    ordered = sorted(
        (v for v in venues if v.max_qty > 0 and v.price > 0),
        key=lambda v: v.price,
        reverse=(side is OrderSide.SELL),
    )
    allocations: list[Allocation] = []
    remaining = qty
    notional = 0.0
    for v in ordered:
        if remaining <= 1e-12:
            break
        take = min(remaining, v.max_qty)
        allocations.append(Allocation(venue=v.name, qty=take, price=v.price))
        notional += take * v.price
        remaining -= take
    filled = qty - remaining
    return RoutePlan(
        allocations=allocations,
        filled_qty=filled,
        est_avg_price=(notional / filled) if filled > 0 else 0.0,
        unfilled_qty=max(0.0, remaining),
    )


class SmartOrderRouter:
    def __init__(self, adapters: dict[str, BaseExchange], per_venue_cap: float = 1e9) -> None:
        if not adapters:
            raise ValueError("at least one exchange adapter is required")
        self._adapters = adapters
        self._cap = per_venue_cap

    async def quote(self, symbol: str, side: OrderSide, qty: float) -> RoutePlan:
        venues: list[Venue] = []
        for name, ex in self._adapters.items():
            t = await ex.fetch_ticker(symbol)
            price = t.ask if side is OrderSide.BUY else t.bid
            venues.append(Venue(name=name, price=price, max_qty=self._cap))
        return plan_route(side, qty, venues)

    async def execute(self, symbol: str, side: OrderSide, qty: float) -> dict:
        plan = await self.quote(symbol, side, qty)
        fills: list[dict] = []
        notional = 0.0
        total = 0.0
        for alloc in plan.allocations:
            order = await self._adapters[alloc.venue].place_order(
                symbol=symbol,
                side=side,
                type=OrderType.MARKET,
                qty=alloc.qty,
            )
            fill_price = order.avg_fill_price or alloc.price
            fills.append({"venue": alloc.venue, "qty": order.filled_qty, "price": fill_price})
            notional += order.filled_qty * fill_price
            total += order.filled_qty
        return {
            "symbol": symbol,
            "side": side.value,
            "requested_qty": qty,
            "filled_qty": total,
            "avg_price": (notional / total) if total > 0 else 0.0,
            "fills": fills,
            "unfilled_qty": plan.unfilled_qty,
        }
