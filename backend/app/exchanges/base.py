"""Abstract exchange interface shared by all adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass(frozen=True)
class ExchangePermissions:
    can_trade: bool
    can_withdraw: bool

    @property
    def is_trade_only(self) -> bool:
        return self.can_trade and not self.can_withdraw


@dataclass(frozen=True)
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float


@dataclass(frozen=True)
class Order:
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None
    status: str
    filled_qty: float
    avg_fill_price: float | None


@dataclass(frozen=True)
class Position:
    symbol: str
    side: OrderSide
    qty: float
    avg_entry: float


class BaseExchange(ABC):
    """Unified exchange abstraction. Adapters never expose raw credentials."""

    name: str

    @abstractmethod
    async def verify_permissions(self) -> ExchangePermissions:
        """Return the API key's permissions. Must reflect withdrawal scope."""

    @abstractmethod
    async def fetch_balance(self) -> dict[str, float]: ...

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker: ...

    @abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 100
    ) -> list[list[float]]: ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        qty: float,
        price: float | None = None,
        client_order_id: str | None = None,
    ) -> Order: ...

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> None: ...

    @abstractmethod
    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]: ...

    @abstractmethod
    async def fetch_position(self, symbol: str) -> Position | None: ...

    async def close(self) -> None:
        """Release any underlying network resources. Override if needed."""
        return None
