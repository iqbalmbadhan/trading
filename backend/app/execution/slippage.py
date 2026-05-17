"""Slippage measurement against an expected price."""

from __future__ import annotations

from app.exchanges.base import OrderSide


def slippage_bps(expected: float, fill: float, side: OrderSide) -> float:
    """Signed slippage in basis points (positive = worse than expected).

    A buy filled above expected, or a sell filled below expected, is
    adverse and reported as positive.
    """
    if expected <= 0:
        return 0.0
    raw = (fill - expected) / expected
    signed = raw if side is OrderSide.BUY else -raw
    return signed * 10_000.0


def exceeds_threshold(expected: float, fill: float, side: OrderSide, threshold_bps: float) -> bool:
    return slippage_bps(expected, fill, side) > threshold_bps
