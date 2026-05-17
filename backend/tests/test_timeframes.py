"""Phase 4: timeframe math and candle rollup."""

import pytest

from app.market_data.timeframes import bucket_start, rollup, timeframe_seconds


def test_timeframe_seconds():
    assert timeframe_seconds("1m") == 60
    assert timeframe_seconds("1h") == 3600
    assert timeframe_seconds("1d") == 86400
    with pytest.raises(ValueError):
        timeframe_seconds("2w")


def test_bucket_start_aligns_down():
    assert bucket_start(125, "1m") == 120
    assert bucket_start(3601, "1h") == 3600


def test_rollup_1m_to_5m():
    base = [
        {"ts": 0, "o": 10, "h": 12, "l": 9, "c": 11, "v": 1},
        {"ts": 60, "o": 11, "h": 15, "l": 10, "c": 14, "v": 2},
        {"ts": 120, "o": 14, "h": 14, "l": 8, "c": 9, "v": 3},
        {"ts": 300, "o": 9, "h": 9, "l": 7, "c": 8, "v": 4},
    ]
    out = rollup(base, "5m")
    assert len(out) == 2
    first = out[0]
    assert first == {"ts": 0, "o": 10, "h": 15, "l": 8, "c": 9, "v": 6}
    assert out[1]["ts"] == 300 and out[1]["o"] == 9 and out[1]["v"] == 4


def test_rollup_handles_unsorted_input():
    base = [
        {"ts": 120, "o": 3, "h": 3, "l": 3, "c": 3, "v": 1},
        {"ts": 0, "o": 1, "h": 1, "l": 1, "c": 1, "v": 1},
        {"ts": 60, "o": 2, "h": 2, "l": 2, "c": 2, "v": 1},
    ]
    out = rollup(base, "5m")
    assert len(out) == 1
    assert out[0]["o"] == 1 and out[0]["c"] == 3 and out[0]["v"] == 3
