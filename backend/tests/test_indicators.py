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


def test_rsi_all_gains_is_100():
    from app.strategies.indicators import rsi

    out = rsi([1, 2, 3, 4, 5, 6], 2)
    assert out[1] is None
    assert out[-1] == pytest.approx(100.0)


def test_rsi_known_values():
    from app.strategies.indicators import rsi

    out = rsi([10, 11, 10, 11, 10, 11, 12, 9], 2)
    assert out[2] == pytest.approx(50.0)
    assert out[3] == pytest.approx(75.0)


def test_bollinger_constant_collapses_bands():
    from app.strategies.indicators import bollinger

    mid, upper, lower = bollinger([10, 10, 10, 10], 3, 2.0)
    assert mid[-1] == 10.0 and upper[-1] == 10.0 and lower[-1] == 10.0


def test_donchian_trailing_window():
    from app.strategies.indicators import donchian

    up, lo = donchian([1, 3, 2, 5, 4], [1, 1, 1, 1, 1], 3)
    assert up == [None, None, 3, 5, 5]
    assert lo == [None, None, 1, 1, 1]
