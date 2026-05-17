"""Phase 7: locally-simulated bracket / OCO."""

import pytest

from app.exchanges.base import OrderSide
from app.execution.bracket import Bracket


def test_long_target_then_oco():
    b = Bracket(OrderSide.BUY, entry_price=100, stop_price=95, target_price=110)
    assert b.on_price(105) is None
    assert b.on_price(111) == "target"
    assert b.done is True
    # One-cancels-other: further prices do nothing.
    assert b.on_price(94) is None


def test_long_stop():
    b = Bracket(OrderSide.BUY, entry_price=100, stop_price=95, target_price=110)
    assert b.on_price(94) == "stop"


def test_short_legs():
    b = Bracket(OrderSide.SELL, entry_price=100, stop_price=105, target_price=90)
    assert b.on_price(101) is None
    assert b.on_price(89) == "target"

    b2 = Bracket(OrderSide.SELL, entry_price=100, stop_price=105, target_price=90)
    assert b2.on_price(106) == "stop"


def test_invalid_bracket_geometry():
    with pytest.raises(ValueError):
        Bracket(OrderSide.BUY, entry_price=100, stop_price=110, target_price=120)
    with pytest.raises(ValueError):
        Bracket(OrderSide.SELL, entry_price=100, stop_price=90, target_price=80)
