"""Risk configuration and the runtime inputs the checks need."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    """Per-user risk limits. Persisted as a single rules row."""

    max_trade_risk_pct: float = Field(default=0.01, gt=0, le=1)
    max_position_value: float = Field(default=100_000.0, gt=0)
    max_open_positions: int = Field(default=10, ge=1)
    blacklist: list[str] = Field(default_factory=list)
    strategy_daily_loss_limit: float = Field(default=500.0, ge=0)
    account_daily_loss_limit: float = Field(default=1_000.0, ge=0)
    max_drawdown_pct: float = Field(default=0.2, gt=0, le=1)
    max_correlation: float = Field(default=0.8, ge=0, le=1)
    require_stop_loss: bool = True


@dataclass(frozen=True)
class TradeProposal:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    entry_price: float
    stop_price: float | None
    strategy_id: int | None = None


@dataclass
class AccountState:
    equity: float
    open_position_symbols: list[str] = field(default_factory=list)
    strategy_daily_pnl: float = 0.0
    account_daily_pnl: float = 0.0
    drawdown_pct: float = 0.0
    # symbol -> recent return series (e.g. rolling 30d), for correlation.
    returns: dict[str, list[float]] = field(default_factory=dict)
