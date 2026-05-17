"""Pure pre-trade risk checks.

Each check returns ``(ok, reason)``. A proposal is only allowed when every
check passes; the reasons of failing checks explain the rejection and are
written to the decision log.
"""

from __future__ import annotations

from app.risk.config import AccountState, RiskConfig, TradeProposal

CheckResult = tuple[bool, str | None]


def _pearson(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a <= 0 or var_b <= 0:
        return None
    return cov / (var_a**0.5 * var_b**0.5)


def check_stop_loss(p: TradeProposal, cfg: RiskConfig, _: AccountState) -> CheckResult:
    if cfg.require_stop_loss and p.stop_price is None:
        return False, "mandatory stop-loss missing"
    return True, None


def check_blacklist(p: TradeProposal, cfg: RiskConfig, _: AccountState) -> CheckResult:
    if p.symbol in cfg.blacklist:
        return False, f"{p.symbol} is blacklisted"
    return True, None


def check_per_trade_risk(p: TradeProposal, cfg: RiskConfig, state: AccountState) -> CheckResult:
    if p.stop_price is None:
        return True, None  # stop-loss check owns the missing-stop case
    risk = abs(p.entry_price - p.stop_price) * p.qty
    budget = state.equity * cfg.max_trade_risk_pct
    if risk > budget:
        return False, f"per-trade risk {risk:.2f} exceeds budget {budget:.2f}"
    return True, None


def check_position_value(p: TradeProposal, cfg: RiskConfig, _: AccountState) -> CheckResult:
    value = p.qty * p.entry_price
    if value > cfg.max_position_value:
        return False, f"position value {value:.2f} exceeds max {cfg.max_position_value:.2f}"
    return True, None


def check_max_open_positions(p: TradeProposal, cfg: RiskConfig, state: AccountState) -> CheckResult:
    if p.symbol in state.open_position_symbols:
        return True, None  # adding to an existing position, not a new slot
    if len(state.open_position_symbols) >= cfg.max_open_positions:
        return False, f"open positions at limit ({cfg.max_open_positions})"
    return True, None


def check_strategy_daily_loss(
    _: TradeProposal, cfg: RiskConfig, state: AccountState
) -> CheckResult:
    if state.strategy_daily_pnl <= -cfg.strategy_daily_loss_limit:
        return False, "strategy daily loss limit reached"
    return True, None


def check_account_daily_loss(_: TradeProposal, cfg: RiskConfig, state: AccountState) -> CheckResult:
    if state.account_daily_pnl <= -cfg.account_daily_loss_limit:
        return False, "account daily loss limit reached"
    return True, None


def check_max_drawdown(_: TradeProposal, cfg: RiskConfig, state: AccountState) -> CheckResult:
    if state.drawdown_pct >= cfg.max_drawdown_pct:
        return False, f"max drawdown {cfg.max_drawdown_pct:.0%} breached"
    return True, None


def check_correlation(p: TradeProposal, cfg: RiskConfig, state: AccountState) -> CheckResult:
    proposed = state.returns.get(p.symbol)
    if not proposed:
        return True, None
    for sym in state.open_position_symbols:
        other = state.returns.get(sym)
        if not other:
            continue
        corr = _pearson(proposed, other)
        if corr is not None and abs(corr) >= cfg.max_correlation:
            return False, f"correlation with {sym} ({corr:.2f}) exceeds threshold"
    return True, None


ALL_CHECKS = (
    check_stop_loss,
    check_blacklist,
    check_per_trade_risk,
    check_position_value,
    check_max_open_positions,
    check_strategy_daily_loss,
    check_account_daily_loss,
    check_max_drawdown,
    check_correlation,
)
