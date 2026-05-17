"""Phase 7: live order router — fills, idempotency, retries, risk, kill switch."""

import pytest
from sqlalchemy import select

from app.db.models import Order, Position, Trade, User
from app.exchanges.base import OrderSide, OrderType, Ticker
from app.exchanges.errors import OrderError
from app.exchanges.paper import PaperExchange
from app.execution.errors import KillSwitchEngaged, RiskRejected
from app.execution.router import LiveOrderRouter, OrderRequest, RetryPolicy
from app.risk.config import AccountState, RiskConfig
from app.risk.kill_switch import KillSwitch
from app.risk.manager import RiskManager
from tests.test_kill_switch import FakeFlagStore


def _src(p: float):
    async def _s(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=p, ask=p, last=p)

    return _s


async def _user(db) -> int:
    u = User(email="o@example.com", password_hash="x")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u.id


async def test_happy_path_persists_order_trade_position(db_session):
    uid = await _user(db_session)
    ex = PaperExchange(_src(100.0), starting_cash=10_000.0, slippage_bps=0.0)
    r = LiveOrderRouter(db_session, ex, uid)
    order = await r.place(OrderRequest("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=2.0))
    assert order.status == "closed"
    assert order.filled_qty == 2.0
    assert order.avg_fill == 100.0
    assert order.slippage_bps == pytest.approx(0.0)

    trades = (await db_session.execute(select(Trade))).scalars().all()
    assert len(trades) == 1 and trades[0].qty == 2.0
    pos = (await db_session.execute(select(Position))).scalars().all()
    assert len(pos) == 1 and pos[0].symbol == "BTC/USDT" and pos[0].qty == 2.0


async def test_kill_switch_blocks_before_persist(db_session):
    uid = await _user(db_session)
    ks = KillSwitch(FakeFlagStore())
    ks.trip("manual")
    ex = PaperExchange(_src(100.0), starting_cash=10_000.0)
    r = LiveOrderRouter(db_session, ex, uid, kill_switch=ks)
    with pytest.raises(KillSwitchEngaged):
        await r.place(OrderRequest("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 1.0))
    assert (await db_session.execute(select(Order))).scalars().all() == []


async def test_risk_rejection(db_session):
    uid = await _user(db_session)
    ex = PaperExchange(_src(100.0), starting_cash=10_000.0)
    mgr = RiskManager(RiskConfig(require_stop_loss=True))
    r = LiveOrderRouter(
        db_session, ex, uid, risk_manager=mgr, account_state=AccountState(equity=1000)
    )
    with pytest.raises(RiskRejected) as ei:
        await r.place(OrderRequest("BTC/USDT", OrderSide.BUY, OrderType.MARKET, 1.0))
    assert "stop-loss" in str(ei.value)


class LandsThenFails:
    """First send reaches the exchange (resting) but the ack is lost."""

    def __init__(self, inner: PaperExchange) -> None:
        self._inner = inner
        self.place_calls = 0

    async def fetch_ticker(self, symbol):
        return await self._inner.fetch_ticker(symbol)

    async def place_order(self, **kw):
        self.place_calls += 1
        await self._inner.place_order(**kw)  # actually lands as a resting order
        raise OrderError("connection reset after send")

    async def fetch_open_orders(self, symbol=None):
        return await self._inner.fetch_open_orders(symbol)

    async def close(self):
        return None


async def test_idempotency_does_not_duplicate(db_session):
    uid = await _user(db_session)
    inner = PaperExchange(_src(100.0), starting_cash=10_000.0)
    ex = LandsThenFails(inner)
    r = LiveOrderRouter(db_session, ex, uid, retry=RetryPolicy(attempts=3))
    order = await r.place(
        OrderRequest("BTC/USDT", OrderSide.BUY, OrderType.LIMIT, qty=1.0, price=50.0)
    )
    # Sent once; recovered the already-resting order instead of resending.
    assert ex.place_calls == 1
    assert order.status == "open"
    assert len(await inner.fetch_open_orders()) == 1


class TransientThenOk:
    def __init__(self, inner: PaperExchange) -> None:
        self._inner = inner
        self.place_calls = 0

    async def fetch_ticker(self, symbol):
        return await self._inner.fetch_ticker(symbol)

    async def place_order(self, **kw):
        self.place_calls += 1
        if self.place_calls == 1:
            raise OrderError("temporary 503")
        return await self._inner.place_order(**kw)

    async def fetch_open_orders(self, symbol=None):
        return []  # nothing landed on the failed attempt

    async def close(self):
        return None


async def test_retry_after_transient_failure(db_session):
    uid = await _user(db_session)
    inner = PaperExchange(_src(100.0), starting_cash=10_000.0, slippage_bps=0.0)
    ex = TransientThenOk(inner)
    r = LiveOrderRouter(db_session, ex, uid, retry=RetryPolicy(attempts=3))
    order = await r.place(OrderRequest("BTC/USDT", OrderSide.BUY, OrderType.MARKET, qty=1.0))
    assert ex.place_calls == 2
    assert order.status == "closed" and order.filled_qty == 1.0
