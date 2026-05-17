"""Phase 5: strategy CRUD + lifecycle API."""

import app.strategies.service as strategy_service
import app.workers.tasks as worker_tasks


class FakeStop:
    def __init__(self, *a, **k):
        pass

    def clear(self):
        pass

    def request_stop(self):
        pass


class FakeTask:
    def __init__(self):
        self.calls = []

    def delay(self, *args):
        self.calls.append(args)


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "s@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "s@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _valid_payload() -> dict:
    return {
        "name": "BTC MA",
        "type": "ma_crossover",
        "params": {"fast_period": 5, "slow_period": 20},
        "symbol": "BTC/USDT",
        "timeframe": "1h",
    }


def test_templates_lists_ma_crossover(client):
    headers = _auth(client)
    tpls = client.get("/api/v1/strategies/templates", headers=headers).json()
    types = {t["type"] for t in tpls}
    assert "ma_crossover" in types


def test_create_rejects_invalid_params(client):
    headers = _auth(client)
    bad = _valid_payload()
    bad["params"] = {"fast_period": 50, "slow_period": 10}  # fast >= slow
    r = client.post("/api/v1/strategies", json=bad, headers=headers)
    assert r.status_code == 400


def test_crud_and_clone(client):
    headers = _auth(client)
    created = client.post("/api/v1/strategies", json=_valid_payload(), headers=headers)
    assert created.status_code == 201
    sid = created.json()["id"]
    assert created.json()["is_paper"] is True
    assert created.json()["is_active"] is False

    assert client.get("/api/v1/strategies", headers=headers).json()[0]["id"] == sid

    patched = client.patch(
        f"/api/v1/strategies/{sid}",
        json={"params": {"fast_period": 8, "slow_period": 21}},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["version"] == 2

    cloned = client.post(f"/api/v1/strategies/{sid}/clone", headers=headers)
    assert cloned.status_code == 201
    assert cloned.json()["name"].endswith("(copy)")

    assert client.delete(f"/api/v1/strategies/{sid}", headers=headers).status_code == 204


def test_start_and_stop_lifecycle(client, monkeypatch):
    fake_task = FakeTask()
    monkeypatch.setattr(strategy_service, "RedisStopController", FakeStop)
    monkeypatch.setattr(worker_tasks, "run_strategy_run", fake_task)

    headers = _auth(client)
    sid = client.post("/api/v1/strategies", json=_valid_payload(), headers=headers).json()["id"]

    started = client.post(f"/api/v1/strategies/{sid}/start", headers=headers)
    assert started.status_code == 200
    run_id = started.json()["id"]
    assert fake_task.calls == [(run_id,)]
    assert client.get(f"/api/v1/strategies/{sid}", headers=headers).json()["is_active"]

    # Cannot start twice or edit while running.
    assert client.post(f"/api/v1/strategies/{sid}/start", headers=headers).status_code == 409
    assert (
        client.patch(
            f"/api/v1/strategies/{sid}",
            json={"name": "x"},
            headers=headers,
        ).status_code
        == 400
    )

    assert client.post(f"/api/v1/strategies/{sid}/stop", headers=headers).status_code == 204
    assert client.get(f"/api/v1/strategies/{sid}", headers=headers).json()["is_active"] is False
