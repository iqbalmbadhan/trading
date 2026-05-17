"""Registry mapping strategy type names to implementations."""

from __future__ import annotations

from app.strategies.base import BaseStrategy, StrategyParams
from app.strategies.bollinger_squeeze import BollingerSqueeze
from app.strategies.dca import DCA
from app.strategies.donchian_breakout import DonchianBreakout
from app.strategies.funding_arb import FundingArb
from app.strategies.grid import GridTrading
from app.strategies.ma_crossover import MACrossover
from app.strategies.rsi_mean_reversion import RSIMeanReversion

STRATEGIES: dict[str, type[BaseStrategy]] = {
    "ma_crossover": MACrossover,
    "rsi_mean_reversion": RSIMeanReversion,
    "bollinger_squeeze": BollingerSqueeze,
    "donchian_breakout": DonchianBreakout,
    "grid": GridTrading,
    "dca": DCA,
    "funding_arb": FundingArb,
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
