"""Phase 4: OHLCV normalization and dedup."""

from app.market_data.normalizer import normalize_ohlcv


def test_milliseconds_converted_to_seconds():
    out = normalize_ohlcv([[1_700_000_000_000, 1, 2, 0.5, 1.5, 10]])
    assert out[0]["ts"] == 1_700_000_000
    assert out[0]["o"] == 1.0 and out[0]["h"] == 2.0


def test_dedup_keeps_last_and_sorts():
    out = normalize_ohlcv(
        [
            [2_000_000, 9, 9, 9, 9, 1],
            [1_000_000, 1, 1, 1, 1, 1],
            [1_000_000, 2, 2, 2, 2, 2],  # duplicate ts -> keeps this one
        ]
    )
    assert [c["ts"] for c in out] == [1000, 2000]
    assert out[0]["o"] == 2.0 and out[0]["v"] == 2.0
