"""Position sizing methods.

All methods return a non-negative quantity. The Kelly method is always
capped at a configurable fraction of full Kelly (default and hard ceiling
0.25x) so a single estimate error cannot blow up the account.
"""

from __future__ import annotations

MAX_KELLY_FRACTION = 0.25


def fixed_fractional(
    equity: float, risk_pct: float, entry_price: float, stop_price: float
) -> float:
    """Risk a fixed fraction of equity between entry and stop."""
    if equity <= 0 or risk_pct <= 0:
        return 0.0
    distance = abs(entry_price - stop_price)
    if distance <= 0:
        return 0.0
    return (equity * risk_pct) / distance


def volatility_adjusted(equity: float, risk_pct: float, atr: float, atr_mult: float) -> float:
    """Size so the ATR-derived stop distance risks `risk_pct` of equity."""
    if equity <= 0 or risk_pct <= 0 or atr <= 0 or atr_mult <= 0:
        return 0.0
    stop_distance = atr * atr_mult
    return (equity * risk_pct) / stop_distance


def fractional_kelly(
    equity: float,
    win_prob: float,
    win_loss_ratio: float,
    price: float,
    kelly_fraction: float = MAX_KELLY_FRACTION,
) -> float:
    """Quantity from fractional Kelly, hard-capped at 0.25x full Kelly."""
    if not 0.0 <= win_prob <= 1.0:
        raise ValueError("win_prob must be in [0, 1]")
    if equity <= 0 or win_loss_ratio <= 0 or price <= 0:
        return 0.0
    full_kelly = win_prob - (1.0 - win_prob) / win_loss_ratio
    if full_kelly <= 0:
        return 0.0
    fraction = full_kelly * min(kelly_fraction, MAX_KELLY_FRACTION)
    return (equity * fraction) / price
