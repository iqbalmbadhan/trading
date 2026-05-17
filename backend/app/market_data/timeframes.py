"""Timeframe definitions and candle rollup logic."""

from __future__ import annotations

TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}

# Source timeframe each aggregate is built from.
ROLLUP_SOURCE: dict[str, str] = {
    "5m": "1m",
    "15m": "5m",
    "1h": "15m",
    "4h": "1h",
    "1d": "4h",
}


def timeframe_seconds(timeframe: str) -> int:
    try:
        return TIMEFRAME_SECONDS[timeframe]
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe '{timeframe}'") from exc


def bucket_start(ts: int, timeframe: str) -> int:
    step = timeframe_seconds(timeframe)
    return ts - (ts % step)


def rollup(candles: list[dict], target_timeframe: str) -> list[dict]:
    """Aggregate lower-timeframe candles into `target_timeframe` buckets.

    Each input candle is a dict with keys ts, o, h, l, c, v (ts in seconds).
    Output is sorted by bucket start time. Partial buckets are emitted as-is;
    callers decide whether the most recent bucket is final.
    """
    step = timeframe_seconds(target_timeframe)
    buckets: dict[int, dict] = {}
    for candle in sorted(candles, key=lambda c: c["ts"]):
        key = candle["ts"] - (candle["ts"] % step)
        agg = buckets.get(key)
        if agg is None:
            buckets[key] = {
                "ts": key,
                "o": candle["o"],
                "h": candle["h"],
                "l": candle["l"],
                "c": candle["c"],
                "v": candle["v"],
            }
        else:
            agg["h"] = max(agg["h"], candle["h"])
            agg["l"] = min(agg["l"], candle["l"])
            agg["c"] = candle["c"]
            agg["v"] += candle["v"]
    return [buckets[k] for k in sorted(buckets)]
