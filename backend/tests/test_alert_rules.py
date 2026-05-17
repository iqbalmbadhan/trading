"""Phase 11: alert rule matching and message formatting."""

from app.alerts.rules import Event, format_message, rule_matches


def test_daily_pnl_threshold():
    e = Event("daily_pnl", {"pnl_pct": -0.03})
    assert rule_matches(e, {"threshold": -0.02})
    assert not rule_matches(Event("daily_pnl", {"pnl_pct": -0.01}), {"threshold": -0.02})


def test_position_drawdown_threshold():
    assert rule_matches(Event("position_drawdown", {"drawdown": 0.07}), {"threshold": 0.05})
    assert not rule_matches(Event("position_drawdown", {"drawdown": 0.02}), {"threshold": 0.05})


def test_always_on_events():
    assert rule_matches(Event("new_fill", {}), {})
    assert rule_matches(Event("strategy_stopped", {}), {})
    assert rule_matches(Event("kill_switch", {}), {})


def test_messages():
    assert "Fill" in format_message(
        Event("new_fill", {"side": "buy", "qty": 1, "symbol": "BTC/USDT", "price": 100})
    )
    assert "KILL SWITCH" in format_message(Event("kill_switch", {"reason": "panic"}))
    assert "%" in format_message(Event("daily_pnl", {"pnl_pct": -0.05}))
