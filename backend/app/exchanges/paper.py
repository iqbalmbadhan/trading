"""Paper exchange: simulates fills against a live price source.

Slippage and latency are configurable. The same connector interface is used
for paper and live so strategy/execution code paths are identical.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable

from app.exchanges.base import (
    BaseExchange,
    ExchangePermissions,
    Order,
    OrderSide,
    OrderType,
    Position,
    Ticker,
)
from app.exchanges.errors import OrderError

PriceSource = Callable[[str], Awaitable[Ticker]]


class PaperExchange(BaseExchange):
    name = "paper"

    def __init__(
        self,
        price_source: PriceSource,
        starting_cash: float = 10_000.0,
        quote_currency: str = "USDT",
        slippage_bps: float = 5.0,
        latency_s: float = 0.0,
    ) -> None:
        self._price_source = price_source
        self._quote = quote_currency
        self._slippage = slippage_bps / 10_000.0
        self._latency = latency_s
        self._starting_cash = starting_cash
        self._balances: dict[str, float] = {quote_currency: starting_cash}
        self._positions: dict[str, Position] = {}
        self._open_orders: dict[str, Order] = {}

    def reset(self) -> None:
        self._balances = {self._quote: self._starting_cash}
        self._positions.clear()
        self._open_orders.clear()

    async def verify_permissions(self) -> ExchangePermissions:
        # A simulated account can never withdraw real funds.
        return ExchangePermissions(can_trade=True, can_withdraw=False)

    async def fetch_balance(self) -> dict[str, float]:
        return dict(self._balances)

    async def fetch_ticker(self, symbol: str) -> Ticker:
        return await self._price_source(symbol)

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[list[float]]:
        raise OrderError("Paper exchange does not provide historical candles; use market_data")

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        return (
            price * (1 + self._slippage) if side is OrderSide.BUY else price * (1 - self._slippage)
        )

    def _settle_fill(self, symbol: str, side: OrderSide, qty: float, price: float) -> None:
        base = symbol.split("/")[0]
        cost = qty * price
        if side is OrderSide.BUY:
            if self._balances.get(self._quote, 0.0) < cost:
                raise OrderError("Insufficient paper balance")
            self._balances[self._quote] -= cost
            self._balances[base] = self._balances.get(base, 0.0) + qty
        else:
            if self._balances.get(base, 0.0) < qty:
                raise OrderError("Insufficient paper position to sell")
            self._balances[base] -= qty
            self._balances[self._quote] = self._balances.get(self._quote, 0.0) + cost
        self._update_position(symbol, side, qty, price)

    def _update_position(self, symbol: str, side: OrderSide, qty: float, price: float) -> None:
        pos = self._positions.get(symbol)
        signed = qty if side is OrderSide.BUY else -qty
        if pos is None:
            net = signed
        else:
            prev = pos.qty if pos.side is OrderSide.BUY else -pos.qty
            net = prev + signed
        if abs(net) < 1e-12:
            self._positions.pop(symbol, None)
            return
        new_side = OrderSide.BUY if net > 0 else OrderSide.SELL
        if pos is not None and pos.side is new_side:
            total = pos.qty + qty
            avg = (pos.avg_entry * pos.qty + price * qty) / total
        else:
            avg = price
        self._positions[symbol] = Position(
            symbol=symbol, side=new_side, qty=abs(net), avg_entry=avg
        )

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        qty: float,
        price: float | None = None,
        client_order_id: str | None = None,
    ) -> Order:
        if qty <= 0:
            raise OrderError("qty must be positive")
        if self._latency:
            await asyncio.sleep(self._latency)
        ticker = await self._price_source(symbol)
        order_id = client_order_id or uuid.uuid4().hex

        if type is OrderType.MARKET:
            ref = ticker.ask if side is OrderSide.BUY else ticker.bid
            fill_price = self._apply_slippage(ref, side)
            self._settle_fill(symbol, side, qty, fill_price)
            return Order(
                id=order_id,
                symbol=symbol,
                side=side,
                type=type,
                qty=qty,
                price=fill_price,
                status="closed",
                filled_qty=qty,
                avg_fill_price=fill_price,
            )

        if price is None:
            raise OrderError("limit order requires a price")
        marketable = (side is OrderSide.BUY and price >= ticker.ask) or (
            side is OrderSide.SELL and price <= ticker.bid
        )
        if marketable:
            self._settle_fill(symbol, side, qty, price)
            return Order(
                id=order_id,
                symbol=symbol,
                side=side,
                type=type,
                qty=qty,
                price=price,
                status="closed",
                filled_qty=qty,
                avg_fill_price=price,
            )
        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            type=type,
            qty=qty,
            price=price,
            status="open",
            filled_qty=0.0,
            avg_fill_price=None,
        )
        self._open_orders[order_id] = order
        return order

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        if self._open_orders.pop(order_id, None) is None:
            raise OrderError(f"Unknown open order {order_id}")

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        orders = list(self._open_orders.values())
        if symbol is not None:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def fetch_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)
