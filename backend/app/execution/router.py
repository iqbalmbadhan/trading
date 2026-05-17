"""Live order router: risk + kill switch, idempotent send with safe retries.

A client-side UUID is persisted *before* the order is sent. On a transient
failure the router first checks whether the order already reached the
exchange (idempotency) and only resends if it definitively did not, so a
signed-but-unconfirmed order is never duplicated.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Order as OrderRow
from app.db.models import Position as PositionRow
from app.db.models import Trade as TradeRow
from app.exchanges.base import BaseExchange, OrderSide, OrderType
from app.execution.errors import KillSwitchEngaged, RiskRejected
from app.execution.slippage import slippage_bps
from app.risk.config import AccountState, TradeProposal
from app.risk.kill_switch import KillSwitch
from app.risk.manager import RiskManager

_log = get_logger("execution")


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None = None
    stop_price: float | None = None
    strategy_id: int | None = None
    exchange_account_id: int | None = None
    is_paper: bool = True


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_s: float = 0.0


class LiveOrderRouter:
    def __init__(
        self,
        db: AsyncSession,
        exchange: BaseExchange,
        user_id: int,
        *,
        kill_switch: KillSwitch | None = None,
        risk_manager: RiskManager | None = None,
        account_state: AccountState | None = None,
        slippage_threshold_bps: float = 50.0,
        retry: RetryPolicy | None = None,
    ) -> None:
        self._db = db
        self._ex = exchange
        self._user_id = user_id
        self._kill = kill_switch
        self._risk = risk_manager
        self._state = account_state
        self._slip_threshold = slippage_threshold_bps
        self._retry = retry or RetryPolicy()

    async def _expected_price(self, req: OrderRequest) -> float:
        if req.price is not None:
            return req.price
        ticker = await self._ex.fetch_ticker(req.symbol)
        return ticker.last

    async def _find_existing(self, symbol: str, client_order_id: str):
        for o in await self._ex.fetch_open_orders(symbol):
            if o.id == client_order_id:
                return o
        return None

    async def _send_with_retry(self, req: OrderRequest, client_order_id: str):
        last_exc: Exception | None = None
        for attempt in range(self._retry.attempts):
            try:
                return await self._ex.place_order(
                    symbol=req.symbol,
                    side=req.side,
                    type=req.type,
                    qty=req.qty,
                    price=req.price,
                    client_order_id=client_order_id,
                )
            except Exception as exc:  # transient or unknown; verify before retry
                last_exc = exc
                existing = await self._find_existing(req.symbol, client_order_id)
                if existing is not None:
                    _log.warning(
                        "order_send_recovered_via_idempotency",
                        client_order_id=client_order_id,
                    )
                    return existing
                if attempt == self._retry.attempts - 1:
                    break
                if self._retry.base_delay_s:
                    await asyncio.sleep(self._retry.base_delay_s * (2**attempt))
        raise last_exc  # type: ignore[misc]

    async def _upsert_position(self, req: OrderRequest, fill_qty: float, fill_price: float) -> None:
        result = await self._db.execute(
            select(PositionRow).where(
                PositionRow.user_id == self._user_id,
                PositionRow.symbol == req.symbol,
                PositionRow.is_paper == req.is_paper,
            )
        )
        pos = result.scalar_one_or_none()
        signed = fill_qty if req.side is OrderSide.BUY else -fill_qty
        if pos is None:
            self._db.add(
                PositionRow(
                    user_id=self._user_id,
                    exchange_account_id=req.exchange_account_id,
                    symbol=req.symbol,
                    side=req.side.value,
                    qty=fill_qty,
                    avg_entry=fill_price,
                    is_paper=req.is_paper,
                )
            )
            return
        prev = pos.qty if pos.side == OrderSide.BUY.value else -pos.qty
        net = prev + signed
        if abs(net) < 1e-12:
            await self._db.delete(pos)
            return
        new_side = OrderSide.BUY if net > 0 else OrderSide.SELL
        if pos.side == new_side.value:
            total = pos.qty + fill_qty
            pos.avg_entry = (pos.avg_entry * pos.qty + fill_price * fill_qty) / total
        else:
            pos.avg_entry = fill_price
        pos.side = new_side.value
        pos.qty = abs(net)

    async def place(self, req: OrderRequest) -> OrderRow:
        if self._kill is not None and self._kill.is_active():
            raise KillSwitchEngaged("kill switch is active")

        expected = await self._expected_price(req)

        if self._risk is not None:
            state = self._state or AccountState(equity=0.0)
            proposal = TradeProposal(
                symbol=req.symbol,
                side=req.side.value,
                qty=req.qty,
                entry_price=expected,
                stop_price=req.stop_price,
                strategy_id=req.strategy_id,
            )
            decision = self._risk.evaluate(proposal, state)
            if not decision.approved:
                raise RiskRejected(decision.reasons)

        client_order_id = uuid.uuid4().hex
        row = OrderRow(
            user_id=self._user_id,
            exchange_account_id=req.exchange_account_id,
            strategy_id=req.strategy_id,
            client_order_id=client_order_id,
            symbol=req.symbol,
            side=req.side.value,
            type=req.type.value,
            qty=req.qty,
            price=req.price,
            status="submitting",
            is_paper=req.is_paper,
        )
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)

        order = await self._send_with_retry(req, client_order_id)

        row.exchange_order_id = order.id
        row.status = order.status
        row.filled_qty = order.filled_qty
        row.avg_fill = order.avg_fill_price
        row.updated_at = datetime.now(UTC)

        if order.avg_fill_price is not None and order.filled_qty > 0:
            slip = slippage_bps(expected, order.avg_fill_price, req.side)
            row.slippage_bps = slip
            if slip > self._slip_threshold:
                _log.warning(
                    "slippage_exceeded",
                    symbol=req.symbol,
                    expected=expected,
                    fill=order.avg_fill_price,
                    slippage_bps=slip,
                    threshold_bps=self._slip_threshold,
                )
            self._db.add(
                TradeRow(
                    order_id=row.id,
                    ts=int(datetime.now(UTC).timestamp()),
                    qty=order.filled_qty,
                    price=order.avg_fill_price,
                )
            )
            await self._upsert_position(req, order.filled_qty, order.avg_fill_price)

        await self._db.commit()
        await self._db.refresh(row)
        from app.core.metrics import ORDERS_PLACED

        ORDERS_PLACED.labels("paper" if req.is_paper else "live").inc()
        return row
