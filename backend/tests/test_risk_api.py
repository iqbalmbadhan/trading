"""Phase 6: risk rules + kill-switch API."""

from app.api.risk import get_kill_switch
from app.main import app
from app.risk.kill_switch import KillSwitch
from tests.test_kill_switch import FakeFlagStore


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "r@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "r@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _use_fake_kill_switch():
    ks = KillSwitch(FakeFlagStore())
    app.dependency_overrides[get_kill_switch] = lambda: ks
    return ks


def test_rules_defaults_and_update(client):
    headers = _auth(client)
    rules = client.get("/api/v1/risk/rules", headers=headers).json()
    assert rules["max_trade_risk_pct"] == 0.01
    assert rules["require_stop_loss"] is True

    updated = dict(rules)
    updated["max_trade_risk_pct"] = 0.02
    updated["blacklist"] = ["DOGE/USDT"]
    put = client.put("/api/v1/risk/rules", json=updated, headers=headers)
    assert put.status_code == 200
    assert put.json()["max_trade_risk_pct"] == 0.02

    again = client.get("/api/v1/risk/rules", headers=headers).json()
    assert again["blacklist"] == ["DOGE/USDT"]


def test_kill_switch_trip_and_clear(client):
    _use_fake_kill_switch()
    headers = _auth(client)

    assert client.get("/api/v1/risk/kill-switch-status", headers=headers).json() == {
        "active": False,
        "reason": None,
    }

    tripped = client.post(
        "/api/v1/risk/kill-switch",
        json={"reason": "daily loss"},
        headers=headers,
    )
    assert tripped.status_code == 200 and tripped.json()["active"] is True

    status = client.get("/api/v1/risk/kill-switch-status", headers=headers).json()
    assert status == {"active": True, "reason": "daily loss"}

    events = client.get("/api/v1/risk/kill-switch/events", headers=headers).json()
    assert len(events) == 1
    assert events[0]["reason"] == "daily loss"
    assert events[0]["resolved_at"] is None

    cleared = client.post("/api/v1/risk/kill-switch/clear", headers=headers)
    assert cleared.json()["active"] is False
    assert client.get("/api/v1/risk/kill-switch-status", headers=headers).json()["active"] is False
    events = client.get("/api/v1/risk/kill-switch/events", headers=headers).json()
    assert events[0]["resolved_at"] is not None


def test_risk_endpoints_require_auth(client):
    assert client.get("/api/v1/risk/rules").status_code == 401
    assert client.post("/api/v1/risk/kill-switch", json={}).status_code == 401
