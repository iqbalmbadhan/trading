"""Pure indicator implementations.

ta-lib needs a system C library and pandas-ta pulls a heavy dependency tree;
the handful of indicators the built-in strategies need are small, exact, and
deterministic, so they are implemented directly here for testability.
"""

from __future__ import annotations


def sma(values: list[float], period: int) -> list[float | None]:
    """Simple moving average. Entries before `period` samples are None."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = []
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        out.append(running / period if i >= period - 1 else None)
    return out


def true_range(high: float, low: float, prev_close: float | None) -> float:
    if prev_close is None:
        return high - low
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int
) -> list[float | None]:
    """Wilder's Average True Range. None until `period` true ranges exist."""
    if period <= 0:
        raise ValueError("period must be positive")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, closes must be the same length")
    trs: list[float] = []
    out: list[float | None] = []
    prev_atr: float | None = None
    for i in range(len(closes)):
        prev_close = closes[i - 1] if i > 0 else None
        trs.append(true_range(highs[i], lows[i], prev_close))
        if i < period - 1:
            out.append(None)
        elif i == period - 1:
            prev_atr = sum(trs[:period]) / period
            out.append(prev_atr)
        else:
            prev_atr = (prev_atr * (period - 1) + trs[i]) / period
            out.append(prev_atr)
    return out
