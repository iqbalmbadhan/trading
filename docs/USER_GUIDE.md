# User Guide

> No trading system guarantees profit. The platform defaults to **paper
> trading**. You can lose money in live mode. API keys must be trade-only.

## Quick start (the Definition-of-Done path)

1. `./scripts/setup.sh && docker compose up -d`
2. Open http://localhost:3000 and log in with the admin credentials.
3. **Security → 2FA**: from the login/account flow, set up TOTP 2FA and
   verify it (required before live trading is sensible).
4. **Exchanges**: connect Binance with a **trade-only** API key (keys
   with withdrawal scope are rejected automatically).
5. **Strategies**: create the *MA Crossover* strategy, pick a symbol and
   timeframe. It starts in paper mode.
6. **Backtest**: run a backtest for the same strategy/symbol; review the
   metrics grid, equity curve and Monte Carlo distribution.
7. Start the strategy (paper) and let it run; watch **Orders**,
   **Portfolio**, **Analytics**, and **Logs**.
8. When ready, **Orders → Enable live**: type
   `I UNDERSTAND I CAN LOSE MONEY`, then place a small live order.

## Pages

| Page | What it does |
|------|--------------|
| Overview | Account summary |
| Strategies | Create / start / stop strategies (paper) |
| Backtest | Run backtests, view metrics & Monte Carlo |
| Orders | Manual orders, positions, live-enable gate |
| Portfolio | USD holdings, exposure, correlation heatmap |
| Analytics | Per-strategy comparison, equity/drawdown |
| Risk | Risk rules, blacklist, kill switch + history |
| Routing | Best-price split across venues (quote/execute) |
| Exchanges | Connect/verify/disconnect exchange keys |
| Alerts | Telegram/webhook/email rules + history |
| Logs | Audit log and per-run strategy decisions |

## Safety controls

- **Paper by default** — every strategy and connection is simulated until
  you explicitly enable live trading with the typed phrase.
- **Kill switch** — one click stops all activity and blocks new orders.
- **Risk limits** — per-trade risk %, max position/open positions, daily
  loss limits, drawdown, correlation, and mandatory stop-loss.
- **Audit log** — every state change is recorded append-only.
