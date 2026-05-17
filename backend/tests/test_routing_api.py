"""Phase 12: smart routing API."""

import app.api.routing as routing_api
from app.exchanges.base import Ticker
from app.exchanges.paper import PaperExchange


def _paper(price: float) -> PaperExchange:
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=price, ask=price, last=price)

    return PaperExchange(_src, starting_cash=1_000_000.0, slippage_bps=0.0)


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "rt@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "rt@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wire(monkeypatch):
    async def _adapters(db, user_id):
        return {"venueA": _paper(100.0), "venueB": _paper(108.0)}

    monkeypatch.setattr(routing_api, "build_routing_adapters", _adapters)


def test_smart_quote_allocations(client, monkeypatch):
    _wire(monkeypatch)
    headers = _auth(client)
    r = client.post(
        "/api/v1/routing/quote",
        json={"symbol": "BTC/USDT", "side": "buy", "qty": 4, "per_venue_cap": 3},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allocations"][0]["venue"] == "venueA"  # cheaper first
    assert body["filled_qty"] == 4
    assert body["unfilled_qty"] == 0


def test_smart_execute_paper(client, monkeypatch):
    _wire(monkeypatch)
    headers = _auth(client)
    r = client.post(
        "/api/v1/routing/execute",
        json={"symbol": "BTC/USDT", "side": "buy", "qty": 2, "per_venue_cap": 1},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filled_qty"] == 2
    assert {f["venue"] for f in body["fills"]} == {"venueA", "venueB"}


def test_routing_requires_auth(client):
    assert (
        client.post(
            "/api/v1/routing/quote",
            json={"symbol": "BTC/USDT", "side": "buy", "qty": 1},
        ).status_code
        == 401
    )
