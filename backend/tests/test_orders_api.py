"""Phase 7: orders/positions API and the two-step live-trading gate."""

import app.api.orders as orders_api
from app.api.risk import get_kill_switch
from app.exchanges.base import Ticker
from app.exchanges.paper import PaperExchange
from app.main import app
from app.risk.kill_switch import KillSwitch
from tests.test_kill_switch import FakeFlagStore

PHRASE = "I UNDERSTAND I CAN LOSE MONEY"


def _src(p: float):
    async def _s(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=p, ask=p, last=p)

    return _s


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "o@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "o@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wire(monkeypatch, store: FakeFlagStore | None = None):
    store = store or FakeFlagStore()
    ks = KillSwitch(store)
    app.dependency_overrides[get_kill_switch] = lambda: ks

    async def _fake_exchange(*a, **k):
        return PaperExchange(_src(100.0), starting_cash=10_000.0, slippage_bps=0.0)

    monkeypatch.setattr(orders_api, "build_execution_exchange", _fake_exchange)
    return store


def test_live_gate_blocks_until_phrase(client, monkeypatch):
    _wire(monkeypatch)
    headers = _auth(client)

    status = client.get("/api/v1/account/live-trading", headers=headers).json()
    assert status["live_trading_enabled"] is False

    blocked = client.post(
        "/api/v1/orders/manual-place",
        json={"symbol": "BTC/USDT", "side": "buy", "qty": 1, "stop_price": 99, "live": True},
        headers=headers,
    )
    assert blocked.status_code == 403

    bad = client.post(
        "/api/v1/account/live-trading",
        json={"confirm_phrase": "let me trade"},
        headers=headers,
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/v1/account/live-trading",
        json={"confirm_phrase": PHRASE},
        headers=headers,
    )
    assert ok.status_code == 200 and ok.json()["live_trading_enabled"] is True


def test_paper_order_lifecycle(client, monkeypatch):
    _wire(monkeypatch)
    headers = _auth(client)

    placed = client.post(
        "/api/v1/orders/manual-place",
        json={"symbol": "BTC/USDT", "side": "buy", "qty": 2, "stop_price": 99},
        headers=headers,
    )
    assert placed.status_code == 201
    body = placed.json()
    assert body["status"] == "closed" and body["is_paper"] is True
    oid = body["id"]

    listed = client.get("/api/v1/orders", headers=headers).json()
    assert len(listed) == 1 and listed[0]["id"] == oid
    assert client.get(f"/api/v1/orders/{oid}", headers=headers).status_code == 200

    positions = client.get("/api/v1/positions", headers=headers).json()
    assert len(positions) == 1 and positions[0]["symbol"] == "BTC/USDT"
    pid = positions[0]["id"]
    assert client.post(f"/api/v1/positions/{pid}/close", headers=headers).status_code == 204
    assert client.get("/api/v1/positions", headers=headers).json() == []


def test_cancel_resting_order(client, monkeypatch):
    _wire(monkeypatch)
    headers = _auth(client)
    placed = client.post(
        "/api/v1/orders/manual-place",
        json={
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "qty": 1,
            "price": 1.0,
            "stop_price": 0.5,
        },
        headers=headers,
    ).json()
    assert placed["status"] == "open"
    cancelled = client.post(f"/api/v1/orders/{placed['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "canceled"


def test_kill_switch_blocks_manual_order(client, monkeypatch):
    store = _wire(monkeypatch)
    headers = _auth(client)
    KillSwitch(store).trip("manual")
    r = client.post(
        "/api/v1/orders/manual-place",
        json={"symbol": "BTC/USDT", "side": "buy", "qty": 1, "stop_price": 99},
        headers=headers,
    )
    assert r.status_code == 409


def test_risk_rejects_without_stop(client, monkeypatch):
    _wire(monkeypatch)
    headers = _auth(client)
    r = client.post(
        "/api/v1/orders/manual-place",
        json={"symbol": "BTC/USDT", "side": "buy", "qty": 1},
        headers=headers,
    )
    assert r.status_code == 422
    assert "stop-loss" in r.json()["detail"]
