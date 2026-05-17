"""Deterministic fill-simulating exchange for backtests.

Implements the same ``BaseExchange`` surface the live/paper paths use so a
strategy runs unchanged in backtest, paper, and live (no copy-paste). Fills
happen at the current candle with configurable fee and slippage; realized
PnL is booked when a position is reduced or flipped.
"""

from __future__ import annotations

import uuid

from app.exchanges.base import (
    BaseExchange,
    ExchangePermissions,
    Order,
    OrderSide,
    OrderType,
    Position,
    Ticker,
)
from app.strategies.base import Candle


class BacktestExchange(BaseExchange):
    name = "backtest"

    def __init__(
        self,
        starting_cash: float = 10_000.0,
        fee_bps: float = 10.0,
        slippage_bps: float = 5.0,
    ) -> None:
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self._fee = fee_bps / 10_000.0
        self._slip = slippage_bps / 10_000.0
        self._candle: Candle | None = None
        # Net position: positive qty = long, negative = short.
        self._pos_qty = 0.0
        self._avg_entry = 0.0
        self.closed_trades: list[float] = []
        self.traded_notional = 0.0

    def set_candle(self, candle: Candle) -> None:
        self._candle = candle

    @property
    def has_position(self) -> bool:
        return abs(self._pos_qty) > 1e-12

    def equity(self, price: float) -> float:
        if not self.has_position:
            return self.cash
        return self.cash + self._pos_qty * price

    def _fill_price(self, side: OrderSide) -> float:
        assert self._candle is not None, "no candle set"
        base = self._candle.c
        return base * (1 + self._slip) if side is OrderSide.BUY else base * (1 - self._slip)

    def _book(self, side: OrderSide, qty: float, price: float) -> None:
        signed = qty if side is OrderSide.BUY else -qty
        self.traded_notional += qty * price
        self.cash -= self._fee * qty * price

        prev = self._pos_qty
        if prev == 0 or (prev > 0) == (signed > 0):
            # Opening or increasing in the same direction.
            new_qty = prev + signed
            self._avg_entry = (
                (abs(prev) * self._avg_entry + qty * price) / abs(new_qty) if new_qty != 0 else 0.0
            )
            self._pos_qty = new_qty
            self.cash -= signed * price
            return

        # Reducing or flipping: realize PnL on the closed portion.
        closing = min(qty, abs(prev))
        direction = 1.0 if prev > 0 else -1.0
        pnl = (price - self._avg_entry) * closing * direction
        self.closed_trades.append(pnl)
        self.cash += direction * closing * self._avg_entry + pnl

        remaining = signed + prev
        if abs(remaining) < 1e-12:
            self._pos_qty = 0.0
            self._avg_entry = 0.0
        elif (remaining > 0) == (prev > 0):
            self._pos_qty = remaining
        else:
            # Flipped: open the residual at this price.
            self._pos_qty = remaining
            self._avg_entry = price
            self.cash -= remaining * price

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        qty: float,
        price: float | None = None,
        client_order_id: str | None = None,
    ) -> Order:
        fill = self._fill_price(side)
        self._book(side, qty, fill)
        return Order(
            id=client_order_id or uuid.uuid4().hex,
            symbol=symbol,
            side=side,
            type=type,
            qty=qty,
            price=fill,
            status="closed",
            filled_qty=qty,
            avg_fill_price=fill,
        )

    async def fetch_ticker(self, symbol: str) -> Ticker:
        assert self._candle is not None
        c = self._candle.c
        return Ticker(symbol=symbol, bid=c, ask=c, last=c)

    async def verify_permissions(self) -> ExchangePermissions:
        return ExchangePermissions(can_trade=True, can_withdraw=False)

    async def fetch_balance(self) -> dict[str, float]:
        return {"USDT": self.cash}

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[list[float]]:
        raise NotImplementedError("backtest exchange is candle-driven")

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        return None

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        return []

    async def fetch_position(self, symbol: str) -> Position | None:
        if not self.has_position:
            return None
        return Position(
            symbol=symbol,
            side=OrderSide.BUY if self._pos_qty > 0 else OrderSide.SELL,
            qty=abs(self._pos_qty),
            avg_entry=self._avg_entry,
        )
