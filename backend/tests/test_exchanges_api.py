"""Phase 3: exchange connect API enforces trade-only keys."""

from app.exchanges import service
from app.exchanges.base import ExchangePermissions


class _FakeExchange:
    def __init__(self, can_withdraw: bool) -> None:
        self._can_withdraw = can_withdraw

    async def verify_permissions(self) -> ExchangePermissions:
        return ExchangePermissions(can_trade=True, can_withdraw=self._can_withdraw)

    async def fetch_balance(self) -> dict[str, float]:
        return {"USDT": 1234.0}

    async def close(self) -> None:
        return None


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "t@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "t@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_connect_rejects_withdrawal_scoped_key(client, monkeypatch):
    monkeypatch.setattr(service, "build_exchange", lambda *a, **k: _FakeExchange(can_withdraw=True))
    headers = _auth(client)
    r = client.post(
        "/api/v1/exchanges/connect",
        headers=headers,
        json={
            "exchange": "binance",
            "label": "main",
            "api_key": "key-with-withdrawal",
            "secret": "secret-value",
        },
    )
    assert r.status_code == 400
    assert "withdrawal" in r.json()["detail"].lower()
    assert client.get("/api/v1/exchanges", headers=headers).json() == []


def test_connect_accepts_trade_only_and_hides_secrets(client, monkeypatch):
    monkeypatch.setattr(
        service, "build_exchange", lambda *a, **k: _FakeExchange(can_withdraw=False)
    )
    headers = _auth(client)
    r = client.post(
        "/api/v1/exchanges/connect",
        headers=headers,
        json={
            "exchange": "binance",
            "label": "main",
            "api_key": "trade-only-key",
            "secret": "secret-value",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["permissions_verified"] is True
    assert "secret" not in body and "api_key" not in body

    listed = client.get("/api/v1/exchanges", headers=headers).json()
    assert len(listed) == 1 and listed[0]["exchange"] == "binance"

    test_resp = client.post(f"/api/v1/exchanges/{body['id']}/test", headers=headers)
    assert test_resp.status_code == 200
    assert test_resp.json()["balances"] == {"USDT": 1234.0}


def test_connect_requires_auth(client):
    r = client.post(
        "/api/v1/exchanges/connect",
        json={
            "exchange": "binance",
            "label": "main",
            "api_key": "trade-only-key",
            "secret": "secret-value",
        },
    )
    assert r.status_code == 401
