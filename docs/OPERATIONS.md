# Operations Guide

## First-time setup

```bash
./scripts/setup.sh        # generates .env secrets, migrates, creates admin
docker compose up -d      # start all services
```

Override defaults: `ADMIN_EMAIL=you@example.com ADMIN_PASSWORD=... ./scripts/setup.sh`

## Backup & restore

```bash
./scripts/backup.sh                                  # -> backups/trading-<ts>.sql.gz
./scripts/restore.sh backups/trading-<ts>.sql.gz     # confirm with "yes"
```

The database dump contains **encrypted** exchange credentials. Store the
`MASTER_KEY` (in `.env`) separately and securely — without it the dump's
credentials cannot be decrypted.

## Secret rotation (master key)

1. Generate a new key: `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`
2. Re-wrap stored data keys (no plaintext exposure):

   ```bash
   OLD_MASTER_KEY="$current" NEW_MASTER_KEY="$new" \
     docker compose run --rm backend python -m app.scripts.rotate_master_key
   ```

3. Set `MASTER_KEY=$new` in `.env`, then `docker compose up -d` to restart.

Rotate `JWT_SECRET` similarly (all sessions are invalidated on change).

## Monitoring

```bash
docker compose --profile monitoring up -d
```

- Grafana: http://localhost:3001 (anonymous admin; starter dashboard)
- Prometheus: http://localhost:9090 (scrapes `backend:8000/metrics`)
- Loki receives container logs via Promtail

## Migrations

Migrations run automatically on backend container start
(`alembic upgrade head`). To run manually:
`docker compose run --rm backend alembic upgrade head`.

## Kill switch

Trip from the `/risk` page or `POST /api/v1/risk/kill-switch`. It blocks
all new orders, disables running strategies, clears paper positions, and
enqueues liquidation for live accounts. Clear it from the same page.
