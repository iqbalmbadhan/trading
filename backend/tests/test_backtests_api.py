"""Phase 8: backtests API."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.workers.tasks as worker_tasks
from app.db.models import Backtest


class FakeTask:
    def __init__(self):
        self.calls = []

    def delay(self, *a):
        self.calls.append(a)


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "b@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_dispatches_and_lists(client, monkeypatch):
    fake = FakeTask()
    monkeypatch.setattr(worker_tasks, "run_backtest_task", fake)
    headers = _auth(client)

    r = client.post(
        "/api/v1/backtests",
        json={
            "type": "ma_crossover",
            "params": {"fast_period": 5, "slow_period": 20},
            "symbol": "BTC/USDT",
            "timeframe": "1h",
        },
        headers=headers,
    )
    assert r.status_code == 202
    bid = r.json()["id"]
    assert r.json()["status"] == "queued"
    assert fake.calls == [(bid,)]

    listed = client.get("/api/v1/backtests", headers=headers).json()
    assert len(listed) == 1 and listed[0]["id"] == bid


def test_unknown_strategy_rejected(client, monkeypatch):
    monkeypatch.setattr(worker_tasks, "run_backtest_task", FakeTask())
    headers = _auth(client)
    r = client.post(
        "/api/v1/backtests",
        json={"type": "nope", "symbol": "BTC/USDT"},
        headers=headers,
    )
    assert r.status_code == 400


def test_report_and_csv_for_finished_backtest(client):
    headers = _auth(client)
    engine = create_engine(f"sqlite:///{client.app.state.test_db_path}")
    with Session(engine) as s:
        bt = Backtest(
            user_id=1,
            type="ma_crossover",
            params={},
            symbol="BTC/USDT",
            timeframe="1h",
            status="finished",
            metrics={"sharpe": 1.5, "total_return": 0.2},
            monte_carlo={"total_return_p50": 0.1},
            equity_curve=[[0, 100.0], [1, 110.0]],
            trade_pnls=[10.0, -3.0],
        )
        s.add(bt)
        s.commit()
        bid = bt.id
    engine.dispose()

    got = client.get(f"/api/v1/backtests/{bid}", headers=headers).json()
    assert got["status"] == "finished" and got["metrics"]["sharpe"] == 1.5

    report = client.get(f"/api/v1/backtests/{bid}/report", headers=headers)
    assert report.status_code == 200 and "<html" in report.text
    assert "sharpe" in report.text

    csv = client.get(f"/api/v1/backtests/{bid}/trades.csv", headers=headers)
    assert csv.status_code == 200
    assert csv.text.splitlines()[0] == "trade,pnl,cumulative_pnl"

    assert client.delete(f"/api/v1/backtests/{bid}", headers=headers).status_code == 204


def test_backtests_require_auth(client):
    assert client.get("/api/v1/backtests").status_code == 401
