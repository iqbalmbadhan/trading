"""Phase 13: audit + decisions API."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.strategies.service as strategy_service
import app.workers.tasks as worker_tasks
from app.api.risk import get_kill_switch
from app.db.models import Decision, Strategy, StrategyRun
from app.main import app
from app.risk.kill_switch import KillSwitch
from tests.test_kill_switch import FakeFlagStore
from tests.test_strategies_api import FakeStop, FakeTask


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "au@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "au@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_kill_switch_trip_is_audited(client):
    app.dependency_overrides[get_kill_switch] = lambda: KillSwitch(FakeFlagStore())
    headers = _auth(client)
    client.post("/api/v1/risk/kill-switch", json={"reason": "panic"}, headers=headers)
    rows = client.get("/api/v1/audit?action=kill_switch.trip", headers=headers).json()
    assert len(rows) == 1
    assert rows[0]["after"]["reason"] == "panic"
    assert rows[0]["target"] == "kill_switch"


def test_strategy_start_is_audited(client, monkeypatch):
    monkeypatch.setattr(strategy_service, "RedisStopController", FakeStop)
    monkeypatch.setattr(worker_tasks, "run_strategy_run", FakeTask())
    headers = _auth(client)
    sid = client.post(
        "/api/v1/strategies",
        json={
            "name": "S",
            "type": "ma_crossover",
            "params": {"fast_period": 5, "slow_period": 20},
            "symbol": "BTC/USDT",
            "timeframe": "1h",
        },
        headers=headers,
    ).json()["id"]
    client.post(f"/api/v1/strategies/{sid}/start", headers=headers)
    actions = {r["action"] for r in client.get("/api/v1/audit", headers=headers).json()}
    assert "strategy.start" in actions


def test_decisions_endpoint(client):
    headers = _auth(client)
    engine = create_engine(f"sqlite:///{client.app.state.test_db_path}")
    with Session(engine) as s:
        strat = Strategy(
            user_id=1,
            name="s",
            type="ma_crossover",
            params={},
            symbol="BTC/USDT",
            timeframe="1h",
        )
        s.add(strat)
        s.flush()
        run = StrategyRun(strategy_id=strat.id, status="stopped")
        s.add(run)
        s.flush()
        s.add(
            Decision(
                strategy_run_id=run.id,
                ts=1,
                symbol="BTC/USDT",
                decision="buy",
                reasoning={"executed": True},
                indicators={"fast": 1.0, "slow": 2.0},
            )
        )
        s.commit()
        rid = run.id
    engine.dispose()

    rows = client.get(f"/api/v1/audit/decisions/{rid}", headers=headers).json()
    assert len(rows) == 1 and rows[0]["decision"] == "buy"
    assert rows[0]["indicators"]["fast"] == 1.0

    assert client.get("/api/v1/audit/decisions/99999", headers=headers).status_code == 404


def test_audit_requires_auth(client):
    assert client.get("/api/v1/audit").status_code == 401
