"""Kill-switch liquidation: cancel open orders and flatten positions."""

from __future__ import annotations

from dataclasses import dataclass

from app.exchanges.base import BaseExchange, OrderSide, OrderType


@dataclass(frozen=True)
class LiquidationResult:
    cancelled_orders: list[str]
    closed_positions: list[str]


async def liquidate(exchange: BaseExchange, symbols: list[str]) -> LiquidationResult:
    """Cancel every open order, then market-close any position in `symbols`.

    Best-effort and idempotent: calling it again once flat is a no-op.
    """
    cancelled: list[str] = []
    for order in await exchange.fetch_open_orders():
        await exchange.cancel_order(order.id, order.symbol)
        cancelled.append(order.id)

    closed: list[str] = []
    for symbol in symbols:
        position = await exchange.fetch_position(symbol)
        if position is None or position.qty <= 0:
            continue
        close_side = OrderSide.SELL if position.side is OrderSide.BUY else OrderSide.BUY
        await exchange.place_order(
            symbol=symbol,
            side=close_side,
            type=OrderType.MARKET,
            qty=position.qty,
        )
        closed.append(symbol)

    return LiquidationResult(cancelled_orders=cancelled, closed_positions=closed)
