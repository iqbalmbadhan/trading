"""Correlation matrix from per-symbol return series."""

from __future__ import annotations


def _pearson(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / (va**0.5 * vb**0.5)


def returns_from_closes(closes: list[float]) -> list[float]:
    out = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        out.append((closes[i] - prev) / prev if prev else 0.0)
    return out


def correlation_matrix(
    returns_by_symbol: dict[str, list[float]],
) -> dict[str, dict[str, float | None]]:
    symbols = sorted(returns_by_symbol)
    matrix: dict[str, dict[str, float | None]] = {}
    for a in symbols:
        row: dict[str, float | None] = {}
        for b in symbols:
            row[b] = 1.0 if a == b else _pearson(returns_by_symbol[a], returns_by_symbol[b])
        matrix[a] = row
    return matrix
