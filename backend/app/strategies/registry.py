"""Registry mapping strategy type names to implementations."""

from __future__ import annotations

from app.strategies.base import BaseStrategy, StrategyParams
from app.strategies.ma_crossover import MACrossover

STRATEGIES: dict[str, type[BaseStrategy]] = {
    "ma_crossover": MACrossover,
}


def get_strategy_class(strategy_type: str) -> type[BaseStrategy]:
    try:
        return STRATEGIES[strategy_type]
    except KeyError as exc:
        raise ValueError(f"Unknown strategy type '{strategy_type}'") from exc


def build_strategy(strategy_type: str, params: dict) -> BaseStrategy:
    klass = get_strategy_class(strategy_type)
    parsed: StrategyParams = klass.Params(**params)
    return klass(parsed)
