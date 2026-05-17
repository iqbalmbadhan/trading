"""Locally-simulated bracket (OCO) for exchanges without native support.

An entry fill is protected by a linked stop and target. When one leg
triggers the other is cancelled automatically (one-cancels-other).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.exchanges.base import OrderSide


@dataclass
class Bracket:
    side: OrderSide  # side of the *position* being protected
    entry_price: float
    stop_price: float
    target_price: float
    done: bool = False
    triggered_leg: str | None = None

    def __post_init__(self) -> None:
        if self.side is OrderSide.BUY:
            if not (self.stop_price < self.entry_price < self.target_price):
                raise ValueError("long bracket requires stop < entry < target")
        else:
            if not (self.target_price < self.entry_price < self.stop_price):
                raise ValueError("short bracket requires target < entry < stop")

    def on_price(self, price: float) -> str | None:
        """Feed the latest price. Returns the leg that triggered, once."""
        if self.done:
            return None
        if self.side is OrderSide.BUY:
            hit_stop = price <= self.stop_price
            hit_target = price >= self.target_price
        else:
            hit_stop = price >= self.stop_price
            hit_target = price <= self.target_price
        # Stop takes priority if both are crossed in the same observation.
        if hit_stop:
            leg = "stop"
        elif hit_target:
            leg = "target"
        else:
            return None
        self.done = True
        self.triggered_leg = leg
        return leg
