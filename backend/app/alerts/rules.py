"""Alert event types, rule matching, and message formatting."""

from __future__ import annotations

from dataclasses import dataclass, field

# Supported event types and the rule param that gates them.
EVENT_TYPES = (
    "new_fill",
    "strategy_stopped",
    "kill_switch",
    "daily_pnl",
    "position_drawdown",
)


@dataclass(frozen=True)
class Event:
    type: str
    data: dict = field(default_factory=dict)


def rule_matches(event: Event, rule: dict) -> bool:
    """Return whether `event` satisfies a rule's threshold parameters."""
    if event.type == "daily_pnl":
        # Trigger when P&L fraction is at/below the (negative) threshold.
        threshold = float(rule.get("threshold", 0.0))
        return float(event.data.get("pnl_pct", 0.0)) <= threshold
    if event.type == "position_drawdown":
        threshold = float(rule.get("threshold", 0.05))
        return float(event.data.get("drawdown", 0.0)) >= threshold
    # new_fill / strategy_stopped / kill_switch: always notify when enabled.
    return event.type in EVENT_TYPES


def format_message(event: Event) -> str:
    d = event.data
    if event.type == "new_fill":
        return (
            f"Fill: {d.get('side', '?')} {d.get('qty', '?')} {d.get('symbol', '?')} "
            f"@ {d.get('price', '?')}"
        )
    if event.type == "strategy_stopped":
        return f"Strategy {d.get('strategy_id', '?')} stopped ({d.get('status', '?')})"
    if event.type == "kill_switch":
        return f"KILL SWITCH tripped: {d.get('reason', 'manual')}"
    if event.type == "daily_pnl":
        return f"Daily P&L alert: {float(d.get('pnl_pct', 0.0)) * 100:.2f}%"
    if event.type == "position_drawdown":
        return (
            f"Position drawdown {float(d.get('drawdown', 0.0)) * 100:.2f}% "
            f"on {d.get('symbol', '?')}"
        )
    return f"Alert: {event.type}"
