"""Walk-forward optimization: optimize in-sample, evaluate out-of-sample."""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from app.backtest.engine import BacktestConfig, run_backtest_engine
from app.strategies.base import Candle
from app.strategies.registry import build_strategy, get_strategy_class

_MAX_COMBOS = 64


def _grid(strategy_type: str, base_params: dict) -> list[dict]:
    ranges = get_strategy_class(strategy_type).param_ranges
    if not ranges:
        return [dict(base_params)]
    axes: dict[str, list[float]] = {}
    for name, (low, high, step) in ranges.items():
        values: list[float] = []
        v = low
        while v <= high + 1e-9:
            values.append(round(v, 6))
            v += step
        axes[name] = values or [low]
    combos: list[dict] = []
    for combo in itertools.product(*axes.values()):
        params = dict(base_params)
        for name, value in zip(axes.keys(), combo, strict=True):
            params[name] = int(value) if float(value).is_integer() else value
        combos.append(params)
        if len(combos) >= _MAX_COMBOS:
            break
    return combos


@dataclass
class FoldResult:
    fold: int
    best_params: dict
    in_sample_metric: float
    out_of_sample: dict[str, float]


async def _score(strategy_type, params, candles, config, metric) -> float:
    try:
        strat = build_strategy(strategy_type, params)
    except Exception:
        return float("-inf")
    result = await run_backtest_engine(strat, candles, config)
    return result.metrics.get(metric, float("-inf"))


async def walk_forward(
    strategy_type: str,
    base_params: dict,
    candles: list[Candle],
    config: BacktestConfig,
    *,
    folds: int = 4,
    metric: str = "sharpe",
) -> list[FoldResult]:
    seg = len(candles) // (folds + 1)
    if seg < 2:
        raise ValueError("not enough candles for the requested number of folds")

    grid = _grid(strategy_type, base_params)
    results: list[FoldResult] = []
    for i in range(1, folds + 1):
        in_sample = candles[: i * seg]
        out_sample = candles[i * seg : (i + 1) * seg]
        if len(out_sample) < 2:
            break
        best_params = grid[0]
        best_score = float("-inf")
        for params in grid:
            score = await _score(strategy_type, params, in_sample, config, metric)
            if score > best_score:
                best_score, best_params = score, params
        strat = build_strategy(strategy_type, best_params)
        oos = (await run_backtest_engine(strat, out_sample, config)).metrics
        results.append(
            FoldResult(
                fold=i,
                best_params=best_params,
                in_sample_metric=best_score,
                out_of_sample=oos,
            )
        )
    return results
