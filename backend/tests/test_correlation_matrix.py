"""Phase 10: correlation matrix."""

import pytest

from app.portfolio.correlation import correlation_matrix, returns_from_closes


def test_returns_from_closes():
    assert returns_from_closes([100, 110, 99]) == pytest.approx([0.1, -0.1])


def test_perfect_and_anti_correlation():
    m = correlation_matrix(
        {
            "A": [0.01, 0.02, -0.01, 0.03],
            "B": [0.02, 0.04, -0.02, 0.06],  # 2x A -> +1
            "C": [-0.01, -0.02, 0.01, -0.03],  # -A -> -1
        }
    )
    assert m["A"]["A"] == 1.0
    assert m["A"]["B"] == pytest.approx(1.0)
    assert m["A"]["C"] == pytest.approx(-1.0)


def test_insufficient_data_is_none():
    m = correlation_matrix({"A": [0.01], "B": [0.02]})
    assert m["A"]["B"] is None
    assert m["A"]["A"] == 1.0
