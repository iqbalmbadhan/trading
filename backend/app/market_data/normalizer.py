"""Normalize raw exchange OHLCV into the internal candle format."""

from __future__ import annotations


def normalize_ohlcv(raw: list[list[float]]) -> list[dict]:
    """Convert CCXT-style ``[ms_ts, o, h, l, c, v]`` rows to candle dicts.

    CCXT OHLCV timestamps are epoch milliseconds; they are converted to
    integer seconds. Duplicate timestamps are deduplicated keeping the last
    occurrence (exchanges may resend the in-progress candle). Output is
    sorted ascending by ts.
    """
    by_ts: dict[int, dict] = {}
    for row in raw:
        ts = int(row[0]) // 1000
        by_ts[ts] = {
            "ts": ts,
            "o": float(row[1]),
            "h": float(row[2]),
            "l": float(row[3]),
            "c": float(row[4]),
            "v": float(row[5]),
        }
    return [by_ts[ts] for ts in sorted(by_ts)]
