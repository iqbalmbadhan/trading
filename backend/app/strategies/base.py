"""Strategy abstraction: lifecycle, signals, and parameter schemas.

Strategies are pure decision engines. They never touch an exchange directly;
they emit ``Signal`` objects which the execution layer turns into orders.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class SignalSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


@dataclass(frozen=True)
class Candle:
    ts: int
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass(frozen=True)
class Signal:
    ts: int
    symbol: str
    side: SignalSide
    confidence: float = 1.0
    qty: float | None = None
    stop_price: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyContext:
    """Per-run mutable state passed to lifecycle hooks."""

    symbol: str
    timeframe: str
    state: dict[str, Any] = field(default_factory=dict)


class StrategyParams(BaseModel):
    """Base parameter model. Subclasses declare strategy-specific fields."""


class BaseStrategy(ABC):
    """Lifecycle: on_start -> on_candle*/on_tick*/on_order_update* -> on_stop."""

    #: Pydantic model describing this strategy's parameters.
    Params: type[StrategyParams] = StrategyParams
    #: Timeframes the strategy consumes (e.g. ["1h"]).
    required_timeframes: tuple[str, ...] = ()
    #: Indicator names this strategy relies on, for introspection/UI.
    required_indicators: tuple[str, ...] = ()
    #: Parameter ranges for optimization: name -> (low, high, step).
    param_ranges: dict[str, tuple[float, float, float]] = {}

    def __init__(self, params: StrategyParams) -> None:
        self.params = params

    @classmethod
    def default_params(cls) -> StrategyParams:
        return cls.Params()

    async def on_start(self, ctx: StrategyContext) -> None:
        return None

    @abstractmethod
    async def on_candle(self, ctx: StrategyContext, candle: Candle) -> list[Signal]:
        """Return zero or more signals for a closed candle."""

    async def on_tick(self, ctx: StrategyContext, price: float) -> list[Signal]:
        return []

    async def on_order_update(self, ctx: StrategyContext, order: Any) -> None:
        return None

    async def on_stop(self, ctx: StrategyContext) -> None:
        return None
