"""Phase 5: indicator math."""

import pytest

from app.strategies.indicators import atr, sma


def test_sma_warmup_and_values():
    out = sma([1, 2, 3, 4, 5], 3)
    assert out[0] is None and out[1] is None
    assert out[2] == pytest.approx(2.0)
    assert out[3] == pytest.approx(3.0)
    assert out[4] == pytest.approx(4.0)


def test_sma_invalid_period():
    with pytest.raises(ValueError):
        sma([1, 2], 0)


def test_atr_constant_range():
    highs = [11, 11, 11, 11]
    lows = [9, 9, 9, 9]
    closes = [10, 10, 10, 10]
    out = atr(highs, lows, closes, 2)
    assert out[0] is None
    # TR is a constant 2.0, so ATR converges to 2.0.
    assert out[1] == pytest.approx(2.0)
    assert out[-1] == pytest.approx(2.0)


def test_atr_length_mismatch():
    with pytest.raises(ValueError):
        atr([1, 2], [1], [1, 2], 2)
