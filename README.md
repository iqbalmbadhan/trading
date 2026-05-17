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

## Quick Start

```bash
git clone <repo>
cd trading
cp .env.example .env
docker compose up -d
# Backend:  http://localhost:8000/health
# Frontend: http://localhost:3000
```

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
