"""Phase 10: portfolio API."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.portfolio import get_price_provider
from app.db.models import Candle, Position, Symbol
from app.main import app


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "p@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "p@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _fixed_prices(mapping):
    async def _p(symbol: str) -> float:
        return mapping.get(symbol, 0.0)

    return lambda: _p


def _seed_positions(client):
    engine = create_engine(f"sqlite:///{client.app.state.test_db_path}")
    with Session(engine) as s:
        s.add(Position(user_id=1, symbol="BTC/USDT", side="buy", qty=1.0, avg_entry=90))
        s.add(Position(user_id=1, symbol="ETH/USDT", side="buy", qty=2.0, avg_entry=40))
        s.commit()
    engine.dispose()


def test_summary_and_allocation(client):
    headers = _auth(client)
    _seed_positions(client)
    app.dependency_overrides[get_price_provider] = _fixed_prices(
        {"BTC/USDT": 100.0, "ETH/USDT": 50.0}
    )

    summary = client.get("/api/v1/portfolio/summary", headers=headers).json()
    assert summary["total_value_usd"] == 100.0 + 100.0
    symbols = {h["symbol"]: h["value_usd"] for h in summary["holdings"]}
    assert symbols["BTC/USDT"] == 100.0 and symbols["ETH/USDT"] == 100.0

    alloc = client.get("/api/v1/portfolio/allocation", headers=headers).json()
    assert alloc["allocation"]["BTC/USDT"] == 0.5
    assert alloc["exposure_by_base"]["ETH"] == 0.5


def test_correlation(client):
    headers = _auth(client)
    _seed_positions(client)
    engine = create_engine(f"sqlite:///{client.app.state.test_db_path}")
    with Session(engine) as s:
        for name in ("BTC/USDT", "ETH/USDT"):
            sym = Symbol(exchange="binance", symbol=name, base="X", quote="USDT")
            s.add(sym)
            s.flush()
            for i, c in enumerate([100, 110, 99, 120, 105]):
                s.add(
                    Candle(
                        symbol_id=sym.id,
                        timeframe="1h",
                        ts=i * 3600,
                        o=c,
                        h=c,
                        l=c,
                        c=c,
                        v=1.0,
                    )
                )
        s.commit()
    engine.dispose()

    matrix = client.get("/api/v1/portfolio/correlation", headers=headers).json()["matrix"]
    assert matrix["BTC/USDT"]["BTC/USDT"] == 1.0
    # Identical close series -> perfectly correlated.
    assert matrix["BTC/USDT"]["ETH/USDT"] == 1.0


def test_portfolio_requires_auth(client):
    assert client.get("/api/v1/portfolio/summary").status_code == 401
