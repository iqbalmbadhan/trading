"""Phase 7: slippage measurement."""

import pytest

from app.exchanges.base import OrderSide
from app.execution.slippage import exceeds_threshold, slippage_bps


def test_buy_above_expected_is_adverse():
    assert slippage_bps(100.0, 101.0, OrderSide.BUY) == pytest.approx(100.0)


def test_sell_below_expected_is_adverse():
    assert slippage_bps(100.0, 99.0, OrderSide.SELL) == pytest.approx(100.0)


def test_favorable_fill_is_negative():
    assert slippage_bps(100.0, 99.0, OrderSide.BUY) == pytest.approx(-100.0)


def test_threshold():
    assert exceeds_threshold(100.0, 101.0, OrderSide.BUY, threshold_bps=50.0)
    assert not exceeds_threshold(100.0, 100.2, OrderSide.BUY, threshold_bps=50.0)
