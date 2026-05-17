"""Phase 6: pre-trade risk checks."""

from app.risk.config import AccountState, RiskConfig, TradeProposal
from app.risk.manager import RiskManager


def _proposal(**kw) -> TradeProposal:
    base = dict(
        symbol="BTC/USDT",
        side="buy",
        qty=1.0,
        entry_price=100.0,
        stop_price=99.0,
        strategy_id=1,
    )
    base.update(kw)
    return TradeProposal(**base)


def test_clean_proposal_approved():
    mgr = RiskManager(RiskConfig(max_trade_risk_pct=0.5))
    decision = mgr.evaluate(_proposal(), AccountState(equity=10_000))
    assert decision.approved and decision.reasons == []


def test_missing_stop_loss_rejected():
    mgr = RiskManager(RiskConfig())
    d = mgr.evaluate(_proposal(stop_price=None), AccountState(equity=10_000))
    assert not d.approved
    assert any("stop-loss" in r for r in d.reasons)


def test_per_trade_risk_limit():
    mgr = RiskManager(RiskConfig(max_trade_risk_pct=0.01))
    # risk = |100-90| * 10 = 100; budget = 10000*0.01 = 100 -> ok at boundary
    ok = mgr.evaluate(
        _proposal(qty=10, entry_price=100, stop_price=90), AccountState(equity=10_000)
    )
    assert ok.approved
    bad = mgr.evaluate(
        _proposal(qty=11, entry_price=100, stop_price=90), AccountState(equity=10_000)
    )
    assert not bad.approved and any("per-trade risk" in r for r in bad.reasons)


def test_blacklist_and_position_value():
    mgr = RiskManager(
        RiskConfig(blacklist=["BTC/USDT"], max_position_value=50, max_trade_risk_pct=1.0)
    )
    d = mgr.evaluate(_proposal(qty=1, entry_price=100), AccountState(equity=10_000))
    assert not d.approved
    assert any("blacklisted" in r for r in d.reasons)
    assert any("position value" in r for r in d.reasons)


def test_max_open_positions():
    mgr = RiskManager(RiskConfig(max_open_positions=2, max_trade_risk_pct=1.0))
    state = AccountState(equity=10_000, open_position_symbols=["ETH/USDT", "SOL/USDT"])
    d = mgr.evaluate(_proposal(symbol="BTC/USDT"), state)
    assert not d.approved and any("open positions" in r for r in d.reasons)
    # Adding to an existing position is allowed.
    state2 = AccountState(equity=10_000, open_position_symbols=["BTC/USDT", "ETH/USDT"])
    assert mgr.evaluate(_proposal(symbol="BTC/USDT"), state2).approved


def test_daily_loss_and_drawdown_limits():
    mgr = RiskManager(
        RiskConfig(
            strategy_daily_loss_limit=100,
            account_daily_loss_limit=200,
            max_drawdown_pct=0.2,
            max_trade_risk_pct=1.0,
        )
    )
    state = AccountState(
        equity=10_000,
        strategy_daily_pnl=-100,
        account_daily_pnl=-250,
        drawdown_pct=0.25,
    )
    d = mgr.evaluate(_proposal(), state)
    reasons = " ".join(d.reasons)
    assert not d.approved
    assert "strategy daily loss" in reasons
    assert "account daily loss" in reasons
    assert "drawdown" in reasons


def test_correlation_check():
    mgr = RiskManager(RiskConfig(max_correlation=0.8, max_trade_risk_pct=1.0))
    returns = {
        "BTC/USDT": [1.0, 2.0, 3.0, 4.0],
        "ETH/USDT": [2.0, 4.0, 6.0, 8.0],  # perfectly correlated
    }
    state = AccountState(equity=10_000, open_position_symbols=["ETH/USDT"], returns=returns)
    d = mgr.evaluate(_proposal(symbol="BTC/USDT"), state)
    assert not d.approved and any("correlation" in r for r in d.reasons)
