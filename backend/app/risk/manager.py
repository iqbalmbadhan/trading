"""Risk manager: runs every pre-trade check and returns an auditable decision."""

from __future__ import annotations

from dataclasses import dataclass

from app.risk.checks import ALL_CHECKS
from app.risk.config import AccountState, RiskConfig, TradeProposal


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reasons: list[str]


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def evaluate(self, proposal: TradeProposal, state: AccountState) -> RiskDecision:
        reasons: list[str] = []
        for check in ALL_CHECKS:
            ok, reason = check(proposal, self._config, state)
            if not ok and reason:
                reasons.append(reason)
        return RiskDecision(approved=not reasons, reasons=reasons)
