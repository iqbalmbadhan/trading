"""Phase 11: alerts API + dispatch via kill switch."""

import app.alerts.channels as channels
from app.api.risk import get_kill_switch
from app.main import app
from app.risk.kill_switch import KillSwitch
from tests.test_kill_switch import FakeFlagStore


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "al@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "al@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _capture_http(monkeypatch) -> list:
    calls = []

    async def _fake(url, payload):
        calls.append((url, payload))

    monkeypatch.setattr(channels, "_http_post", _fake)
    return calls


def test_rule_crud_and_validation(client):
    headers = _auth(client)

    bad_event = client.post(
        "/api/v1/alerts",
        json={"channel": "webhook", "event_type": "nope", "config": {}},
        headers=headers,
    )
    assert bad_event.status_code == 400

    bad_channel = client.post(
        "/api/v1/alerts",
        json={"channel": "fax", "event_type": "new_fill", "config": {}},
        headers=headers,
    )
    assert bad_channel.status_code == 400

    created = client.post(
        "/api/v1/alerts",
        json={
            "channel": "webhook",
            "event_type": "kill_switch",
            "config": {"url": "https://hook.test/x"},
        },
        headers=headers,
    )
    assert created.status_code == 201
    rid = created.json()["id"]

    assert len(client.get("/api/v1/alerts", headers=headers).json()) == 1
    patched = client.patch(f"/api/v1/alerts/{rid}", json={"is_enabled": False}, headers=headers)
    assert patched.json()["is_enabled"] is False
    assert client.delete(f"/api/v1/alerts/{rid}", headers=headers).status_code == 204


def test_test_send_records_history(client, monkeypatch):
    calls = _capture_http(monkeypatch)
    headers = _auth(client)
    rid = client.post(
        "/api/v1/alerts",
        json={
            "channel": "webhook",
            "event_type": "new_fill",
            "config": {"url": "https://hook.test/x"},
        },
        headers=headers,
    ).json()["id"]

    r = client.post(f"/api/v1/alerts/{rid}/test", headers=headers)
    assert r.status_code == 200 and r.json()["sent"] is True
    assert len(calls) == 1

    history = client.get("/api/v1/alerts/history", headers=headers).json()
    assert history[0]["status"] == "sent"
    assert history[0]["event_type"] == "test"


def test_kill_switch_trip_dispatches_alert(client, monkeypatch):
    calls = _capture_http(monkeypatch)
    app.dependency_overrides[get_kill_switch] = lambda: KillSwitch(FakeFlagStore())
    headers = _auth(client)
    client.post(
        "/api/v1/alerts",
        json={
            "channel": "webhook",
            "event_type": "kill_switch",
            "config": {"url": "https://hook.test/ks"},
        },
        headers=headers,
    )
    r = client.post("/api/v1/risk/kill-switch", json={"reason": "panic"}, headers=headers)
    assert r.status_code == 200
    assert any("hook.test/ks" in url for url, _ in calls)
    history = client.get("/api/v1/alerts/history", headers=headers).json()
    assert any(h["event_type"] == "kill_switch" for h in history)


def test_alerts_require_auth(client):
    assert client.get("/api/v1/alerts").status_code == 401
