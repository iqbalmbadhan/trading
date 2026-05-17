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


def rsi(values: list[float], period: int) -> list[float | None]:
    """Wilder's RSI. None until `period` deltas are available."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period

    def _rsi(g: float, loss: float) -> float:
        if loss == 0:
            return 100.0
        rs = g / loss
        return 100.0 - 100.0 / (1.0 + rs)

    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi(avg_gain, avg_loss)
    return out


def bollinger(
    values: list[float], period: int, num_std: float
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Return (middle, upper, lower) Bollinger Bands using population stddev."""
    if period <= 0:
        raise ValueError("period must be positive")
    mid: list[float | None] = []
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            mid.append(None)
            upper.append(None)
            lower.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        sd = var**0.5
        mid.append(m)
        upper.append(m + num_std * sd)
        lower.append(m - num_std * sd)
    return mid, upper, lower


def donchian(
    highs: list[float], lows: list[float], period: int
) -> tuple[list[float | None], list[float | None]]:
    """Return (upper, lower) Donchian channel over a trailing window."""
    if period <= 0:
        raise ValueError("period must be positive")
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(highs)):
        if i < period - 1:
            upper.append(None)
            lower.append(None)
            continue
        upper.append(max(highs[i - period + 1 : i + 1]))
        lower.append(min(lows[i - period + 1 : i + 1]))
    return upper, lower
