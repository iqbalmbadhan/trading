"""Phase 15: Prometheus metrics endpoint and domain counters."""

from app.api.risk import get_kill_switch
from app.main import app
from app.risk.kill_switch import KillSwitch
from tests.test_kill_switch import FakeFlagStore


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "m@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "m@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _counter_value(text: str, name: str) -> float:
    total = 0.0
    for line in text.splitlines():
        if line.startswith(name) and not line.startswith(name + "_"):
            total += float(line.rsplit(" ", 1)[1])
    return total


def test_metrics_endpoint_exposes_http_metrics(client):
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body


def test_kill_switch_trip_increments_counter(client):
    app.dependency_overrides[get_kill_switch] = lambda: KillSwitch(FakeFlagStore())
    headers = _auth(client)

    before = _counter_value(client.get("/metrics").text, "kill_switch_trips_total")
    r = client.post("/api/v1/risk/kill-switch", json={"reason": "panic"}, headers=headers)
    assert r.status_code == 200
    after = _counter_value(client.get("/metrics").text, "kill_switch_trips_total")
    assert after >= before + 1
