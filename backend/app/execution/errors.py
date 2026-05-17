"""Execution-layer exceptions."""


class ExecutionError(Exception):
    """Base class for execution failures."""


class RiskRejected(ExecutionError):
    """Raised when the risk manager rejects a proposed order."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


class LiveTradingNotEnabled(ExecutionError):
    """Raised when a live order is attempted without the two-step opt-in."""


class KillSwitchEngaged(ExecutionError):
    """Raised when an order is attempted while the kill switch is tripped."""
