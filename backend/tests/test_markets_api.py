"""Phase 4: market data read API."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Candle, Symbol


def _auth(client) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": "md@example.com", "password": "supersecret1"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "md@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed(client) -> int:
    """Insert a symbol + 3 candles directly via a sync session (no event loop)."""
    engine = create_engine(f"sqlite:///{client.app.state.test_db_path}")
    with Session(engine) as s:
        sym = Symbol(
            exchange="binance",
            symbol="BTC/USDT",
            base="BTC",
            quote="USDT",
            contract_type="spot",
        )
        s.add(sym)
        s.flush()
        for i in range(3):
            s.add(
                Candle(
                    symbol_id=sym.id,
                    timeframe="1m",
                    ts=i * 60,
                    o=1.0,
                    h=2.0,
                    l=0.5,
                    c=1.5,
                    v=float(i),
                )
            )
        s.commit()
        symbol_id = sym.id
    engine.dispose()
    return symbol_id


def test_candles_endpoint_requires_auth(client):
    assert client.get("/api/v1/markets/candles?symbol_id=1").status_code == 401


def test_symbols_and_candles_roundtrip(client):
    headers = _auth(client)
    assert client.get("/api/v1/markets/symbols", headers=headers).json() == []

    symbol_id = _seed(client)

    symbols = client.get("/api/v1/markets/symbols", headers=headers).json()
    assert len(symbols) == 1 and symbols[0]["symbol"] == "BTC/USDT"

    candles = client.get(
        f"/api/v1/markets/candles?symbol_id={symbol_id}&timeframe=1m",
        headers=headers,
    ).json()
    assert [c["ts"] for c in candles] == [0, 60, 120]
    assert candles[0]["o"] == 1.0 and candles[0]["c"] == 1.5

    windowed = client.get(
        f"/api/v1/markets/candles?symbol_id={symbol_id}&timeframe=1m&start=60&end=60",
        headers=headers,
    ).json()
    assert [c["ts"] for c in windowed] == [60]
