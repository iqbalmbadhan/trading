"""Detect missing candle ranges so the fetcher can backfill them."""

from __future__ import annotations

from app.market_data.timeframes import timeframe_seconds


def expected_timestamps(start: int, end: int, timeframe: str) -> list[int]:
    """Inclusive list of aligned candle open times in [start, end]."""
    step = timeframe_seconds(timeframe)
    first = start - (start % step)
    if first < start:
        first += step
    return list(range(first, end + 1, step))


def find_gaps(start: int, end: int, timeframe: str, existing: set[int]) -> list[tuple[int, int]]:
    """Return contiguous ``(gap_start, gap_end)`` ranges of missing candles.

    Bounds are aligned candle open times; both ends inclusive.
    """
    step = timeframe_seconds(timeframe)
    missing = [ts for ts in expected_timestamps(start, end, timeframe) if ts not in existing]
    if not missing:
        return []
    gaps: list[tuple[int, int]] = []
    run_start = prev = missing[0]
    for ts in missing[1:]:
        if ts == prev + step:
            prev = ts
            continue
        gaps.append((run_start, prev))
        run_start = prev = ts
    gaps.append((run_start, prev))
    return gaps
