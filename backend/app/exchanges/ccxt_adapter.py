"""CCXT-backed adapter wrapping any CCXT-supported exchange."""

from __future__ import annotations

import ccxt.async_support as ccxt

from app.exchanges.base import (
    BaseExchange,
    ExchangePermissions,
    Order,
    OrderSide,
    OrderType,
    Position,
    Ticker,
)
from app.exchanges.errors import OrderError, PermissionVerificationError
from app.exchanges.rate_limiter import TokenBucketRateLimiter


def _map_order(raw: dict) -> Order:
    return Order(
        id=str(raw.get("id")),
        symbol=raw.get("symbol", ""),
        side=OrderSide(raw.get("side", "buy")),
        type=OrderType(raw.get("type", "market")),
        qty=float(raw.get("amount") or 0.0),
        price=raw.get("price"),
        status=raw.get("status", "open"),
        filled_qty=float(raw.get("filled") or 0.0),
        avg_fill_price=raw.get("average"),
    )


class CCXTExchange(BaseExchange):
    """Wraps a CCXT async exchange client with a token-bucket rate limiter."""

    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        secret: str,
        *,
        rate: float = 8.0,
        capacity: int = 16,
    ) -> None:
        if not hasattr(ccxt, exchange_id):
            raise PermissionVerificationError(f"Unsupported exchange '{exchange_id}'")
        self.name = exchange_id
        klass = getattr(ccxt, exchange_id)
        self._client = klass({"apiKey": api_key, "secret": secret, "enableRateLimit": True})
        self._limiter = TokenBucketRateLimiter(rate=rate, capacity=capacity)

    async def verify_permissions(self) -> ExchangePermissions:
        """Detect withdrawal scope. Fails closed for exchanges we can't check.

        Binance exposes an explicit API-restrictions endpoint; unknown
        exchanges raise so the caller rejects the key rather than assuming
        it is safe.
        """
        await self._limiter.acquire()
        if self.name in ("binance", "binanceusdm", "binancecoinm"):
            res = await self._client.sapiGetAccountApiRestrictions()
            return ExchangePermissions(
                can_trade=bool(res.get("enableSpotAndMarginTrading", True)),
                can_withdraw=bool(res.get("enableWithdrawals", False)),
            )
        raise PermissionVerificationError(
            f"Automatic permission verification is not supported for '{self.name}'. "
            "Use a trade-only key on a supported exchange."
        )

    async def fetch_balance(self) -> dict[str, float]:
        await self._limiter.acquire()
        raw = await self._client.fetch_balance()
        total = raw.get("total", {})
        return {k: float(v) for k, v in total.items() if v}

    async def fetch_ticker(self, symbol: str) -> Ticker:
        await self._limiter.acquire()
        t = await self._client.fetch_ticker(symbol)
        return Ticker(
            symbol=symbol,
            bid=float(t.get("bid") or t["last"]),
            ask=float(t.get("ask") or t["last"]),
            last=float(t["last"]),
        )

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[list[float]]:
        await self._limiter.acquire()
        return await self._client.fetch_ohlcv(symbol, timeframe, limit=limit)

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        qty: float,
        price: float | None = None,
        client_order_id: str | None = None,
    ) -> Order:
        if type is OrderType.LIMIT and price is None:
            raise OrderError("limit order requires a price")
        await self._limiter.acquire()
        params = {"clientOrderId": client_order_id} if client_order_id else {}
        raw = await self._client.create_order(symbol, str(type), str(side), qty, price, params)
        return _map_order(raw)

    async def cancel_order(self, order_id: str, symbol: str) -> None:
        await self._limiter.acquire()
        await self._client.cancel_order(order_id, symbol)

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        await self._limiter.acquire()
        raw = await self._client.fetch_open_orders(symbol)
        return [_map_order(o) for o in raw]

    async def fetch_position(self, symbol: str) -> Position | None:
        if not self._client.has.get("fetchPositions"):
            return None
        await self._limiter.acquire()
        for p in await self._client.fetch_positions([symbol]):
            contracts = float(p.get("contracts") or 0.0)
            if contracts:
                return Position(
                    symbol=symbol,
                    side=OrderSide(p.get("side", "buy")),
                    qty=contracts,
                    avg_entry=float(p.get("entryPrice") or 0.0),
                )
        return None

    async def close(self) -> None:
        await self._client.close()
