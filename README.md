# Trading Bot Platform

Production-grade, self-hosted autonomous trading platform. Runs locally via
Docker Compose with zero cloud dependency.

> **Risk:** No trading system guarantees profit. The platform defaults to
> **paper trading**. Live trading is opt-in and requires explicit two-step
> confirmation. API keys must be trade-only (never withdrawal).

## Status

Built in phases.

**Phase 1 (Foundation)** — complete:

- Repository scaffold (`backend/`, `frontend/`, infra)
- Docker Compose: PostgreSQL/TimescaleDB, Redis, backend, frontend
- FastAPI backend with `/health` and `/api/v1/system/version`
- Next.js 14 frontend (App Router + TypeScript + Tailwind)
- CI: lint + format + tests for backend and frontend

**Phase 2 (Auth & Users)** — complete:

- `User` model + Alembic migration (migrations run on backend startup)
- Argon2id password hashing, JWT access (15m) + rotating refresh tokens
- TOTP 2FA: setup, verify, enforced at login once enabled
- Auth API: `register`, `login`, `refresh`, `logout`, `me`, `2fa-setup`, `2fa-verify`
- Frontend: `/login` page and auth-guarded home view

**Phase 3 (Exchange Connectors)** — complete:

- `BaseExchange` interface; CCXT-backed adapter; paper adapter with
  configurable slippage/latency and live-price fills
- Envelope encryption (per-secret data key wrapped by master-key KEK);
  plaintext keys never persisted or logged
- Permission verifier rejects keys with withdrawal scope (fails closed)
- Per-exchange token-bucket rate limiter
- `exchange_accounts` table + migration; API: list / connect / test /
  verify-permissions / disconnect
- Frontend `/exchanges` page with trade-only warning and connect flow

**Phase 4 (Market Data)** — complete:

- `symbols` + `candles` tables; migration `0003` creates a TimescaleDB
  hypertable and 1m→5m→15m→1h→4h→1d continuous aggregates on Postgres
  (guarded so sqlite/test runs skip the Timescale-only DDL)
- Historical `CandleFetcher`: gap detection, dedup, idempotent backfill
- OHLCV normalizer (ms→s, dedup) and timeframe rollup logic
- Live `BinanceKlineStream` with pure, unit-tested message parsing;
  Redis pub/sub `MarketDataBus` for in-process consumers
- Read API: `/api/v1/markets/symbols`, `/api/v1/markets/candles`

**Phase 5 (Strategy Base + Paper Execution)** — complete:

- `BaseStrategy` lifecycle + typed `Signal`/Pydantic params; pure
  indicator implementations (SMA, ATR)
- Fully-implemented **MA Crossover** strategy with ATR-based stops
- Signal → `PaperExecutor` pipeline; `StrategyRunner` (deterministic
  replay + live polling) shared by paper/live paths
- `strategies`/`strategy_runs`/`signals` tables + migration `0004`
- Strategy CRUD/clone/start/stop API; runs execute in a **Celery
  worker** with a Redis-backed stop control; new `worker` compose service
- Frontend `/strategies` page (templates, create, start/stop) — paper-only

**Phase 6 (Risk Manager)** — complete:

- All nine pre-trade checks (per-trade risk %, max position value, max
  open positions, blacklist, strategy/account daily loss, max drawdown,
  correlation, mandatory stop-loss) via a `RiskManager` returning an
  auditable decision
- Position sizing: fixed-fractional, ATR volatility-adjusted, fractional
  Kelly hard-capped at 0.25x full Kelly
- Global kill switch (single `KILL_SWITCH` Redis flag) enforced in the
  executor chokepoint; tripping disables all of a user's strategies and
  logs an event
- `risk_rules`/`kill_switch_events` tables + migration `0005`; risk rules
  CRUD + kill-switch trip/clear/status/events API
- Frontend `/risk` page (rules, blacklist, kill switch + history)

**Phase 7 (Order Execution — Live)** — complete:

- `LiveOrderRouter`: risk + kill-switch gate, client-UUID idempotency
  (persist before send, recover instead of resend on lost ack), safe
  exponential-backoff retries, slippage measurement/alerting, position
  and trade bookkeeping
- Locally-simulated bracket/OCO (`Bracket`), kill-switch liquidation
  (`liquidate` + per-account Celery task; trip clears paper positions and
  flattens live ones)
- `orders`/`trades`/`positions` tables + user live flags + migration
  `0006`; orders/positions API and two-step live enablement (typed phrase)
- Frontend `/orders` page (manual order, positions, orders table with
  slippage/fees, live-enable panel)

**Phase 8 (Backtest Engine)** — complete:

- Event-driven engine replays historical candles through the *unchanged*
  strategy code (same path as paper/live) via a fill-simulating
  `BacktestExchange` (fee + slippage, realized-PnL booking)
- Metrics: total return, CAGR, Sharpe, Sortino, Calmar, max drawdown,
  win rate, profit factor, avg win/loss, expectancy, exposure, turnover
- Walk-forward optimization (in-sample grid → out-of-sample eval) and
  Monte Carlo trade resampling (seeded, percentiles)
- Artifacts: inline SVG equity curve, CSV trades, HTML report
- `backtests` table + migration `0007`; Celery-run with status; API to
  create/list/get/equity/report/trades.csv/cancel
- Frontend `/backtest` page (create, list, metrics + Monte Carlo grids)

**Phase 9 (Remaining Strategies)** — complete:

- Added indicators: Wilder RSI, Bollinger Bands, Donchian channel
- Six fully-implemented strategies, each with Pydantic params and
  optimization ranges: RSI Mean Reversion (trend-filtered), Bollinger
  Squeeze Breakout, Donchian Breakout, Grid (auto-range), DCA (with
  optional dip-buying), Funding-Rate Arbitrage
- All registered; immediately usable in paper/backtest/live and exposed
  via the strategy-templates endpoint (no UI changes needed)

**Phase 10 (Portfolio & Analytics)** — complete:

- USD-normalized holdings valuation (long/short delta), per-symbol
  allocation and exposure-by-asset; pure correlation matrix from candle
  returns
- Portfolio API: summary / allocation / correlation (injectable price
  provider)
- Analytics aggregated from finished backtests: overall metrics, per-
  strategy comparison, equity + drawdown curve API
- Frontend `/portfolio` (holdings, exposure, correlation heatmap) and
  `/analytics` (metric cards, per-strategy comparison) pages

**Phase 11 (Alerts)** — complete:

- Channels: Telegram, webhook (Discord/Slack), email (SMTP) — network/
  SMTP behind injectable helpers
- Rule engine with event types (new_fill, strategy_stopped, kill_switch,
  daily_pnl, position_drawdown) + threshold matching + message formatting
- `notifications`/`notification_log` tables + migration `0008`; best-
  effort dispatch (failures logged, never break trading); kill-switch
  trip emits an alert
- Alerts API: CRUD, test send, delivery history; frontend `/alerts` page

**Phase 12 (Smart Order Routing)** — complete:

- Pure best-price split planner (`plan_route`): cheapest-ask-first for
  buys, highest-bid-first for sells, per-venue liquidity caps, reports
  unfilled remainder
- `SmartOrderRouter`: quotes top-of-book across venue adapters and
  executes child orders, aggregating fills into one synthetic result
- API: `/api/v1/routing/quote` (across connected venues) and
  `/execute` (paper-only); frontend `/routing` page

**Phase 13 (Audit & Decision Log)** — complete:

- Append-only `audit_log` (deletes recorded as tombstones with prior
  state) and per-run `decisions` (decision + indicators + reasoning)
- `record_audit` (own-commit, never blocks the caller) wired into
  strategy start/stop/delete, kill-switch trip/clear, live-trading
  enable/disable, exchange connect/disconnect; `record_decision` written
  for every strategy signal in `execute_run`
- Read API: `/api/v1/audit` (action/target filter) and
  `/api/v1/audit/decisions/{run}` (ownership-checked); migration `0009`
- Frontend `/logs` page (filterable audit + per-run decisions)

**Phase 14 (Mobile PWA Polish)** — complete:

- `@ducanh2912/next-pwa` integration (service worker, runtime caching,
  disabled in dev), web app manifest + SVG icon, theme/viewport metadata,
  installable + offline-capable
- Shared responsive `AppShell` (sticky nav, desktop row + mobile
  hamburger menu, sign-out) injected via `RequireAuth` so every
  authenticated page gets consistent mobile-friendly navigation

**Phase 15 (Observability)** — complete:

- Prometheus `/metrics` endpoint: HTTP request count + latency histogram
  (labelled by method/route/status) plus domain counters (orders placed,
  signals recorded, kill-switch trips, strategy starts) wired at their
  call sites
- `--profile monitoring` Compose services: Prometheus (scrapes backend),
  Loki + Promtail (container log shipping), Grafana with provisioned
  datasources and a starter dashboard

Run monitoring: `docker compose --profile monitoring up -d` (Grafana on
`:3001`, Prometheus on `:9090`).

**Phase 16 (Hardening & Docs)** — complete:

- `scripts/setup.sh` (generate secrets, migrate, create admin — idempotent),
  `scripts/backup.sh` / `scripts/restore.sh` (one-command DB backup/restore)
- Secret rotation: `rewrap_dek` re-wraps data keys under a new master key
  with no plaintext exposure, driven by `app.scripts.rotate_master_key`;
  `app.scripts.create_admin` management command
- Docs: `docs/PENTEST_CHECKLIST.md`, `docs/OPERATIONS.md`,
  `docs/USER_GUIDE.md`

**All 16 phases complete.** Full suite green: backend 193 pytest, frontend
lint/format/build.

## Quick Start

```bash
git clone <repo>
cd trading
./scripts/setup.sh        # generates .env secrets, migrates, creates admin
docker compose up -d
# Backend:  http://localhost:8000/health
# Frontend: http://localhost:3000
```

See `docs/USER_GUIDE.md` for the end-to-end walkthrough and
`docs/OPERATIONS.md` for backup/restore, monitoring, and secret rotation.

## Local Development

Backend:

```bash
cd backend
pip install ".[dev]"
uvicorn app.main:app --reload
pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, structlog
- **Data:** PostgreSQL 16 + TimescaleDB, Redis 7
- **Frontend:** Next.js 14, TypeScript, TailwindCSS
- **Infra:** Docker Compose

## Roadmap

See the build specification. 16 phases: foundation → auth → exchange
connectors → market data → strategies → risk → execution → backtest →
analytics → alerts → observability → hardening.
