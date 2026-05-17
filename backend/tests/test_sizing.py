"""Phase 6: position sizing math, including property-based tests."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.risk.sizing import (
    MAX_KELLY_FRACTION,
    fixed_fractional,
    fractional_kelly,
    volatility_adjusted,
)


def test_fixed_fractional_basic():
    # equity 10000, risk 1%, stop distance 1 -> 100 units
    assert fixed_fractional(10_000, 0.01, 100.0, 99.0) == pytest.approx(100.0)


def test_fixed_fractional_zero_distance():
    assert fixed_fractional(10_000, 0.01, 100.0, 100.0) == 0.0


def test_volatility_adjusted_basic():
    # risk budget 100, atr*mult = 2 -> 50 units
    assert volatility_adjusted(10_000, 0.01, 1.0, 2.0) == pytest.approx(50.0)


def test_kelly_capped_and_bounds():
    with pytest.raises(ValueError):
        fractional_kelly(10_000, 1.5, 2.0, 100.0)
    # Negative-edge bet sizes to zero.
    assert fractional_kelly(10_000, 0.4, 1.0, 100.0) == 0.0


@given(
    equity=st.floats(min_value=1.0, max_value=1e9, allow_nan=False),
    risk_pct=st.floats(min_value=1e-4, max_value=1.0),
    entry=st.floats(min_value=0.01, max_value=1e6, allow_nan=False),
    distance=st.floats(min_value=0.01, max_value=1e5, allow_nan=False),
)
def test_fixed_fractional_never_exceeds_budget(equity, risk_pct, entry, distance):
    stop = entry + distance
    qty = fixed_fractional(equity, risk_pct, entry, stop)
    risk_taken = qty * abs(entry - stop)
    assert qty >= 0
    assert risk_taken <= equity * risk_pct + 1e-6


@given(
    equity=st.floats(min_value=1.0, max_value=1e9, allow_nan=False),
    win_prob=st.floats(min_value=0.0, max_value=1.0),
    wl=st.floats(min_value=0.1, max_value=10.0),
    price=st.floats(min_value=0.01, max_value=1e6, allow_nan=False),
    frac=st.floats(min_value=0.0, max_value=1.0),
)
def test_kelly_capped_at_quarter(equity, win_prob, wl, price, frac):
    qty = fractional_kelly(equity, win_prob, wl, price, kelly_fraction=frac)
    assert qty >= 0
    full = win_prob - (1.0 - win_prob) / wl
    cap_qty = (equity * max(full, 0.0) * MAX_KELLY_FRACTION) / price
    assert qty <= cap_qty + 1e-6
