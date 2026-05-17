"""USD-normalized holdings valuation and exposure breakdown."""

from __future__ import annotations

from dataclasses import dataclass

# Quote assets treated as ~1 USD for normalization.
STABLES = {"USDT", "USDC", "USD", "DAI", "BUSD", "TUSD"}


@dataclass(frozen=True)
class Holding:
    symbol: str
    base: str
    qty: float
    price_usd: float
    value_usd: float
    is_paper: bool


def base_of(symbol: str) -> str:
    return symbol.split("/")[0].split(":")[0]


def value_holdings(positions: list[dict], price_usd: dict[str, float]) -> list[Holding]:
    """Value each position in USD using a ``symbol -> price`` map.

    A position dict has: symbol, qty, side, is_paper. Short positions carry
    negative value (delta exposure).
    """
    out: list[Holding] = []
    for p in positions:
        symbol = p["symbol"]
        price = float(price_usd.get(symbol, 0.0))
        signed_qty = p["qty"] if p["side"] == "buy" else -p["qty"]
        out.append(
            Holding(
                symbol=symbol,
                base=base_of(symbol),
                qty=signed_qty,
                price_usd=price,
                value_usd=signed_qty * price,
                is_paper=bool(p.get("is_paper", True)),
            )
        )
    return out


def allocation(holdings: list[Holding]) -> dict[str, float]:
    """Fraction of gross exposure per symbol (absolute value weighted)."""
    gross = sum(abs(h.value_usd) for h in holdings)
    if gross <= 0:
        return {}
    return {h.symbol: abs(h.value_usd) / gross for h in holdings}


def exposure_by_base(holdings: list[Holding]) -> dict[str, float]:
    gross = sum(abs(h.value_usd) for h in holdings)
    if gross <= 0:
        return {}
    out: dict[str, float] = {}
    for h in holdings:
        out[h.base] = out.get(h.base, 0.0) + abs(h.value_usd) / gross
    return out


def total_value_usd(holdings: list[Holding]) -> float:
    return sum(h.value_usd for h in holdings)
