#!/usr/bin/env bash
# Back up the Postgres database to ./backups/<timestamp>.sql.gz
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backups
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="backups/trading-${STAMP}.sql.gz"

docker compose exec -T db pg_dump -U trading trading | gzip > "${OUT}"
echo "Backup written: ${OUT}"
echo "Keep your .env (MASTER_KEY) safe and separate — without it, encrypted"
echo "exchange credentials in this dump cannot be decrypted."
