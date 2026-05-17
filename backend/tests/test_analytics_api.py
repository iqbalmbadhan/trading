"""Phase 10: analytics API."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Backtest


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed(client):
    engine = create_engine(f"sqlite:///{client.app.state.test_db_path}")
    with Session(engine) as s:
        s.add(
            Backtest(
                user_id=1,
                type="ma_crossover",
                params={},
                symbol="BTC/USDT",
                timeframe="1h",
                status="finished",
                metrics={"sharpe": 2.0, "total_return": 0.3},
                equity_curve=[[0, 100.0], [1, 120.0], [2, 110.0]],
                trade_pnls=[10.0],
            )
        )
        s.add(
            Backtest(
                user_id=1,
                type="ma_crossover",
                params={},
                symbol="ETH/USDT",
                timeframe="1h",
                status="finished",
                metrics={"sharpe": 1.0, "total_return": 0.1},
                equity_curve=[[0, 100.0]],
                trade_pnls=[],
            )
        )
        s.commit()
        bid = s.query(Backtest).filter(Backtest.symbol == "BTC/USDT").first().id
    engine.dispose()
    return bid


def test_metrics_and_comparison(client):
    headers = _auth(client)
    _seed(client)

    metrics = client.get("/api/v1/analytics/metrics", headers=headers).json()
    assert metrics["backtests"] == 2
    assert metrics["best_sharpe"] == 2.0
    assert metrics["best_type"] == "ma_crossover"

    comp = client.get("/api/v1/analytics/strategy-comparison", headers=headers).json()
    assert len(comp) == 1
    row = comp[0]
    assert row["type"] == "ma_crossover" and row["backtests"] == 2
    assert row["sharpe"] == 1.5  # average of 2.0 and 1.0


def test_equity_curve_with_drawdown(client):
    headers = _auth(client)
    bid = _seed(client)
    data = client.get(f"/api/v1/analytics/equity-curve/{bid}", headers=headers).json()
    assert data["equity_curve"][0] == [0, 100.0]
    # peak 120 then 110 -> drawdown ~ -0.0833 on the last point
    assert data["drawdown"][-1][1] < 0


def test_analytics_requires_auth(client):
    assert client.get("/api/v1/analytics/metrics").status_code == 401
