"""Phase 10: holdings valuation."""

import pytest

from app.portfolio.valuation import (
    allocation,
    base_of,
    exposure_by_base,
    total_value_usd,
    value_holdings,
)


def test_base_of():
    assert base_of("BTC/USDT") == "BTC"
    assert base_of("ETH/USDT:USDT") == "ETH"


def test_long_and_short_valuation():
    positions = [
        {"symbol": "BTC/USDT", "qty": 2.0, "side": "buy", "is_paper": True},
        {"symbol": "ETH/USDT", "qty": 10.0, "side": "sell", "is_paper": False},
    ]
    prices = {"BTC/USDT": 100.0, "ETH/USDT": 20.0}
    h = value_holdings(positions, prices)
    assert h[0].value_usd == pytest.approx(200.0)
    assert h[1].value_usd == pytest.approx(-200.0)  # short = negative delta
    assert total_value_usd(h) == pytest.approx(0.0)


def test_allocation_and_exposure():
    positions = [
        {"symbol": "BTC/USDT", "qty": 1.0, "side": "buy"},
        {"symbol": "ETH/USDT", "qty": 1.0, "side": "buy"},
    ]
    h = value_holdings(positions, {"BTC/USDT": 300.0, "ETH/USDT": 100.0})
    alloc = allocation(h)
    assert alloc["BTC/USDT"] == pytest.approx(0.75)
    assert alloc["ETH/USDT"] == pytest.approx(0.25)
    assert exposure_by_base(h)["BTC"] == pytest.approx(0.75)


def test_empty_portfolio():
    assert allocation([]) == {}
    assert exposure_by_base([]) == {}
